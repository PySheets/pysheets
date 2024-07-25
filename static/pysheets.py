import ltk
import ltk.pubsub
import api
import collections
import constants
import history
import inventory
import menu
import models
import preview
import timeline
import random
import html_maker
import selection
import storage
import state
import editor
import sys

from models import *

from pyscript import window  # type: ignore

ACTIVITY_PASTE = "Paste from clipboard"

state.console.write("pysheets", f"[Main] Pysheets starting {constants.ICON_HOUR_GLASS}")

completion_cache = {}
proxy = ltk.proxy
is_mac = window.navigator.platform.upper().startswith("MAC")
is_ios = window.navigator.platform.upper().startswith("I")
is_apple = is_mac or is_ios
sheet = None


def is_command_key(event):
    return (event.metaKey or event.ctrlKey) if is_apple else event.ctrlKey


def rgb_to_hex(rgb):
    try:
        r, g, b = map(int, rgb[4:-1].split(", "))
        return f"#{r:02x}{g:02x}{b:02x}"
    except:
        return "#404"


class SpreadsheetView():
    def __init__(self, model):
        self.model = model
        self.model.listen(self.model_changed)
        self.clear()
        ltk.subscribe(constants.PUBSUB_SHEET_ID, ltk.TOPIC_WORKER_RESULT, self.handle_worker_result)
        ltk.subscribe(constants.PUBSUB_SHEET_ID, ltk.pubsub.TOPIC_WORKER_READY, self.worker_ready)
        self.cell_views = {}
        self.selection = ltk.Input("").addClass("selection")
        self.multi_selection = selection.MultiSelection(self)
        self.selection_edited = False
        self.mousedown = False
        self.fill_cache()

    def fill_cache(self):
        for model in self.model.cells.values():
            self.cache[model.key] = convert(model.value)

    def model_changed(self, sheet, info):
        field_name = info["name"]
        if field_name == "rows":
            ltk.find(f".row-{info['row']}").css("height", info['height'])
            self.reselect()
        elif field_name == "columns":
            ltk.find(f".col-{info['column']}").css("width", info['width'])
            self.reselect()
        elif field_name == "name":
            new_name = sheet.name
            if window.document.title != new_name:
                window.document.title = new_name
                ltk.find("#title").val(new_name)
                history.add(models.NameChanged("", new_name).apply(self.model))
        sheet_resized()

    def get_cell(self, key):
        assert api.is_cell_reference(key), f"Bad key, got '{key}', expected something like 'A2'"
        if key not in self.cell_views:
            cell_model = self.model.get_cell(key)
            self.cell_views[key] = CellView(self, key, cell_model)
        return self.cell_views[key]

    def clear(self):
        self.cells = {}
        self.cache = {}
        self.counts = collections.defaultdict(int)
        self.current = None

    def copy(self, from_cell, to_cell):
        to_cell.set(from_cell.model.script)
        to_cell.value.get()
        to_cell.store_edit()
        from_cell.store_edit()
        to_cell.attr("style", from_cell.attr("style"))

    def handle_worker_result(self, result):
        key = result["key"]
        preview.add(self, key, result["preview"])
        cell: CellView = self.get_cell(key)
        cell.handle_worker_result(result)
        if result["prompt"]:
            add_completion_button(key, lambda: insert_prompt(result["prompt"]))
        self.reselect()
        
    def post_load(self):
        create_top()
        ltk.find("#main").focus().on("keydown", proxy(lambda event: self.navigate(event)))
        ltk.find(".hidden").removeClass("hidden")
        state.set_title(self.model.name)
        current = self.model.selected or "A1"
        ltk.schedule(lambda: self.select(self.get_cell(current)), "select-later", 0.1)
        ltk.find(".main-editor-container").width(window.editor_width)
        ltk.find(".sheet").css("cursor", "default")
        self.show_loading()
        preview.load(self)
        ltk.schedule(self.run_ai, "run ai", 3)
        ltk.find("#main").animate(ltk.to_js({ "opacity": 1 }), constants.ANIMATION_DURATION)
        window.document.title = self.model.name
        window.makeSheetResizable()
        window.makeSheetScrollable()
        timeline.setup()
    
    def run_ai(self):
        ltk.schedule(self.find_pandas_data_frames, "find frames", 1)
        ltk.schedule(self.find_urls, "find urls", 1)

    def sync(self):
        pass # ltk.schedule(self.save_screenshot, "check edits", 5)

    def find_pandas_data_frames(self):
        visited = set()
        def get_width(cell_model):
            col = cell_model.column
            while True:
                col += 1
                key = models.get_key_from_col_row(col, cell_model.row)
                visited.add(key)
                if not key in self.model.cells:
                    break
            return col - cell_model.column

        def get_height(cell_model):
            row = cell_model.row
            while True:
                row += 1
                key = models.get_key_from_col_row(cell_model.column, row)
                visited.add(key)
                if not key in self.model.cells:
                    break
            return row - cell_model.row

        def add_frame(cell_model, width, height):
            for col in range(cell_model.column, cell_model.column + width):
                for row in range(cell_model.row, cell_model.row + height):
                    other_key = models.get_key_from_col_row(col, row)
                    visited.add(other_key)
            prompt = f"""
Convert the spreadsheet cells in range "{cell_model.key}:{other_key}" into a 
Pandas dataframe by calling "pysheets.sheet(range)".
Make the last expression refer to the dataframe.
Do not import the pysheets module.
"""
            text = f"""
# Create a Pandas DataFrame from values found in the current sheet
pysheets.sheet("{cell_model.key}:{other_key}")
"""
            add_completion_button(cell_model.key, lambda: insert_prompt(prompt))

        cell = sheet.get_cell("A1")
        width = get_width(cell.model)
        height = get_height(cell.model)
        if width > 1 and height > 1:
            add_frame(cell.model, width, height)

    def get_url_keys(self):
        return [
            key
            for key, cell in self.model.cells.items()
            if cell.value.startswith("https:")
        ]

    def save_current_position(self):
        history.add(models.SelectionChanged(key=self.current.model.key).apply(self.model))

    def find_urls(self):
        for key in self.get_url_keys():
            prompt = f"""
Load the data URL already stored in variable {key} into a 
Pandas dataframe by calling "pysheets.load_sheet(url)".
Make the last expression refer to the dataframe.
"""
            # TODO: add button

    def setup_selection(self):
        
        def mousedown(event):
            self.mousedown = False
            if ltk.find(event.target).hasClass("selection"):
                self.selection.css("caret-color", "black").focus()
                self.selection_edited = True
                return
            self.mousedown = True
            element = ltk.find(event.target).closest(".cell")
            if element.length == 0:
                return
            key = element.attr("id")
            cell = self.get_cell(key)
            if cell.hasClass("cell"):
                self.save_selection()
                if event.shiftKey:
                    self.multi_selection.extend(cell, force=True)
                else:
                    self.multi_selection.start(cell)
            event.preventDefault()

        def mousemove(event):
            if not self.mousedown:
                return
            element = ltk.find(event.target).closest(".cell")
            if element.length == 0:
                return
            key = element.attr("id")
            cell = self.get_cell(key)
            self.multi_selection.extend(cell)
            event.preventDefault()

        def mouseup(event):
            if not self.mousedown:
                return
            element = ltk.find(event.target).closest(".cell")
            if element.length == 0:
                return
            key = element.attr("id")
            cell = self.get_cell(key)
            self.multi_selection.stop(cell)
            event.preventDefault()
            ltk.find(event.target).trigger("click")

        ltk.find("#sheet") \
            .on("mousedown", proxy(mousedown)) \
            .on("mousemove", proxy(mousemove)) \
            .on("mouseup", proxy(mouseup)) \

    def navigate(self, event):
        target = ltk.find(event.target)
        if target.hasClass("selection"):
            self.navigate_selection(event)
        elif target.hasClass("main"):
            self.navigate_main(event)

    def navigate_selection(self, event):
        if event.key == "Escape":
            self.select(self.current)
        elif event.key in ["Tab", "Enter", "ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "PageUp", "PageDown", "Home", "End"]:
            self.navigate_main(event)
        else:
            ltk.schedule(self.copy_selection_to_main_editor, "copy-to-editor")
            return
        ltk.find("#main").focus()

    def save_selection(self, event=None):
        if self.selection_edited and self.current and self.selection.val() != self.current.text():
            self.current.edited(self.selection.val())
        self.sync()
    
    def copy_selection_to_main_editor(self):
        main_editor.set(self.selection.val())
        ltk.find("#ai-prompt").val(self.current.model.prompt)

    def navigate_main(self, event):
        if not self.current or event.key == "Meta":
            return
        current = self.multi_selection.cell2 if event.shiftKey else self.current
        column, row = current.model.column, current.model.row
        if event.key == "Tab":
            column += -1 if event.shiftKey else 1
        elif event.key == "Delete" or event.key == "Backspace":
            self.multi_selection.clear()
        elif event.key == "ArrowLeft":
            column = max(1, column - 1)
        elif event.key == "Home":
            column = 1
        elif event.key == "ArrowRight":
            column += 1
        elif event.key == "End":
            column = ltk.find("#column-header").children().length - 1
        elif event.key == "ArrowUp":
            row = max(1, row - 1)
        elif event.key == "PageDown":
            row = row + 25
        elif event.key == "PageUp":
            row = max(1, row - 25)
        elif event.key == "ArrowDown" or event.key == "Enter":
            row += 1

        if len(event.key) == 1:
            if is_command_key(event):
                handler = self.multi_selection.handler_by_shortcut.get(event.key)
                if handler:
                    handler(event)
            if event.metaKey or event.ctrlKey:
                return
            self.selection_edited = True
            self.selection.css("caret-color", "black").val("").focus()
            ltk.schedule(self.copy_selection_to_main_editor, "copy-to-editor")
        else:
            if self.current and (column != self.current.model.column or row != self.current.model.row):
                self.save_selection()
            cell = self.get_cell(models.get_key_from_col_row(column, row))
            if event.shiftKey:
                self.multi_selection.extend(cell, force=True)
            else:
                self.select(cell)
            event.preventDefault()

    def select(self, cell, force=False):
        if self.current is cell and not force:
            return
        ltk.find(".selection").remove()
        self.current = cell
        self.multi_selection.select(cell)
        cell.select()
        self.selection_edited = False
        self.selection \
            .css("background-color", "white") \
            .css("padding", "") \
            .attr("style", cell.attr("style")) \
            .css("position", "absolute") \
            .css("color", cell.css("color")) \
            .css("left", 0) \
            .css("top", 0) \
            .css("height", "calc(100% - 8px)") \
            .css("width", "calc(100% - 8px)") \
            .appendTo(cell.element) \
            .attr("class", self.current.attr("class").replace("cell", "selection")) \
            .val(cell.text())
        self.selection.css("caret-color", "transparent")
        
    def reselect(self):
        cell = self.current
        ltk.schedule(lambda: self.select(cell, force=True), "reselect")

    def show_loading(self):
        for key, cell in self.model.cells.items():
            if cell.script.startswith("="):
                self.get_cell(key).show_loading()

    def worker_ready(self, data):
        for key, cell in self.model.cells.items():
            if cell.script.startswith("="):
                self.get_cell(key).worker_ready()
        self.sync()
        if main_editor.get() == "Loading...":
            complete_prompt()

    def save_screenshot(self):
        take_screenshot(lambda data_url: history.add(models.ScreenshotChanged(url=data_url or self.model.screenshot).apply(self.model)))
 
k = {
"script":"=\ndataframe = pysheets.sheet(\"B3:D8\")                # extract values from the sheet into a Pandas dataframe\ngrouped = dataframe.groupby(\"Category\")      # pivot the table by sales category\naggregrate = grouped.agg(\"sum\")                    # total the values",
"style":{
"text-align":"center","color":"rgb(33, 37, 41)","font-size":"13.3333px","vertical-align":"middle","background-color":"rgb(217, 179, 255)"
},
"key":"D13"
}

class CycleError(Exception): pass


class CellView(ltk.Widget):
    def __init__(self, sheet: SpreadsheetView, key: str, model: models.Cell, td=None):
        self.sheet= sheet
        self.model = model
        if not key:
            raise ValueError(f"Missing key for cell")
        if not self.model:
            raise ValueError(f"No model for cell {key}")
        self.element = td or ltk.find(f"#{self.model.key}")
        if not self.element.length:
            window.fillSheet(model.column, model.row)
            self.element = ltk.find(f"#{self.model.key}")
        self.running = False
        self.needs_worker = False
        self.inputs = set()
        self.dependents = set()
        if self.model.script != self.model.value:
            self.set(self.model.script, evaluate=False)
        self.on("mouseenter", ltk.proxy(lambda event: self.enter()))
        self.model.listen(self.model_changed)
        self.element.on("DOMSubtreeModified", ltk.proxy(lambda event: self.ui_changed()))

    def ui_changed(self):
        new_value = str(self.element.attr("worker-set"))
        if not new_value in ["None", "<undefined>"]:
            self.set(new_value)
            self.element.removeAttr("worker-set")

    def model_changed(self, model, info):
        if info["name"] == "script":
            self.set(model.script)
        elif info["name"] == "value":
            self.text(model.value)
        elif info["name"] == "style":
            self.css(model.style)
        ltk.schedule(self.sheet.run_ai, "run ai", 3)
        
    def enter(self):
        selection.remove_arrows(0)
        self.draw_cell_arrows()
        self.raise_preview()
        
    def set(self, script, evaluate=True):
        if self.model.script != script:
            history.add(models.CellScriptChanged(self.model.key, self.model.script, script).apply(sheet.model))
            self.model.script = script
        if script == "":
            self.clear()
        if self.sheet.current == self:
            main_editor.set(self.model.script)
            self.sheet.select(self)
        if not self.is_formula():
            self.sheet.cache[self.model.key] = convert(script)
        if evaluate:
            ltk.schedule(self.evaluate, f"eval-{self.model.key}")

    def is_formula(self):
        return self.model.script and isinstance(self.model.script, str) and self.model.script.startswith("=")

    def update(self, duration, value):
        if self.model.script:
            count = self.sheet.counts[self.model.key]
            if count:
                if isinstance(value, str) and not "Error" in value:
                    if count > 1:
                        message = f"Ran in worker {count} times, last run took {duration:.3f}s"
                    else:
                        message = f"Ran once in worker, taking {duration:.3f}s"
                    state.console.write(
                        self.model.key,
                        f"[DAG] {self.model.key}: {message}"
                    )
        self.text(str(value))
        if self.model.value != value and self.model.script != value:
            history.add(models.CellValueChanged(self.model.key, self.model.value, value).apply(sheet.model))
        self.notify()
        self.model.value = value
        if self.sheet.current == self:
            self.sheet.selection.val(self.text())
        self.sheet.multi_selection.draw()
    
    def get_preview(self, value):
        if type(value) is dict:
            return api.get_dict_table(value)

    def notify(self):
        for key in self.dependents:
            self.sheet.get_cell(key).evaluate()
    
    def worker_ready(self):
        if self.model.key in self.sheet.cache:
            del self.sheet.cache[self.model.key]
        self.running = False
        self.evaluate()

    def select(self):
        self.remove_arrows()
        ltk.schedule(lambda: self.sheet.save_current_position(), "save selection", 3)
        main_editor.set(self.model.script)
        ltk.find("#ai-prompt").val(self.model.prompt)
        ltk.find("#selection").text(f"Cell: {self.model.key}")
        ltk.find("#cell-attributes-container").css("display", "block")
        self.set_css_editors()
        selection.scroll(self)

    def set_css_editors(self):
        ltk.find("#cell-font-family").val(self.css("font-family") or constants.DEFAULT_FONT_FAMILY)
        ltk.find("#cell-font-size").val(round(window.parseFloat(self.css("font-size"))) or constants.DEFAULT_FONT_SIZE)

        color = rgb_to_hex(self.css("color")) or constants.DEFAULT_COLOR
        ltk.find("#cell-color").val(color).css("background", color)

        background = rgb_to_hex(self.css("background-color")) or constants.DEFAULT_FILL
        ltk.find("#cell-fill").val(background).css("background", background)

        ltk.find("#cell-vertical-align").val(self.css("vertical-align") or constants.DEFAULT_VERTICAL_ALIGN)
        ltk.find("#cell-text-align").val(self.css("text-align").replace("start", "left") or constants.DEFAULT_TEXT_ALIGN)
        ltk.find("#cell-font-weight").val({"400": "normal", "700": "bold"}[self.css("font-weight")] or constants.DEFAULT_FONT_WEIGHT)
        ltk.find("#cell-font-style").val(self.css("font-style") or constants.DEFAULT_FONT_STYLE)

    def clear(self):
        self.css("font-family", constants.DEFAULT_FONT_FAMILY)
        self.css("font-size", constants.DEFAULT_FONT_SIZE)
        self.css("font-style", constants.DEFAULT_FONT_STYLE)
        self.css("color", constants.DEFAULT_COLOR)
        self.css("background-color", constants.DEFAULT_FILL)
        self.css("vertical-align", constants.DEFAULT_VERTICAL_ALIGN)
        self.css("font-weight", constants.DEFAULT_FONT_WEIGHT)
        self.css("text-align", constants.DEFAULT_TEXT_ALIGN)

        ltk.find(f"#preview-{self.model.key}").remove()
        preview.remove(self.model.key)
        if self.model.key in self.sheet.model.previews:
            history.add(models.PreviewDeleted(key=self.model.key))

        ltk.find(f"#completion-{self.model.key}").remove()
        state.console.remove(f"ai-{self.model.key}")

        self.text("")
        self.model.clear(self.sheet.model)
        self.inputs.clear()
        if self.model.key in self.sheet.cells:
            del self.sheet.cells[self.model.key]
        self.sheet.cache[self.model.key] = 0

        history.add(models.CellScriptChanged(key=self.model.key, script=""))
        history.add(models.CellValueChanged(key=self.model.key, value=""))
        history.add(models.CellStyleChanged(key=self.model.key, style={}))
        self.notify()

        self.sheet.reselect()

    def draw_cell_arrows(self):
        self.draw_arrows([])
        self.adjust_arrows()
    
    def raise_preview(self):
        preview = ltk.find(f"#preview-{self.model.key}")
        preview.appendTo(preview.parent())

    def remove_arrows(self):
        selection.remove_arrows()

    def report_cycle(self, seen):
        seen.append(self.model.key)
        cycle = " ⬅ ".join(seen)
        state.console.write(self.model.key, f"[ERROR] {self.model.key}: Dependency cycle detected: {cycle}")

    def draw_arrows(self, seen):
        if self.model.key in seen:
            self.report_cycle(seen)
            return
        seen.append(self.model.key)
        self.remove_arrows()
        if state.mobile():
            return
        if not self.inputs:
            return
        cells = [ self.sheet.get_cell(input) for input in self.inputs ]
        window.addArrow(create_marker(cells, "inputs-marker arrow", seen), self.element)
        self.addClass("arrow")

    def adjust_arrows(self):
        ltk.find(".leader-line").appendTo(ltk.find("#sheet-scrollable"))
        container = ltk.find("#sheet-container")
        scroll_left = container.scrollLeft()
        scroll_top = container.scrollTop()
        for arrow_line in ltk.find_list(".leader-line"):
            arrow_line \
                .css("top", window.parseFloat(arrow_line.css("top")) + scroll_top - 49) \
                .css("left", window.parseFloat(arrow_line.css("left")) + scroll_left)

    def is_int(self, value):
        try:
            int(value)
            return True
        except:
            return False

    def edited(self, script):
        self.set(script)
        
    def get_input_cells(self):
        return {
            key: self.sheet.cache.get(key, 0)
            for key in self.inputs
        }

    def should_run_locally(self):
        return "# no-worker" in self.model.script
        
    def is_formula(self):
        return isinstance(self.model.script, str) and self.model.script and self.model.script[0] == "="

    def evaluate(self):
        script = self.model.script
        expression = script[1:] if self.is_formula() else script
        state.console.remove(self.model.key)
        if self.is_formula():
            if self.should_run_locally():
                self.evaluate_locally(expression, self.get_input_cells())
            else:
                self.resolve_inputs()
        else:
            self.update(0, self.model.script)
        
    def evaluate_locally(self, script, inputs={}):
        inputs["pysheets"] = api.PySheets(self.sheet, self.sheet.cache)
        start = ltk.get_time()
        try:
            exec(api.intercept_last_expression(script), inputs)
        except Exception as e:
            state.console.write(self.model.key, f"[Error] {self.model.key}: {e}")
            return
        duration = ltk.get_time() - start
        value = inputs["_"]
        self.sheet.cache[self.model.key] = convert(value)
        self.update(duration, value)
    
    def show_loading(self):
        if state.worker_version != constants.WORKER_LOADING:
            return
        text = self.text()
        if not text.startswith(constants.ICON_HOUR_GLASS):
            self.text(f"{constants.ICON_HOUR_GLASS} {text}")

    def resolve_inputs(self):
        if self.running:
            return
        self.running = True
        ltk.publish(
            "Application",
            "Worker",
            constants.TOPIC_WORKER_FIND_INPUTS,
            {
                "key": self.model.key, 
                "script": self.model.script[1:]
            },
        )
        # result will arrive in handle_inputs

    def inputs_missing(self):
        for key in self.inputs:
            cell = self.sheet.get_cell(key)
            if cell.is_formula() and not self.sheet.counts[key]:
                return True

    def set_inputs(self, inputs):
        self.running = False
        self.inputs = inputs
        for key in self.get_input_cells():
            cell = self.sheet.get_cell(key)
            cell.dependents.add(self.model.key)

    def handle_inputs(self, inputs):
        self.running = False
        if self.model.key in inputs:
            self.report_cycle(inputs)
        self.set_inputs(inputs)
        if self.inputs_missing():
            return
        self.sheet.counts[self.model.key] += 1
        self.needs_worker = True
        self.show_loading()
        ltk.publish(
            "Application",
            "Worker",
            ltk.TOPIC_WORKER_RUN,
            [self.model.key, self.model.script[1:], self.get_input_cells()]
        )
        # result will arrive in handle_worker_result

    def handle_worker_result(self, result):
        self.running = False
        if self.model.script == "":
            self.update(0, "")
            return
        if result["error"]:
            error = result["error"]
            duration = result["duration"]
            lineno = result["lineno"]
            tb = result["traceback"]
            parts = error.split("'")
            if len(parts) == 3 and parts[0] == "name " and parts[2] == " is not defined":
                key = parts[1]
                if key in self.inputs:
                    # The worker job ran out of sequence, ignore this error for now
                    return
            self.update(duration, error)
            if self.sheet.current.model.key == self.model.key:
                main_editor.mark_line(lineno)
            last_tb_lines = "\n".join(tb.split("\n")[-2:])
            state.console.write(self.model.key, f"[Error] {self.model.key}: Line {lineno}: {last_tb_lines}")
            return
        value = result["value"]
        if isinstance(value, str):
            value = value[1:-1] if value.startswith("'") and value.endswith("'") else value
        self.update(result["duration"], value)
        self.notify()

    def __repr__(self):
        return f"cell[{self.model.key}]"


def hide_marker(event):
    selection.remove_arrows()


def create_marker(cells, clazz, seen):
    if not cells:
        return
    if len(cells) == 1:
        cells[0].draw_arrows(seen)
        return cells[0]
    top, left, bottom, right = 10000, 10000, 0, 0
    for cell in cells:
        position = cell.position()
        left = min(position.left, left)
        top = min(position.top, top) 
        right = max(position.left + cell.outerWidth(), right)
        bottom = max(position.top + cell.outerHeight(), bottom)
    return (ltk.Div()
        .addClass("marker")
        .addClass(clazz)
        .css("left", left)
        .css("top", top)
        .width(round(right - left - 4))
        .height(round(bottom - top - 5))
        .on("mousemove", proxy(hide_marker))
        .appendTo(ltk.find(".sheet-grid"))
    )


def take_screenshot(callback):
    if state.sheet.screenshot:
        callback(state.sheet.screenshot)
        return
    
    def done(screenshot):
        state.sheet.screenshot = screenshot
        callback(screenshot)

    def fail(error):
        window.console.orig_log(error)
        state.console.write("screenshot", f"[Error] Cannot take screenshot: {error}")
        done(get_plot_screenshot())

    try:
        if len(sheet.model.cells) > 300:
            done(get_plot_screenshot())
        else:
            options = ltk.to_js({
                "width": 200 * 4,
                "height": 150 * 4,
                "x": 0,
                "y": 48,
                "scale": 0.25,
            })
            window.html2canvas(window.document.body, options) \
                .then(ltk.proxy(lambda canvas: done(canvas.toDataURL()))) \
                .catch(ltk.proxy(fail))
    except Exception as e:
        fail(e)


def get_plot_screenshot():
    src = ltk.find(".preview img").attr("src")
    return src if isinstance(src, str) else "/screenshot.png"


def clear_name(event):
    if ltk.find("#title").val() == "Untitled Sheet":
        ltk.find("#title").val("")


def reset_name(event):
    if ltk.find("#title").val() == "":
        ltk.find("#title").val("Untitled Sheet")


def set_name(event):
    sheet.model.name = ltk.find("#title").val()


ltk.find("#title") \
    .on("focus", proxy(clear_name)) \
    .on("blur", proxy(reset_name)) \
    .on("change", proxy(set_name))


def update_cell(event=None):
    script = main_editor.get()
    cell = sheet.current
    cell.model.prompt = ltk.find("#ai-prompt").val()
    if cell and cell.model.script != script:
        cell.set(script)
        cell.evaluate()
    sheet.sync()


main_editor = editor.Editor()
main_editor.attr("id", "editor").css("overflow", "hidden").on(
    "change", proxy(update_cell)
)


def reload_with_packages(packages):
    host = f"{window.location.protocol}//{window.location.host}"
    args = [
        f"{constants.PYTHON_PACKAGES}={packages}",
        f"{constants.SHEET_ID}={state.uid}",
    ]
    window.location = f"{host}?{'&'.join(args)}"


def save_packages(event):
    packages = " ".join(ltk.find("#packages").val().replace(",", " ").split())
    reload_with_packages(packages)


def clear_prompt():
    ltk.find("#ai-prompt").val("")


def add_prompt(extra_text):
    prompt = ltk.find("#ai-prompt").val()
    newline = '\n' if prompt else ''
    ltk.find("#ai-prompt").val(f"{prompt}{newline}{extra_text}")

def run_current(event=None):
    selection.remove_arrows()
    sheet.current.evaluate()

def complete_prompt(event=None):
    if not ltk.find("#ai-prompt").val():
        ltk.window.alert("Please enter a prompt and then press 'generate code' again.")
    elif not main_editor.get() and "AI-generated" in main_editor.get():
        ltk.window.alert("Please select an empty cell and press 'generate code' again.")
    else:
        ltk.find("#ai-prompt").prop("disabled", "true"),
        ltk.find("#ai-generate").attr("disabled", "true"),
        main_editor.set("Loading...")
        prompt = ltk.find("#ai-prompt").val()
        request_completion(sheet.current.model.key, prompt)
        ltk.schedule(check_completion, "check-openai", 5)

def load_from_web(event=None):
    insert_prompt("""
Load a sheet from the following URL:
"https://chrislaffra.com/forbes_ai_50_2024.csv".
To load the sheet call "pysheets.load_sheet(url)".
Return the result as the last expression in the code.
    """.strip())


def create_sheet_view(model):
    global sheet
    def resize_ai(*args):
        selection.remove_arrows()
        main_editor.refresh()

    def resize_editor(*args):
        selection.remove_arrows()
        main_editor.refresh()

    def show_reload_button(event=None):
        ltk.find("#reload-button").css("display", "block").addClass("small-button")

    ltk.schedule(main_editor.refresh, "refresh editor", 3)
    sheet = SpreadsheetView(model)

    packages = ltk.get_url_parameter(constants.PYTHON_PACKAGES)
    console = ltk.VBox(
        ltk.HBox(
            ltk.Input("")
                .addClass("console-filter")
                .attr("placeholder", "Filter the console..."),
            ltk.Button("clear", proxy(lambda event: state.console.clear()))
                .addClass("console-clear")
                .attr("title", "Clear the console")
        ),
        ltk.Div(ltk.Table()).addClass("console"),
    ).addClass("console-container internals").attr("name", "Console")

    tabs = ltk.Tabs(
        console,
        ltk.VBox().addClass("timeline-container").attr("name", "Timeline"),
    ).addClass("internals")

    def set_plot_kind(index, option):
        add_prompt(f"When you create the plot, make it {list(chart_options.values())[index]}.")

    chart_options = {
        "bar": "a bar graph",
        "barh": "a horizontal bar graph",
        "line": "a line plot",
        "pie": "a pie chart",
        "stem": "a stem plot",
        "stairs": "a stairs graph",
        "scatter": "a scatter plot",
        "stack": "a stack plot",
        "fill": "a fill between graph",
    }
    chart_type = ltk.Select([ltk.Option(kind) for kind in chart_options], 0, ltk.proxy(set_plot_kind))

    ai = ltk.VBox(
        ltk.HBox(
            ltk.Text().text("LLM Prompt")
                .css("margin-right", 8),
            ltk.Button("generate code", proxy(complete_prompt))
                .addClass("small-button")
                .attr("id", "generate-button"),
            ltk.Button("load from web", proxy(load_from_web))
                .addClass("small-button")
                .attr("id", "load-from-web-button"),
            ltk.HBox().addClass("ai-button-container"),
            ltk.Text().text("Chart type:"),
            chart_type,
        ).addClass("ai-header"),
        ltk.TextArea(
        ).attr("id", "ai-prompt").addClass("ai-prompt").attr("placeholder", "Enter your prompt here..."),
    ).addClass("ai-container").on("resize", proxy(resize_ai))

    editor = ltk.VBox(
        ltk.HBox(
            ltk.Text().attr("id", "selection")
                .text("f(x)")
                .css("width", 70),
            ltk.HBox(
                ltk.Text("Packages:"),
                ltk.Input("")
                    .attr("id", "packages")
                    .css("width", 150)
                    .on("keyup", proxy(show_reload_button))
                    .val(packages),
                ltk.Button("Reload", proxy(save_packages))
                    .attr("id", "reload-button")
                    .css("display", "none"),
                ltk.Button("run script", proxy(run_current))
                    .addClass("small-button toolbar-button")
                    .attr("id", "run-button"),
            ).addClass("packages-container"),
        ),
        main_editor,
    ).addClass("editor-container").on("resize", proxy(resize_editor))


    ltk.inject_css(html_maker.make_css(sheet.model))
    left_panel = ltk.Div(
        ltk.Div(
            ltk.jQuery(html_maker.make_html(sheet.model))
        ).attr("id", "sheet-scrollable")
    ).attr("id", "sheet-container")

    editor_and_tabs = ltk.VerticalSplitPane(
        editor,
        tabs if state.pyodide else console,
        "editor-and-console",
    )
    right_panel = ltk.VerticalSplitPane(
        ai,
        editor_and_tabs,
        "ai-and-editor",
    ).addClass("right-panel")

    if state.mobile():
        ltk.find("#main").prepend(
            ltk.VerticalSplitPane(
                left_panel,
                right_panel.addClass("right-panel"),
                "sheet-and-editor",
            ).css("height", "100%")
        )
    else:
        ltk.find("#main").empty().prepend(
            ltk.HorizontalSplitPane(
                left_panel.css("width", "70%"),
                right_panel.css("width", "30%"),
                "sheet-and-editor",
            ).css("height", "calc(100vh - 51px)")
        )
    if not ltk.find("#A1").length:
        raise ValueError("Error: PySheets setup problem, cannot find cell A1")
    ltk.schedule(editor_and_tabs.layout, "layout editor")
    window.adjustSheetPosition()
    sheet.post_load()


def create_top():
    sheet.setup_selection()
    ltk.find("#menu").empty().append(menu.create_menu(sheet))
    ltk.find("#main").focus()
    create_attribute_editors()


def create_attribute_editors():
    def set_font(index, option):
        sheet.multi_selection.css("font-family", option.text())

    def set_font_size(index, option):
        sheet.multi_selection.css("font-size", f"{option.text()}px")

    def set_font_weight(index, option):
        sheet.multi_selection.css("font-weight", option.text())

    def set_font_style(index, option):
        sheet.multi_selection.css("font-style", option.text())

    def set_color(event):
        color = ltk.find(event.target).val()
        sheet.multi_selection.css("color", color)
        ltk.find(event.target).css("background-color", color)
        event.preventDefault()

    def set_background(event):
        color = ltk.find(event.target).val()
        sheet.multi_selection.css("background-color", color)
        ltk.find(event.target).css("background-color", color)
        event.preventDefault()

    def set_vertical_align(index, option):
        sheet.multi_selection.css("vertical-align", option.text())

    def set_text_align(index, option):
        sheet.multi_selection.css("text-align", option.text())
                   
    def activate_fill_colorpicker(event):
        container = ltk.find(event.target)
        container.parent().find(".cell-fill-colorpicker").click()
                   
    def activate_color_colorpicker(event):
        container = ltk.find(event.target)
        container.parent().find(".cell-color-colorpicker").click()

    ltk.find("#cell-attributes-container").empty().append(

        ltk.Span(
            ltk.ColorPicker()
                .on("input", proxy(set_background))
                .val("#ffffff")
                .attr("id", "cell-fill")
                .addClass("cell-fill-colorpicker"),
            ltk.jQuery('<img src="/icons/format-color-fill.png">')
                .on("click", proxy(activate_fill_colorpicker))
                .addClass("cell-fill-icon"),
        ).addClass("cell-fill-container"),

        ltk.Span(
            ltk.ColorPicker()
                .on("input", proxy(set_color))
                .val("#ffffff")
                .attr("id", "cell-color")
                .addClass("cell-color-colorpicker"),
            ltk.jQuery('<img src="/icons/format-color-text.png">')
                .on("click", proxy(activate_color_colorpicker))
                .addClass("cell-color-icon"),
        ).addClass("cell-color-container"),

        ltk.Select(constants.FONT_NAMES, "Arial", set_font).attr(
            "id", "cell-font-family"
        ),
        ltk.Select(map(str, constants.FONT_SIZES), "12", set_font_size).attr(
            "id", "cell-font-size"
        ),
        ltk.Select(["normal", "italic"], "normal", set_font_style).attr(
            "id", "cell-font-style"
        ),
        ltk.Select(["normal", "bold"], "normal", set_font_weight).attr(
            "id", "cell-font-weight"
        ),
        ltk.Select(["top", "middle", "bottom"], "bottom", set_vertical_align).attr(
            "id", "cell-vertical-align"
        ),
        ltk.Select(["left", "center", "right"], "right", set_text_align).attr(
            "id", "cell-text-align"
        ),
    ).css("opacity", 0).animate(ltk.to_js({ "opacity": 1 }), constants.ANIMATION_DURATION)
    state.console.setup()


def logout(event=None):
    state.logout()
    menu.go_home()


def setup():
    def load_sheet(model):
        create_sheet_view(model)
        state.sheet = model
    if state.uid:
        state.clear()
        storage.load(state.uid, load_sheet)
    else:
        inventory.list_sheets()


def cleanup_completion(text):
    if "import matplotlib" in text:
        lines = text.split("\n")
        for line in lines[:]:
            if line.startswith("#") or line.startswith("import"):
                return "\n".join(lines)
            lines.pop(0)
    return text


def request_completion(key, prompt):
    ltk.publish(
        "Application",
        "Worker",
        constants.TOPIC_WORKER_COMPLETE,
        {
            "key": key, 
            "prompt": prompt,
        },
    )
    # the answer will arrive in handle_completion_request
        

def handle_completion_request(completion):
    try:
        import json
        key = completion["key"]
        text = completion["text"]
        prompt = completion["prompt"]
        text = cleanup_completion(text)
        text = f"# This code was generated by an AI. Please check it for errors.\n\n{text.strip()}"

        if ltk.find("#ai-text").length:
            ltk.find("#ai-text").text(text)
            ltk.find("#ai-insert").removeAttr("disabled")
            return

        completion_cache[key] = text
        main_editor.set(f"=\n{text}")
        set_random_color()
        update_cell()
        run_current()
    except Exception as e:
        state.console.write("ai-complete", "[Error] Could not handle completion from OpenAI...", e)
        state.print_stack(e)
    finally:
        ltk.find("#ai-prompt").prop("disabled", ""),
        ltk.find("#ai-generate").attr("disabled", ""),


def set_random_color():
    color = f"hsla({(360 * random.random())}, 70%,  72%, 0.8)"
    cell = sheet.current
    cell.css("background-color", color)
    sheet.selection.css("background-color", color)
    _style = cell.model.style.copy()
    cell.model.style["background-color"] = color
    history.add(models.CellStyleChanged(cell.model.key, _style, cell.model.style).apply(sheet.model))


def check_completion():
    if ltk.find("#ai-text").text() == "Loading...":
        ltk.find("#ai-generate").removeAttr("disabled")
        ltk.find("#ai-insert").attr("disabled", "true"),
        ltk.find("#ai-text").text("It looks like OpenAI is overloaded. Please try again.")


def insert_prompt(prompt):
    clear_prompt()
    add_prompt(prompt.strip())
    complete_prompt()


def add_completion_button(key, handler):
    if ltk.find(f"#completion-{key}").length:
        return

    def run(event):
        handler()
        ltk.schedule(sheet.sync, "find-ai-suggestions", 1)
        
    ltk.find(".ai-button-container").append(
        ltk.Button(f"{constants.ICON_STAR} {key}", proxy(run))
            .addClass("small-button toolbar-button")
            .attr("id", f"completion-{key}")
    )


def sheet_resized():
    sheet.multi_selection.draw()
    sheet.select(sheet.current)


def column_resizing(event):
    label = ltk.find(event.target)
    column = label.attr('col')
    ltk.find(f".cell.col-{column}").css("width", round(label.width()))
    sheet_resized()

def column_resized(event):
    label = ltk.find(event.target)
    column = label.attr('col')
    width = round(label.width())
    history.add(models.ColumnChanged(int(column), width).apply(sheet.model))


def row_resizing(event):
    label = ltk.find(event.target)
    row = label.attr('row')
    ltk.find(f".cell.row-{row}").css("height", round(label.height()))
    sheet_resized()

def row_resized(event):
    label = ltk.find(event.target)
    row = int(label.attr('row'))
    height = round(label.height())
    history.add(models.RowChanged(row, height).apply(sheet.model))


window.columnResizing = ltk.proxy(column_resizing)
window.columnResized = ltk.proxy(column_resized)
window.rowResizing = ltk.proxy(row_resizing)
window.rowResized = ltk.proxy(row_resized)

worker = state.start_worker()

def handle_code_completion(completions):
    main_editor.handle_code_completion(completions)


def handle_inputs(data):
    cell = sheet.get_cell(data["key"])
    cell.handle_inputs(data["inputs"])


def main():
    ltk.inject_css("pysheets.css")
    ltk.subscribe(constants.PUBSUB_SHEET_ID, constants.TOPIC_WORKER_COMPLETION, handle_completion_request)
    ltk.subscribe(constants.PUBSUB_SHEET_ID, constants.TOPIC_WORKER_CODE_COMPLETION, handle_code_completion)
    ltk.subscribe(constants.PUBSUB_SHEET_ID, constants.TOPIC_WORKER_PRINT, print)
    ltk.subscribe(constants.PUBSUB_SHEET_ID, constants.TOPIC_WORKER_INPUTS, handle_inputs)
    ltk.subscribe(constants.PUBSUB_SHEET_ID, ltk.TOPIC_INFO, print)
    ltk.subscribe(constants.PUBSUB_SHEET_ID, ltk.TOPIC_ERROR, print)
    storage.setup(setup)


vm_version = sys.version.split()[0].replace(";", "")
minimized = "minimized" if __name__ != "pysheets" else "full"
message = f"[UI] Running {state.vm_type(sys.version)}; Python {vm_version}; UI startup took {ltk.get_time():.3f}s."
state.console.write("pysheets", message)


def convert(value):
    try:
        return float(value) if "." in value else int(value)
    except:
        return value if value else 0

