import ltk
import api
import collections
import constants
import history
import inventory
import login
import menu
import models
import preview
import timeline
import random
import selection
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
        self.post_load()

    def fill_cache(self):
        for model in self.model.cells.values():
            self.cache[model.key] = convert(model.value)

    def model_changed(self, sheet, info):
        field_name = info["name"]
        if field_name == "rows":
            ltk.find(f".row-{info['row']}").css("height", info['height'])
        if field_name == "columns":
            ltk.find(f".col-{info['column']}").css("width", info['width'])
        if field_name == "name":
            old_name = state.doc.name
            new_name = sheet.name
            if old_name != new_name:
                window.document.title = state.doc.name = new_name
                ltk.find("#title").val(new_name)
                history.add(models.NameChanged(old_name, new_name))
        sheet_resized()

    def get_cell(self, key):
        if key not in self.cell_views:
            self.cell_views[key] = CellView(self, key, self.model.get_cell(key))
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

    def show_column_menu(self, event):
        label = ltk.find(event.target)
        selected_column = int(label.attr("col")) - 1

        def insert_column(event):
            for cell in sorted(self.cells.values(), key=lambda cell: -cell.model.column):
                if cell.model.column >= selected_column:
                    next_key = models.get_key_from_col_row(cell.model.column + 1, cell.model.row)
                    self.copy(cell, self.get_cell(next_key, cell.model.column + 1, cell.model.row))
                if cell.model.column == selected_column:
                    cell.clear()
                if cell.model.column > 1:
                    previous_key = models.get_key_from_col_row(cell.model.column - 1, cell.model.row)
                    if not previous_key in self.cells:
                        cell.clear()

        def delete_column(event):
            for cell in sorted(self.cells.values(), key=lambda cell: cell.model.column):
                next_key = models.get_key_from_col_row(cell.model.column + 1, cell.model.row)
                if cell.model.column >= selected_column:
                    if not next_key in self.cells:
                        cell.clear()
                    self.copy(self.get_cell(next_key, cell.model.column + 1, cell.model.row), cell)

        ltk.MenuPopup(
            ltk.MenuItem("+", f"insert column", None, proxy(insert_column)),
            ltk.MenuItem("-", f"delete column {models.get_column_name(selected_column)}", None, proxy(delete_column)),
        ).show(label)
        event.preventDefault()

    def show_row_menu(self, event):
        label = ltk.find(event.target)
        selected_row = int(label.attr("row")) - 1

        def insert_row(event):
            for cell in sorted(self.cells.values(), key=lambda cell: -cell.model.row):
                if cell.model.row >= selected_row:
                    next_key = models.get_key_from_col_row(cell.model.column, cell.model.row + 1)
                    self.copy(cell, self.get_cell(next_key, cell.model.column + 1, cell.model.row))
                if cell.model.row == selected_row:
                    cell.clear()
                if cell.model.row > 1:
                    previous_key = models.get_key_from_col_row(cell.model.column, cell.model.row - 1)
                    if not previous_key in self.cells:
                        cell.clear()

        def delete_row(event):
            for cell in sorted(self.cells.values(), key=lambda cell: cell.model.row):
                next_key = models.get_key_from_col_row(cell.model.column, cell.model.row + 1)
                if cell.model.row >= selected_row:
                    if not next_key in self.cells:
                        cell.clear()
                    self.copy(self.get_cell(next_key, cell.model.column + 1, cell.model.row), cell)

        ltk.MenuPopup(
            ltk.MenuItem("+", f"insert row", None, proxy(insert_row)),
            ltk.MenuItem("-", f"delete row {selected_row + 1} ", None, proxy(delete_row)),
        ).show(label)
        event.preventDefault()

    def handle_worker_result(self, result):
        key = result["key"]
        preview.add(self, key, result["preview"])
        cell = self.get_cell(key)
        cell.running = False
        if result["error"]:
            error = result["error"]
            duration = result["duration"]
            tb = result["traceback"]
            parts = error.split("'")
            if len(parts) == 3 and parts[0] == "name " and parts[2] == " is not defined":
                key = parts[1]
                if key in cell.inputs:
                    # The worker job ran out of sequence, ignore this error for now
                    return
            cell.update(duration, error)
            state.console.write(key, f"[Error] {key}: {error} {tb}")
            return
        if not cell.model.script:
            return
        value = result["value"]
        if isinstance(value, str):
            value = value[1:-1] if value.startswith("'") and value.endswith("'") else value
        cell.update(result["duration"], value)
        cell.find_inputs(cell.model.script)
        cell.notify()

    def post_load(self):
        ltk.find("#main").focus().on("keydown", proxy(lambda event: self.navigate(event)))
        ltk.find(".hidden").removeClass("hidden")
        url_packages = ltk.get_url_parameter(constants.DATA_KEY_PACKAGES)
        if window.packages and not url_packages:
            reload_with_packages(window.packages)
        state.doc.name = window.document.title = window.name
        state.set_title(state.doc.name)
        current = window.selected
        if window.runtime == "py":
            ltk.find("#run-in-main").prop("checked", True)
        ltk.schedule(lambda: self.select(self.get_cell(current)), "select-later", 0.1)
        ltk.find(".main-editor-container").width(window.editor_width)
        ltk.find(".sheet").css("cursor", "default")
        self.show_loading()
        preview.load(self)
    
    def run_ai(self):
        ltk.schedule(self.find_frames, "find frames", 1)
        ltk.schedule(self.find_urls, "find urls", 1)

    def sync(self):
        ltk.schedule(self.check_edits, "check edits", 0.5)

    def check_edits(self):
        def handle_edits(groups):
            for group in groups:
                try:
                    for edit_dict in eval(group[constants.DATA_KEY_EDITS]):
                        class_name = edit_dict["_class"]
                        del edit_dict["_class"]
                        del edit_dict["_listeners"]
                        edit = globals()[class_name](**edit_dict)
                        if isinstance(edit, models.CellChanged):
                            _ = self.get_cell(edit.key)
                        edit.apply(sheet.model)
                except Exception as e:
                    print("ERROR EVAL", e, group[constants.DATA_KEY_EDITS])
                    state.print_stack(e)
        history.sync_edits(handle_edits)

    def find_frames(self):
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
Convert the spreadsheet cells in range "{cell_model.key}:{other_key}" into a Pandas dataframe.
To load a Dataframe from cells, use "pysheets.sheet(range)".
Make the last expression refer to the dataframe.
The pysheets module is already imported.
Generate Python code.
"""
            text = f"""
# Create a Pandas DataFrame from values found in the current sheet
pysheets.sheet("{cell_model.key}:{other_key}")
"""
            add_completion_button(cell_model.key, lambda: insert_completion(cell_model.key, prompt, text, { "total": 0 }))

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
        # history.add(models.SelectionChanged(key=self.current.model.key))
        pass

    def find_urls(self):
        for key in self.get_url_keys():
            prompt = f"""
Load the data URL already stored in variable {key} into a Pandas Dataframe.
To load a Dataframe from a url, use "pysheets.load_sheet(url)".
Make the last expression refer to the dataframe.
Generate Python code.
"""
            request_completion(key, prompt.strip())

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
            ltk.schedule(self.sync, "check edits", 1)
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

        def show_menu(event):
            return
            div = ltk.find(event.target).closest(".cell")
            key = div.attr("id")
            col = int(div.attr("col"))
            row = int(div.attr("row"))
            cell = self.get_cell(key, col, row)
            if not cell:
                return
            event.preventDefault()

        ltk.find("#sheet") \
            .on("mousedown", proxy(mousedown)) \
            .on("mousemove", proxy(mousemove)) \
            .on("mouseup", proxy(mouseup)) \
            .on("contextmenu", proxy(show_menu))

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

    def select(self, cell):
        if not cell or not cell.hasClass("cell"):
            print("Not a cell", cell)
            return
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
        self.current = cell

    def show_loading(self):
        for key, cell in self.model.cells.items():
            if cell.script.startswith("="):
                self.get_cell(key).show_loading()

    def worker_ready(self, data):
        for key, cell in self.model.cells.items():
            if cell.script.startswith("="):
                self.get_cell(key).worker_ready()
        self.sync()

    def save_file(self, done=lambda response: None):
        def handle_screenshot(screenshot):
            self.save_screenshot(screenshot, done)
        take_screenshot(handle_screenshot)
 
    def save_screenshot(self, screenshot=None, done=lambda response: None):
        history.add(models.ScreenshotChanged(url=screenshot or state.doc.screenshot))


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
        self.find_inputs(self.model.script)
        self.setup_listener()
        
    def setup_listener(self):
        self.model.listen(self.model_changed)

    def model_changed(self, model, info):
        if info["name"] == "script":
            self.set(model.script)
        if info["name"] == "value":
            self.text(model.value)
        if info["name"] == "style":
            self.css(model.style)
        
    def enter(self):
        self.draw_cell_arrows()
        self.raise_preview()
    
    def set(self, script, evaluate=True):
        if self.model.script != script:
            history.add(models.CellScriptChanged(self.model.key, self.model.script, script))
            self.model.script = script
            self.find_inputs(script)
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
                speed = '🐌' if duration > 1.0 else '🚀'
                if isinstance(value, str) and not "Error" in value:
                    state.console.write(
                        self.model.key,
                        f"[DAG] {self.model.key}: Ran in worker {count} time{'s' if count > 1 else ''}, last run took {duration:.3f}s {speed}"
                    )
        self.text(str(value))
        if self.model.value != value and self.model.script != value:
            history.add(models.CellValueChanged(self.model.key, self.model.value, value))
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

    def find_inputs(self, script):
        for input in self.inputs:
            self.sheet.get_cell(input).dependents.remove(self.model.key)
        if not isinstance(script, str) or not script or script[0] != "=" or "no-inputs" in script:
            return
        # TODO: sort first and last by min/max col/row
        self.inputs = set()
        index = 0
        is_col = lambda c: c >= "A" and c <= "Z"
        is_row = lambda c: c.isdigit()
        string = self.model.script[1:]
        while index < len(string):
            c = string[index]
            if is_col(string[index]):
                start = index
                while index < len(string) and is_col(string[index]):
                    index += 1
                if index < len(string) and is_row(string[index]):
                    while index < len(string) and is_row(string[index]):
                        index += 1
                    key = string[start:index]
                    if start > 0 and string[start - 1] == ":" and self.inputs:
                        keys = self.get_input_range(self.inputs.pop(), key)
                    else:
                        keys = set([key])
                    for key in keys:
                        if key != self.model.key:
                            self.inputs.add(key)
                            self.sheet.get_cell(key).dependents.add(self.model.key)
            index += 1

    def get_input_range(self, start, end):
        start_col, start_row = models.get_col_row_from_key(start)
        end_col, end_row = models.get_col_row_from_key(end)
        return [
            models.get_key_from_col_row(col, row)
            for row in range(start_row, end_row + 1)
            for col in range(start_col, end_col + 1)
        ]

    def select(self):
        self.remove_arrows()
        if self.sheet.current and self.sheet.current is not self:
            ltk.schedule(lambda: self.sheet.save_current_position(), "save selection", 3)
        self.sheet.current = self
        main_editor.set(self.model.script)
        ltk.find("#selection").text(f"Cell: {self.model.key}")
        ltk.find("#cell-attributes-container").css("display", "block")

        try:
            self.set_css_editors()
        except Exception as e:
            pass

        selection.scroll(self)

    def set_css_editors(self):
        ltk.find("#cell-font-family").val(self.css("font-family") or constants.DEFAULT_FONT_FAMILY)
        ltk.find("#cell-font-size").val(round(window.parseFloat(self.css("font-size"))) or constants.DEFAULT_FONT_SIZE)
        ltk.find("#cell-font-color").val(rgb_to_hex(self.css("color")) or constants.DEFAULT_COLOR)
        ltk.find("#cell-fill").val(rgb_to_hex(self.css("background-color")) or constants.DEFAULT_FILL)
        ltk.find("#cell-vertical-align").val(self.css("vertical-align") or constants.DEFAULT_VERTICAL_ALIGN)
        ltk.find("#cell-text-align").val(self.css("text-align").replace("start", "left") or constants.DEFAULT_TEXT_ALIGN)
        ltk.find("#cell-font-weight").val({"400": "normal", "700": "bold"}[self.css("font-weight")] or constants.DEFAULT_FONT_WEIGHT)
        ltk.find("#cell-font-style").val(self.css("font-style") or constants.DEFAULT_FONT_STYLE)

    def clear(self):
        self.inputs = set()
        self.dependents = set()
        self.text("")

        self.css("font-family", constants.DEFAULT_FONT_FAMILY)
        self.css("font-size", constants.DEFAULT_FONT_SIZE)
        self.css("font-style", constants.DEFAULT_FONT_STYLE)
        self.css("color", constants.DEFAULT_COLOR)
        self.css("background-color", constants.DEFAULT_FILL)
        self.css("vertical-align", constants.DEFAULT_VERTICAL_ALIGN)
        self.css("font-weight", constants.DEFAULT_FONT_WEIGHT)
        self.css("text-align", constants.DEFAULT_TEXT_ALIGN)

        ltk.find(f"#preview-{self.model.key}").remove()
        ltk.find(f"#completion-{self.model.key}").remove()
        state.console.remove(f"ai-{self.model.key}")
        self.model.clear()
        if self.model.key in self.sheet.cells:
            del self.sheet.cells[self.model.key]
        if self.model.key in self.sheet.model.previews:
            history.add(models.PreviewDeleted(key=self.model.key))
        history.add(models.CellScriptChanged(key=self.model.key, script=""))
        history.add(models.CellValueChanged(key=self.model.key, value=""))
        history.add(models.CellStyleChanged(key=self.model.key, style={}))

    def draw_cell_arrows(self):
        self.draw_arrows()
        self.adjust_arrows()
    
    def raise_preview(self):
        preview = ltk.find(f"#preview-{self.model.key}")
        preview.appendTo(preview.parent())

    def remove_arrows(self):
        selection.remove_arrows()

    def draw_arrows(self):
        self.remove_arrows()
        if state.mobile():
            return
        if not self.inputs:
            return
        cells = [ self.sheet.get_cell(input) for input in self.inputs ]
        window.addArrow(create_marker(cells, "inputs-marker arrow"), self.element)
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

    def evaluate(self):
        script = self.model.script
        is_formula = isinstance(script, str) and script and script[0] == "="
        expression = api.edit_script(script[1:]) if is_formula else script
        state.console.remove(self.model.key)
        if is_formula:
            try:
                if not "# worker" in self.model.script and (state.pyodide or "# no-worker" in self.model.script):
                    self.evaluate_locally(expression)
                else:
                    raise Exception("only run in worker")
            except Exception as e:
                if state.pyodide:
                    state.console.write(self.model.key, f"[Error] {self.model.key}: {e}")
                if "no-worker" in self.model.script:
                    state.console.write(self.model.key, f"[Error] {self.model.key}: {e}")
                    self.update(0, str(e))
                else:
                    self.evaluate_in_worker(expression)
        else:
            self.update(0, self.model.script)
        
    def evaluate_locally(self, expression):
        inputs = {}
        inputs["pysheets"] = api.PySheets(self.sheet, self.sheet.cache)
        inputs.update(self.sheet.cache)
        start = ltk.get_time()
        exec(expression, inputs)
        duration = ltk.get_time() - start
        value = inputs["_"]
        self.sheet.cache[self.model.key] = convert(value)
        self.update(duration, value)
    
    def show_loading(self):
        text = self.text()
        if not text.startswith(constants.ICON_HOUR_GLASS):
            self.text(f"{constants.ICON_HOUR_GLASS} {text}")

    def evaluate_in_worker(self, expression):
        if self.running:
            return
        self.sheet.counts[self.model.key] += 1
        self.running = True
        self.needs_worker = True
        self.show_loading()
        inputs = dict(
            (key,value)
            for key, value in self.sheet.cache.items()
            if key != self.model.key
        )
        ltk.publish(
            "Application",
            "Worker",
            ltk.TOPIC_WORKER_RUN,
            [self.model.key, expression, inputs]
        )

    def __repr__(self):
        return f"cell[{self.model.key}]"


def hide_marker(event):
    selection.remove_arrows()


def create_marker(cells, clazz):
    if not cells:
        return
    if len(cells) == 1:
        cells[0].draw_arrows()
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


def check_network():
    if ltk.find(".cell").length == 0:
        state.console.write("network-status", "[I/O] Error: Cannot reach PySheet's document storage ️️🤬🤬🤬. Try reloading the page...")


def email_to_class(email):
    return email.replace("@", "-").replace(".", "-")


def remove_marker(email):
    ltk.find(f".marker-{email_to_class(email)}").remove()


def take_screenshot(callback):
    if state.doc.screenshot:
        callback(state.doc.screenshot)
        return
    
    def done(screenshot):
        state.doc.screenshot = screenshot
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


def set_name(event):
    sheet.model.name = ltk.find("#title").val()


ltk.find("#title").on("change", proxy(set_name))


def update_cell(event=None):
    script = main_editor.get()
    cell = sheet.current
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
        f"{constants.DATA_KEY_PACKAGES}={packages}",
        f"{constants.DATA_KEY_RUNTIME}={'pyodide' if ltk.find('#run-in-main').prop('checked') else 'micropython'}",
        f"{constants.DATA_KEY_UID}={state.doc.uid}",
    ]
    window.location = f"{host}?{'&'.join(args)}"


def save_packages(event):
    packages = " ".join(ltk.find("#packages").val().replace(",", " ").split())
    sheet.save_file(lambda: reload_with_packages(packages))


def create_sheet(model):
    if not state.user.token:
        return SpreadsheetView(Sheet())

    def resize_editor(*args):
        selection.remove_arrows()
        main_editor.refresh()

    def run_in_main(event):
        show_button()
        ltk.find("#run-in-main").prop("checked", ltk.find(event.target).prop("checked"))

    def show_button(event=None):
        ltk.find("#reload-button").css("display", "block").addClass("small-button")

    def run_current(event=None):
        selection.remove_arrows()
        sheet.current.evaluate()

    sheet = SpreadsheetView(model)

    packages = ltk.get_url_parameter(constants.DATA_KEY_PACKAGES)

    console = ltk.VBox(
        ltk.HBox(
            ltk.Input("")
                .addClass("console-filter")
                .attr("placeholder", "filter the console"),
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
                    .on("keyup", proxy(show_button))
                    .val(packages),
                ltk.Switch("Run in main:", False)
                    .on("change", proxy(run_in_main))
                    .attr("id", "run-in-main") if not state.force_pyodide else ltk.Span(""),
                ltk.Button("Reload", proxy(save_packages))
                    .attr("id", "reload-button")
                    .css("display", "none"),
                ltk.Button("run", proxy(run_current))
                    .addClass("small-button toolbar-button")
                    .attr("id", "run-button"),
                ltk.Button(constants.ICON_STAR, proxy(lambda event: insert_completion(sheet.current.model.key if sheet.current else "", "", "", { "total": 0 })))
                    .addClass("small-button toolbar-button"),
            ).addClass("packages-container"),
        ),
        main_editor,
    ).addClass("editor-container").on("resize", proxy(resize_editor))

    left_panel = ltk.Div(
        ltk.Div(
            ltk.find(".sheet")
        ).attr("id", "sheet-scrollable")
    ).attr("id", "sheet-container")

    right_panel = ltk.VerticalSplitPane(
        editor,
        tabs if state.pyodide else console,
        "editor-and-console",
    ).addClass("right-panel")

    if state.mobile():
        ltk.find("#main").prepend(
            ltk.VerticalSplitPane(
                left_panel,
                right_panel.css("height", "30%"),
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
    window.adjustSheetPosition()
    ltk.schedule(create_top, "create top section", 0)
    return sheet


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
        sheet.multi_selection.css("color", ltk.find(event.target).val())
        event.preventDefault()

    def set_background(event):
        sheet.multi_selection.css("background-color", ltk.find(event.target).val())
        event.preventDefault()

    def set_vertical_align(index, option):
        sheet.multi_selection.css("vertical-align", option.text())

    def set_text_align(index, option):
        sheet.multi_selection.css("text-align", option.text())

    ltk.find("#cell-attributes-container").empty().append(
        ltk.ColorPicker()
        .on("input", proxy(set_background))
        .val("#ffffff")
        .attr("id", "cell-fill"),
        ltk.ColorPicker().on("input", proxy(set_color)).attr("id", "cell-font-color"),
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


def setup(model):
    global sheet
    if state.doc.uid:
        state.clear()
        sheet = create_sheet(model)
    elif state.user.token:
        inventory.list_sheets()
    else:
        state.set_title("")
        ltk.find("#login-container").css("display", "block")
    ltk.find("#main").animate(ltk.to_js({ "opacity": 1 }), constants.ANIMATION_DURATION)



def cleanup_completion(text):
    if "import matplotlib" in text:
        lines = text.split("\n")
        for line in lines[:]:
            if line.startswith("#") or line.startswith("import"):
                return "\n".join(lines)
            lines.pop(0)
    return text


def handle_completion_request(completion):
    try:
        import json
        key = completion["key"]
        text = completion["text"]
        prompt = completion["prompt"]
        if not "CompletionBudgetException" in text:
            text = cleanup_completion(text)
            text = f"# The following code is entirely AI-generated. Please check it for errors.\n\n{text}"

        if ltk.find("#ai-text").length:
            ltk.find("#ai-text").text(text)
            ltk.find("#ai-insert").removeAttr("disabled")
            return

        if sheet.model.cells[key].script == "":
            return
        completion_cache[key] = (text, completion.get("budget"))
        ltk.find(f"#completion-{key}").remove()
        text, budget = completion_cache[key]
        add_completion_button(key, lambda: insert_completion(key, prompt, text, budget))
    except Exception as e:
        state.console.write("ai-complete", "[Error] Could not handle completion from OpenAI...", e)
        state.print_stack(e)


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
        

def set_random_color():
    color = f"hsla({(360 * random.random())}, 70%,  72%, 0.8)"
    sheet.current.css("background-color", color)
    sheet.selection.css("background-color", color)


def check_completion():
    if ltk.find("#ai-text").text() == "Loading...":
        ltk.find("#ai-generate").removeAttr("disabled")
        ltk.find("#ai-insert").attr("disabled", "true"),
        ltk.find("#ai-text").text("It looks like OpenAI is overloaded. Please try again.")


def insert_completion(key, prompt, text, budget):
    def generate(event):
        ltk.find("#ai-budget").text(f"{100 - budget['total']} runs left.")
        ltk.find("#ai-text").text("Loading...")
        ltk.find("#ai-generate").attr("disabled", "true"),
        edited_prompt = ltk.find("#ai-prompt").val()
        request_completion(key, edited_prompt)
        ltk.schedule(check_completion, "check-openai", 5)

    def insert(event):
        text = ltk.find("#ai-text").text()
        if main_editor.get() == "":
            edited_prompt = ltk.find("#ai-prompt").val()
            text = f'=\n\nprompt = """\n{edited_prompt}\n"""\n\n{text}'
            main_editor.set(text).focus()
            update_cell()
            ltk.find("#completion-dialog").remove()
            set_random_color()
        else:
            ltk.find("#ai-message").text(
                "Please select an empty cell and try again."
            ).css("color", "red")
    
    def set_plot_kind(kind):
        add_prompt(f"When you create the plot, make it {kind}.")

    def add_prompt(extra_text):
        prompt = ltk.find("#ai-prompt").val()
        ltk.find("#ai-prompt").val(f"{prompt}\n\n{extra_text}")
        prompt_changed()

    def prompt_changed():
        ltk.find("#ai-generate").removeAttr("disabled")
        ltk.find("#ai-insert").attr("disabled", "true"),
        ltk.find("#ai-text").text("Click the Generate button to get a new completion...")

    extra_prompt_buttons = {
        constants.COMPLETION_KINDS_IMPORT: [
        ],
        constants.COMPLETION_KINDS_NONE: [
        ],
        constants.COMPLETION_KINDS_CHART: [
            ltk.Button("bar", proxy(lambda event: set_plot_kind("a bar graph"))),
            ltk.Button("barh", proxy(lambda event: set_plot_kind("a horizontal bar graph"))),
            ltk.Button("line", proxy(lambda event: set_plot_kind("a line plot"))),
            ltk.Button("pie", proxy(lambda event: set_plot_kind("a pie chart"))),
            ltk.Button("stem", proxy(lambda event: set_plot_kind("a stem plot"))),
            ltk.Button("stairs", proxy(lambda event: set_plot_kind("a stairs graph"))),
            ltk.Button("scatter", proxy(lambda event: set_plot_kind("a scatter plot"))),
            ltk.Button("stack", proxy(lambda event: set_plot_kind("a stack plot"))),
            ltk.Button("fill", proxy(lambda event: set_plot_kind("a fill between graph"))),
        ],
    }
    cell = sheet.get_cell(key)
    if cell.text() == "DataFrame":
        data_kind = constants.COMPLETION_KINDS_CHART
    elif cell.text().startswith("https:"):
        data_kind = constants.COMPLETION_KINDS_IMPORT
    else:
        data_kind = constants.COMPLETION_KINDS_NONE

    ltk.find("#completion-dialog").remove()
    ltk.VBox(
        ltk.HBox(
            ltk.Text("The prompts given to the AI:"),
            extra_prompt_buttons[data_kind],
        ),
        ltk.TextArea(prompt or "Generate Python code.")
            .attr("id", "ai-prompt")
            .on("keyup", proxy(lambda event: prompt_changed()))
            .css("height", 300),
        ltk.HBox(
            ltk.Button("Generate", proxy(generate))
                .attr("disabled", "true")
                .attr("id", "ai-generate"),
            ltk.Text("")
                .attr("id", "ai-budget"),
            ltk.Text("The latest AI generated completion:"),
        ),
        ltk.Preformatted()
            .attr("id", "ai-text")
            .text(text)
            .css("height", 300),
        ltk.HBox(
            ltk.Button("Insert into the Sheet", proxy(insert))
                .attr("id", "ai-insert"),
            ltk.Text("(you can always edit the code later)")
                .attr("id", "ai-message"),
        ),
    ).attr("id", "completion-dialog").dialog(ltk.to_js({
        "width": 700,
        "title": "PySheets ⭐ AI-Driven Code Generation",
    }))


def add_completion_button(key, handler):
    def run(event):
        handler()
        ltk.schedule(sheet.sync, "find-ai-suggestions", 1)
        
    ltk.find(f"#completion-{key}").remove()
    ltk.find(".packages-container").append(
        ltk.Button(f"{constants.ICON_STAR} {key}", proxy(run))
            .addClass("small-button toolbar-button")
            .attr("id", f"completion-{key}")
    )
    if key:
        cell = sheet.get_cell(key)
        cell_contents = api.shorten(cell.model.value, 12)
        message = f'[AI] AI suggestion available for [{key}: "{cell_contents}"]. {constants.ICON_STAR}'
        state.console.write(
            f"ai-{key}",
            message,
            action=ltk.Button(f"{constants.ICON_STAR}{key}", proxy(run)).addClass("small-button toolbar-button")
        )


def sheet_resized():
    ltk.find(".selection").remove()
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
    history.add(models.ColumnChanged(int(column), round(label.width())))


def row_resizing(event):
    label = ltk.find(event.target)
    row = label.attr('row')
    ltk.find(f".cell.row-{row}").css("height", round(label.height()))
    sheet_resized()

def row_resized(event):
    label = ltk.find(event.target)
    row = label.attr('row')
    history.add(models.RowChanged(int(row), round(label.height())))


window.columnResizing = ltk.proxy(column_resizing)
window.columnResized = ltk.proxy(column_resized)
window.rowResizing = ltk.proxy(row_resizing)
window.rowResized = ltk.proxy(row_resized)

worker = state.start_worker()

def handle_code_completion(completions):
    main_editor.handle_code_completion(completions)


def main(model):
    ltk.inject_css("pysheets.css")
    login.setup()
    setup(model)
    ltk.subscribe(constants.PUBSUB_SHEET_ID, constants.TOPIC_WORKER_COMPLETION, handle_completion_request)
    ltk.subscribe(constants.PUBSUB_SHEET_ID, constants.TOPIC_WORKER_CODE_COMPLETION, handle_code_completion)
    ltk.subscribe(constants.PUBSUB_SHEET_ID, constants.TOPIC_WORKER_PRINT, print)
    ltk.subscribe(constants.PUBSUB_SHEET_ID, ltk.TOPIC_INFO, print)
    ltk.subscribe(constants.PUBSUB_SHEET_ID, ltk.TOPIC_ERROR, print)


vm_version = sys.version.split()[0].replace(";", "")
minimized = "minimized" if __name__ != "pysheets" else "full"
message = (
    f"[Main] " +
    f"PyScript:{window.version_pyscript} " +
    f"VM:{state.vm_type(sys.version)} " +
    f"Python:{vm_version} " +
    f"Interpreter:{window.version_interpreter} " +
    f"Storage:{window.version_storage} " +
    f"Mode:{state.mode}-{minimized}."
)
state.console.write("pysheets", message)

version_app = "dev"
state.console.write(
    "discord",
    f"[Main] Meet the PySheets community on our Discord server.",
    action=ltk.Button(
        "💬 Join",
        lambda event: ltk.window.open("https://discord.gg/4wy23872th")
    ).addClass("small-button")
)
state.console.write(
    "welcome",
    f"[Main] PySheets {version_app} is in Beta-mode 😱. Use only for experiments.",
)
state.console.write(
    "form",
    f"[Main] We welcome your feedback and bug reports.",
    action=ltk.Button(
        "📣 Tell",
        lambda event: ltk.window.open("https://forms.gle/W7SBXKgz1yvkTEd76")
    ).addClass("small-button")
)

def insert_url(event):
    if main_editor.get() == "":
        sheet.current.set("https://chrislaffra.com/forbes_ai_50_2024.csv")
        sheet.sync()
        set_random_color()
    else:
        lambda: state.console.write(
            "insert-tip",
            f"[AI] To import a sheet, select an empty cell first. Then enter a URL. {constants.ICON_STAR}", 
            action=ltk.Button(f"{constants.ICON_STAR} Try", insert_url).addClass("small-button toolbar-button")
        )

ltk.schedule(
    lambda: sheet and not sheet.get_url_keys() and state.console.write(
        "insert-tip",
        f"[AI] To import a sheet, enter a URL into a cell. {constants.ICON_STAR}", 
        action=ltk.Button(f"{constants.ICON_STAR} Try", insert_url).addClass("small-button toolbar-button")
    ),
    "give a tip",
    3.0
)


def convert(value):
    try:
        return float(value) if "." in value else int(value)
    except:
        return value if value else 0

