import api
import collections
import constants
import js  # type: ignore
import json
import ltk
import logging
import menu
import re
import state
import editor
import sys

from pyscript import window  # type: ignore

state.console.write("pysheets", f"[Main] Pysheets starting {constants.ICON_HOUR_GLASS}")

previews = {}
logger = logging.getLogger("root")
logger.setLevel(
    logging.DEBUG if state.mode == constants.MODE_DEVELOPMENT else logging.INFO
)
local_storage = window.localStorage
proxy = ltk.proxy
debug = lambda *args: None # print("[Debug]", *args)


def save(force=False):
    state.doc.dirty = True
    delay = (
        constants.SAVE_DELAY_SINGLE_EDITOR
        if ltk.find(".other-editor").length == 0
        else constants.SAVE_DELAY_MULTIPLE_EDITORS
    )
    ltk.schedule(lambda: sheet.save_edits(force), "send changes to server", delay)


def saveit(func):
    def inner(*args):
        save()
        return func(*args)

    return inner


def rgb_to_hex(rgb):
    try:
        r, g, b = map(int, rgb[4:-1].split(", "))
        return f"#{r:02x}{g:02x}{b:02x}"
    except:
        return "#404"


def get_col_row_from_key(key):
    row = 0
    col = 0
    for c in key:
        if c.isdigit():
            row = row * 10 + int(c)
        else:
            col = col * 26 + ord(c) - ord("A") + 1
    return col - 1, row - 1


def get_column_name(col):
    parts = []
    col += 1
    while col > 0:
        col, remainder = divmod(col - 1, 26)
        parts.insert(0, chr(remainder + ord("A")))
    return "".join(parts)


def get_key_from_col_row(col, row):
    return f"{get_column_name(col)}{row + 1}"


class Spreadsheet():
    def __init__(self):
        self.clear()
        ltk.subscribe(constants.PUBSUB_SHEET_ID, ltk.TOPIC_WORKER_RESULT, self.handle_worker_result)
        ltk.subscribe(constants.PUBSUB_SHEET_ID, ltk.pubsub.TOPIC_WORKER_READY, self.worker_ready)

        self.selection = ltk.Input("").addClass("selection")
        ltk.find("#main").on("keydown", proxy(lambda event: self.navigate(event)))

        # ltk.find(".column-label").on("contextmenu", proxy(lambda event: self.show_column_menu(event)))
        # ltk.find(".row-label").on("contextmenu", proxy(lambda event: self.show_row_menu(event)))

    def get(self, key):
        if not key:
            return None
        if not key in self.cells:
            column, row = get_col_row_from_key(key)
            self.cells[key] = Cell(self, column, row, "", None)
        return self.cells[key]

    def clear(self):
        self.cells = {}
        self.cache = {}
        self.current: Cell = None
        self.counts = collections.defaultdict(int)

    def load_cells(self, cells):
        state.console.write("sheet", f"[Main] Loading [{','.join(cells.keys())}].")
        for key, settings in cells.items():
            if key in ["0", "1"]: continue
            cell: Cell = self.get(key)
            data = settings[constants.DATA_KEY_VALUE]
            script = data.get(constants.DATA_KEY_VALUE_FORMULA, "")
            if cell.script != script:
                cell.set(script, data.get(constants.DATA_KEY_VALUE_PREVIEW, ""))
                cell.text(data.get(constants.DATA_KEY_VALUE_KIND, ""))
            fill = settings.get(constants.DATA_KEY_VALUE_FILL, constants.DEFAULT_FILL)
            if fill != constants.DEFAULT_FILL:
                cell.css("background-color", fill)
            font_family = settings.get(constants.DATA_KEY_VALUE_FONT_FAMILY, constants.DEFAULT_FONT_FAMILY)
            if font_family != constants.DEFAULT_FONT_FAMILY:
                cell.css("font-family", font_family)
            color = settings.get(constants.DATA_KEY_VALUE_COLOR, constants.DEFAULT_COLOR)
            if color != constants.DEFAULT_COLOR:
                cell.css("color", color)
            font_size = settings.get(constants.DATA_KEY_VALUE_FONT_SIZE, constants.DEFAULT_FONT_SIZE)
            if font_size != constants.DEFAULT_FONT_SIZE:
                cell.css("font-size", font_size)
        return [key for key in cells]

    def copy(self, from_cell, to_cell):
        to_cell.set(from_cell.script)
        to_cell.value.get()
        to_cell.store_edit()
        from_cell.store_edit()
        to_cell.css("font-family", from_cell.css("font-family"))
        to_cell.css("font-size", from_cell.css("font-size"))
        to_cell.css("color", from_cell.css("color"))
        to_cell.css("background-color", from_cell.css("background-color"))

    def show_column_menu(self, event):
        label = ltk.find(event.target)
        selected_column = int(label.attr("col")) - 1

        @saveit
        def insert_column(event):
            for cell in sorted(self.cells.values(), key=lambda cell: -cell.column):
                if cell.column >= selected_column:
                    next_key = get_key_from_col_row(cell.column + 1, cell.row)
                    self.copy(cell, self.get(next_key))
                if cell.column == selected_column:
                    cell.clear()
                if cell.column > 1:
                    previous_key = get_key_from_col_row(cell.column - 1, cell.row)
                    if not previous_key in self.cells:
                        cell.clear()

        @saveit
        def delete_column(event):
            for cell in sorted(self.cells.values(), key=lambda cell: cell.column):
                next_key = get_key_from_col_row(cell.column + 1, cell.row)
                if cell.column >= selected_column:
                    if not next_key in self.cells:
                        cell.clear()
                    self.copy(self.get(next_key), cell)

        ltk.MenuPopup(
            ltk.MenuItem("+", f"insert column", None, proxy(insert_column)),
            ltk.MenuItem("-", f"delete column {get_column_name(selected_column)}", None, proxy(delete_column)),
        ).show(label)
        event.preventDefault()

    def show_row_menu(self, event):
        label = ltk.find(event.target)
        selected_row = int(label.attr("row")) - 1

        @saveit
        def insert_row(event):
            for cell in sorted(self.cells.values(), key=lambda cell: -cell.row):
                if cell.row >= selected_row:
                    next_key = get_key_from_col_row(cell.column, cell.row + 1)
                    self.copy(cell, self.get(next_key))
                if cell.row == selected_row:
                    cell.clear()
                if cell.row > 1:
                    previous_key = get_key_from_col_row(cell.column, cell.row - 1)
                    if not previous_key in self.cells:
                        cell.clear()

        @saveit
        def delete_row(event):
            for cell in sorted(self.cells.values(), key=lambda cell: cell.row):
                next_key = get_key_from_col_row(cell.column, cell.row + 1)
                if cell.row >= selected_row:
                    if not next_key in self.cells:
                        cell.clear()
                    self.copy(self.get(next_key), cell)

        ltk.MenuPopup(
            ltk.MenuItem("+", f"insert row", None, proxy(insert_row)),
            ltk.MenuItem("-", f"delete row {selected_row + 1} ", None, proxy(delete_row)),
        ).show(label)
        event.preventDefault()

    def handle_worker_result(self, result):
        try:
            cell: Cell = self.cells[result["key"]]
            cell.update(result["duration"], result["value"], result["preview"])
            cell.running = False
            cell.notify()
            debug("Worker", result["key"], "=>", result["value"])
            if result["error"]:
                state.console.write(result["key"], f"{result['key']}: {result['error']}")
        except Exception as e:
            state.console.write(result["key"], f"[Worker] Error: {e}")

    def notify(self, cell):
        for other in self.cells.values():
            if other.key != cell.key and cell.key in other.inputs:
                other.invalidate(f"notify from '{cell.key}'")

    def setup(self, data, is_doc=True):
        self.load_data(data, is_doc)
        self.setup_selection()

    def load_data(self, data, is_doc=True):
        url_packages = ltk.get_url_parameter(constants.DATA_KEY_PACKAGES)
        if is_doc:
            if not isinstance(data, dict):
                state.console.write("network-status", "[Network] Error: Timeout. PySheet's document storage is unreachable 😵‍💫😵‍💫😵‍💫️️. Please reload the page...")
                return
            bytes = window.JSON.stringify(ltk.to_js(data), None, 4)
            state.console.write("network-status", f"[Network] Downloaded the sheet, {len(bytes)} bytes ✅")

        data_packages = data.get(constants.DATA_KEY_PACKAGES)
        if data_packages and not url_packages:
            reload_with_packages(data_packages)
        if is_doc:
            if constants.DATA_KEY_UID not in data:
                logger.warning(f"Data is missing uid. Got {data}")
                return []
            if state.doc.uid != data[constants.DATA_KEY_UID]:
                logger.warning(
                    f"Data is for different doc. Got {data[constants.DATA_KEY_UID]}, expected {state.doc.uid}"
                )
                return []
            if data.get(constants.DATA_KEY_STATUS) == "error":
                logger.error("Cannot load data due to error:", data)
                return []
            if constants.DATA_KEY_NAME in data:
                state.doc.name = data[constants.DATA_KEY_NAME]
            if constants.DATA_KEY_TIMESTAMP in data:
                state.doc.last_edit = state.doc.timestamp = data[
                    constants.DATA_KEY_TIMESTAMP
                ]
        if data.get(constants.DATA_KEY_RUNTIME) == "pyodide":
            ltk.find("#run-in-main").prop("checked", True)
        if not ltk.find("#title:focus").length:
            state.set_title(state.doc.name)
            window.document.title = state.doc.name
        load_previews(data.get(constants.DATA_KEY_PREVIEWS, {}))
        for row, settings in data.get(constants.DATA_KEY_ROWS, {}).items():
            ltk.find(f".row-{row}").css("height", settings[constants.DATA_KEY_HEIGHT])
            ltk.find(f".cell.row-{row}").css("max-height", settings[constants.DATA_KEY_HEIGHT])
        for column, settings in data.get(constants.DATA_KEY_COLUMNS, {}).items():
            ltk.find(f".col-{column}").css("width", settings[constants.DATA_KEY_WIDTH])
            ltk.find(f".cell.col-{column}").css("max-width", settings[constants.DATA_KEY_WIDTH])
        if constants.DATA_KEY_EDITOR_WIDTH in data:
            ltk.find(".main-editor-container").width(data[constants.DATA_KEY_EDITOR_WIDTH])
        ltk.schedule(lambda: remove_arrows(1000), "remove arrows", 2.5)
        ltk.find("#main").animate(ltk.to_js({"opacity": 1}), 400)
        cells = self.load_cells(data.get(constants.DATA_KEY_CELLS, {}))
        if constants.DATA_KEY_CURRENT in data and data[constants.DATA_KEY_CURRENT]:
            self.select(self.get(data[constants.DATA_KEY_CURRENT]))
        ltk.find(".main").focus()
        return cells

    def setup_selection(self):
        def select(event):
            target = ltk.find(event.target)
            if target.hasClass("selection"):
                self.selection.css("caret-color", "black").focus()
            else:
                self.copy_selection()
                self.select(self.get(target.attr("id")))
            event.preventDefault()

        def activate(event):
            if ltk.find(".selection:focus").length == 0:
                (self.selection
                    .val("")
                    .val(self.current.text())
                    .css("caret-color", "black")
                    .focus())
            event.preventDefault()

        ltk.find(".cell").on("dblclick", proxy(activate)).on("click", proxy(select))

    def navigate(self, event):
        target = ltk.find(event.target)
        if target.hasClass("selection"):
            self.navigate_selection(event)
        elif target.hasClass("main"):
            self.navigate_main(event)

    def navigate_selection(self, event):
        if event.key == "Escape":
            self.select(self.current)
        elif event.key == "Tab" or event.key == "Enter":
            self.navigate_main(event)
        else:
            return
        ltk.find(".main").focus()

    def copy_selection(self):
        if self.current and self.selection.val() != self.current.text():
            self.current.edited(self.selection.val())

    def navigate_main(self, event):
        column, row = self.current.column, self.current.row
        if event.key == "Tab":
            column += -1 if event.shiftKey else 1 
        elif event.key == "ArrowLeft":
            column = max(0, column - 1)
        elif event.key == "ArrowRight":
            column += 1
        elif event.key == "ArrowUp":
            row = max(0, row - 1)
        elif event.key == "ArrowDown" or event.key == "Enter":
            row += 1
        if len(event.key) == 1:
            if event.metaKey or event.ctrlKey:
                return
            self.selection.css("caret-color", "black").val("").focus()
        else:
            if self.current and (column != self.current.column or row != self.current.row):
                self.copy_selection()
            self.select(self.get(get_key_from_col_row(column, row)))
            event.preventDefault()

    @saveit
    def select(self, cell):
        if not cell:
            return
        selection_had_focus = ltk.find(".selection:focus").length
        cell.select()
        self.selection \
            .css("position", "absolute") \
            .css("color", cell.css("color")) \
            .css("background-color", cell.css("background-color")) \
            .css("font-family", cell.css("font-family")) \
            .css("font-size", cell.css("font-size")) \
            .css("left", 0) \
            .css("top", 0) \
            .appendTo(cell.element) \
            .css("width", cell.width() - 2) \
            .css("height", cell.height()) \
            .attr("class", self.current.attr("class").replace("cell", "selection")) \
            .val(cell.text())
        if self.current is cell and selection_had_focus:
            self.selection.focus()
        else:
            self.selection.css("caret-color", "transparent")
        self.current = cell

        # remove highlights
        ltk.find(".column-label").css("background-color", "white")
        ltk.find(".row-label").css("background-color", "white")
        ltk.find(f".cell.highlighted").removeClass("highlighted")

        # highlight the column 
        ltk.find(f".column-label.col-{cell.column + 1}").css("background-color", "#d3e2fc")
        ltk.find(f".cell.col-{cell.column + 1}").addClass("highlighted")

        # highlight the row
        ltk.find(f".row-label.row-{cell.row + 1}").css("background-color", "#d3e2fc")
        ltk.find(f".cell.row-{cell.row + 1}").addClass("highlighted")

    def worker_ready(self, data):
        for cell in self.cells.values():
            del self.cache[cell.key]
            cell.running = False
            cell.invalidate("worker ready")

    def save_file(self, done=None):
        try:
            now = ltk.get_time()
            state.doc.timestamp = now
            cells = dict(
                (key, cell.to_dict())
                for key, cell in self.cells.items()
                if cell.script != ""
            )
            columns = dict(
                (n, {constants.DATA_KEY_WIDTH: column.width()})
                for n, column in enumerate(ltk.find_list(".column-label"), 1)
                if round(column.width()) != constants.DEFAULT_COLUMN_WIDTH
            )
            rows = dict(
                (n, {constants.DATA_KEY_HEIGHT: row.height() - 4})
                for n, row in enumerate(ltk.find_list(".row-label"), 1)
                if round(row.height()) != constants.DEFAULT_ROW_HEIGHT
            )
            packages = " ".join(ltk.find("#packages").val().replace(",", " ").split())
            data = {
                constants.DATA_KEY_UID: state.doc.uid,
                constants.DATA_KEY_NAME: state.doc.name,
                constants.DATA_KEY_SCREENSHOT: get_plot_screenshot(),
                constants.DATA_KEY_TIMESTAMP: window.time(),
                constants.DATA_KEY_CELLS: cells,
                constants.DATA_KEY_PACKAGES: packages,
                constants.DATA_KEY_COLUMNS: columns,
                constants.DATA_KEY_ROWS: rows,
                constants.DATA_KEY_RUNTIME: "pyodide" if ltk.find("#run-in-main").prop("checked") == True else "micropython",
                constants.DATA_KEY_PREVIEWS: previews,
                constants.DATA_KEY_EDITOR_WIDTH: main_editor.width(),
                constants.DATA_KEY_CURRENT: self.current.key if self.current else "",
            }

            def save_done(response):
                status = response[constants.DATA_KEY_STATUS]
                state.console.write("save-response", f"[Edits] Full document backup: {status} {'😡' if 'error' in status else '✅'}")
                state.doc.dirty = False
                if done:
                    done()

            url = f"https://pysheets.app/file?{constants.DATA_KEY_UID}={state.doc.uid}"
            ltk.post(state.add_token(url), data, proxy(save_done))
        except Exception as e:
            logger.error("Error saving file %s", e)
            raise e

    def save_edits(self, force=False):
        if not force and (not state.sync_edits or not any(state.doc.edits.values())):
            return
        edits = {}
        for key, edit in list(state.doc.edits.items()):
            if edit:
                debug(f"edit-{key}", "save edit", key, edit)
                edits[key] = edit
        state.doc.edit_count += len(edits)
        state.console.write("edits-sent", f"[Edits] Edits sent to server: {state.doc.edit_count}")
        ltk.post(
            state.add_token(f"https://pysheets.app/edit"),
            {
                constants.DATA_KEY_UID: state.doc.uid,
                constants.DATA_KEY_EDIT: edits,
                constants.DATA_KEY_CURRENT: self.current.key if self.current else "",
            },
            proxy(lambda response: state.doc.empty_edits()),
        )
        self.save_file()


class Cell(ltk.TableData):

    def __init__(self, sheet: Spreadsheet, column: int, row: int, script: str, preview: str):
        ltk.TableData.__init__(self, "")
        self.sheet= sheet
        self.key = get_key_from_col_row(column, row)
        self.element = ltk.find(f"#{self.key}")
        if not self.element.attr("id"):
            debug("Error: Cell has no element", self)
        self.column = column
        self.row = row
        self.on("mouseenter", proxy(lambda event: self.draw_cell_arrows()))
        self.running = False
        self.inputs = []
        self.set(script, preview)

    def set(self, script, preview=None):
        self.script = script
        self.add_preview(preview)
        self.invalidate("load from server")
        if self.sheet.current == self:
            main_editor.set(self.script)
            self.sheet.select(self)

    def update(self, duration, value, preview=None):
        self.sheet.cache[self.key] = convert(value) if value != "" else 0
        self.add_preview(preview)
        if self.script:
            count = self.sheet.counts[self.key]
            if count:
                speed = '🐌' if duration > 1.0 else '🚀'
                state.console.write(self.key, f"[Sheet] {self.key}: runs: {count}, {duration:.3f}s {speed}")
        self.notify()
        self.find(".loading-indicator").remove()
        children = self.children()
        self.text(str(value))
        self.append(children)
        if self.sheet.current == self:
            self.sheet.selection.val(self.text())

    def notify(self):
        self.sheet.notify(self)

    def store_edit(self):
        if self.script != "":
            state.doc.edits[constants.DATA_KEY_CELLS][self.key] = self.to_dict()

    def get_inputs(self, script):
        if not isinstance(script, str) or not script or script[0] != "=" or "# no-inputs" in script:
            return set()
        # TODO: sort first and last by min/max col/row
        inputs = []
        index = 0
        is_col = lambda c: c >= "A" and c <= "Z"
        is_row = lambda c: c.isdigit()
        string = self.script[1:]
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
                    if start > 0 and string[start - 1] == ":" and inputs:
                        inputs.extend(self.get_input_range(inputs.pop(), key))
                    else:
                        inputs.append(key)
            index += 1
        return set(inputs)

    def get_input_range(self, start, end):
        start_col, start_row = get_col_row_from_key(start)
        end_col, end_row = get_col_row_from_key(end)
        return [
            get_key_from_col_row(col, row)
            for row in range(start_row, end_row + 1)
            for col in range(start_col, end_col + 1)
        ]

    @saveit
    def select(self):
        remove_arrows()
        self.sheet.current = self
        main_editor.set(self.script)
        ltk.find("#selection").text(f"Selected cell: {self.key}")
        ltk.find("#cell-font-family").val(self.css("font-family"))
        ltk.find("#cell-font-size").val(window.parseFloat(self.css("font-size")))
        ltk.find("#cell-font-color").val(rgb_to_hex(self.css("color")))
        ltk.find("#cell-fill").val(rgb_to_hex(self.css("background-color")))
        ltk.find("#cell-attributes-container").css("display", "block")
        return self

    def clear(self):
        self.set("")
        self.css("font-family", "")
        self.css("font-size", "")
        self.css("color", "")
        self.css("background-color", "")

    def draw_cell_arrows(self):
        remove_arrows()
        self.draw_arrows()

    def draw_arrows(self):
        if self.preview:
            window.addArrow(self.element, ltk.find(f"#preview-{self.key}"))
        if not self.inputs:
            return
        try:
            inputs = list(sorted(self.inputs))
            first = self.sheet.get(inputs[0])
            last = self.sheet.get(inputs[-1])
        except Exception as e:
            state.console.write(f"arrows-{self.key}", f"Error in draw_arrows: {e}")
            return
        window.addArrow(create_marker(first, last, "inputs-marker arrow"), self.element)
        self.addClass("arrow")
        first.draw_arrows()

    def add_preview(self, preview):
        self.preview = preview
        if not preview:
            return

        def save_preview():
            preview = ltk.find(f"#preview-{self.key}")
            state.doc.edits[constants.DATA_KEY_PREVIEWS][self.key] = previews[
                self.key
            ] = (
                preview.css("left"),
                preview.css("top"),
                preview.css("width"),
                preview.css("height"),
            )

        def dragstart(*args):
            pass

        @saveit
        def dragstop(*args):
            save_preview()

        @saveit
        def resize(event, *args):
            preview = ltk.find(event.target)
            preview.find("img, iframe").css("width", preview.width()).css(
                "height", preview.height()
            )
            save_preview()

        left, top, width, height = previews.get(
            self.key,
            (
                self.offset().left + self.width() + 30,
                self.offset().top + 30,
                "fit-content",
                "fit-content",
            ),
        )

        ltk.find(f"#preview-{self.key}").remove()
        preview = (
            ltk.create("<div>")
            .draggable()
            .addClass("preview")
            .attr("id", f"preview-{self.key}")
            .css("position", "absolute")
            .css("left", left)
            .css("top", top)
            .css("width", width)
            .css("height", height)
            .on("mousemove", proxy(lambda event: self.draw_cell_arrows()))
            .on("mouseleave", proxy(lambda event: remove_arrows()))
            .on("resize", proxy(resize))
            .on("dragstart", proxy(dragstart))
            .on("dragstop", proxy(dragstop))
        )

        try:
            html = self.fix_preview_html(preview, self.preview)
            ltk.find(".sheet").append(preview.append(ltk.create(html)))
        except Exception as e:
            pass

        self.make_resizable()
        self.draw_arrows()

    def fix_preview_html(self, preview, html):
        try:
            html = html.replace("script src=", "script crossorigin='anonymous' src=")
        except Exception as e:
            raise e

        def fix_images():
            script = f"""
                $("img").each(function () {{
                    $(this).attr("crossorigin", "anonymous").attr("src", $(this).attr("src"))
                }});
            """
            preview.find("iframe").contents().find("body").append(
                ltk.create("<script>").html(script)
            )

        ltk.schedule(fix_images, f"fix-images-{self.key}", 1.0)
        return html

    def make_resizable(self):
        preview = ltk.find(f"#preview-{self.key}")
        width = preview.css("width")
        height = preview.css("height")
        preview.find("img, iframe").css("width", width).css("height", height)
        preview.resizable(ltk.to_js({"handles": "s, e"}))

    def is_int(self, value):
        try:
            int(value)
            return True
        except:
            return False

    @saveit
    def edited(self, script):
        self.script = script
        self.invalidate("edited")
        self.store_edit()

    def invalidate(self, reason):
        self.evaluate()

    def evaluate(self):
        script = self.script
        is_formula = isinstance(script, str) and script and script[0] == "="
        expression = script[1:] if is_formula else script
        if is_formula:
            self.inputs = self.get_inputs(script)
            if not self.inputs.issubset(set(self.sheet.cache.keys())):
                return
        if is_formula:
            try:
                self.evaluate_locally(expression)
            except Exception as e:
                if state.pyodide:
                    print("Error:", e)
                self.evaluate_in_worker(expression)
        else:
            self.update(0, self.script)
        
    def evaluate_locally(self, expression):
        inputs = {}
        inputs["pysheets"] = api.PySheets(self.sheet, self.sheet.cache)
        inputs.update(self.sheet.cache)
        start = ltk.get_time()
        exec(api.edit_script(self.script[1:]), inputs)
        duration = ltk.get_time() - start
        self.update(duration, inputs["_"])
    
    def show_loading(self):
        self.find(".loading-indicator").remove()
        self.append(ltk.Span(constants.ICON_HOUR_GLASS).addClass("loading-indicator"))

    def evaluate_in_worker(self, expression):
        if self.running:
            return
        self.sheet.counts[self.key] += 1
        self.running = True
        self.show_loading()
        state.console.write(self.key, f"[Sheet] {self.key}: running in worker {constants.ICON_HOUR_GLASS}")
        ltk.publish(
            "Application",
            "Worker",
            ltk.TOPIC_WORKER_RUN,
            [self.key, expression, self.sheet.cache],
        )

    def to_dict(self):
        result = {
            constants.DATA_KEY_VALUE: {
                constants.DATA_KEY_VALUE_FORMULA: self.script,
                constants.DATA_KEY_VALUE_KIND: self.text(),
                constants.DATA_KEY_VALUE_PREVIEW: self.preview,
            }
        }
        style = window.getComputedStyle(self.element.get(0))
        if style.getPropertyValue("font-family") != constants.DEFAULT_FONT_FAMILY:
            result[constants.DATA_KEY_VALUE_FONT_FAMILY] = style.getPropertyValue("font-family")
        if style.getPropertyValue("font-size") != constants.DEFAULT_FONT_SIZE:
            result[constants.DATA_KEY_VALUE_FONT_SIZE] = style.getPropertyValue("font-size")
        if style.getPropertyValue("color") != constants.DEFAULT_COLOR:
            result[constants.DATA_KEY_VALUE_COLOR] = style.getPropertyValue("color")
        if style.getPropertyValue("background-color") != constants.DEFAULT_FILL:
            result[constants.DATA_KEY_VALUE_FILL] = style.getPropertyValue("background-color")
        return result

    def __repr__(self):
        return f"cell[{self.key}]"


def hide_marker(event):
    remove_arrows()


def create_marker(first, last, clazz):
    if not first or not last:
        return
    first_offset = first.offset()
    last_offset = last.offset()
    if not first_offset or not last_offset:
        return
    left = first_offset.left + 1
    top = first_offset.top
    width = last_offset.left - first_offset.left + last.outerWidth() - 5
    height = last_offset.top - first_offset.top + last.outerHeight() - 5
    return (ltk.Div()
        .addClass("marker")
        .addClass(clazz)
        .css("left", left)
        .css("top", top)
        .width(width)
        .height(height)
        .on("mousemove", proxy(hide_marker))
        .appendTo(ltk.jQuery(window.document.body))
    )

def handle_edits(data):
    if "Error" in data or not constants.DATA_KEY_EDITS in data:
        return
    edits = data[constants.DATA_KEY_EDITS]
    for edit in edits:
        edit[constants.DATA_KEY_UID] = data[constants.DATA_KEY_UID]
        edit[constants.DATA_KEY_CURRENT] = data.get(constants.DATA_KEY_CURRENT, "")
        sheet.load_data(edit)
    state.doc.last_edit = window.time()


def check_edits():
    if state.doc.uid and state.sync_edits:
        url = f"https://pysheets.app/edits?{constants.DATA_KEY_UID}={state.doc.uid}&{constants.DATA_KEY_TIMESTAMP}={state.doc.last_edit}"
        ltk.get(state.add_token(url), proxy(lambda response: handle_edits(response)))
        remove_old_editors()


def remove_arrows(duration=0):
    ltk.find(".arrow").removeClass("arrow")
    arrows = ".leader-line, .inputs-marker"
    if duration:
        ltk.find(arrows).animate(
            ltk.to_js(
                {
                    "opacity": 0,
                }
            ),
            duration,
            lambda: ltk.find(arrows).remove(),
        )
    else:
        ltk.find(arrows).remove()



def load_previews(settings):
    previews.update(settings)
    for key, values in previews.items():
        left, top, width, height = values
        ltk.find(f"#preview-{key}").css(
            ltk.to_js(
                {
                    "left": left,
                    "top": top,
                    "width": width,
                    "height": height,
                }
            )
        )



def restore_history(event):
    if state.doc.uid:
        docid = f"{constants.DATA_KEY_UID}={state.doc.uid}"
        before = f"{constants.DATA_KEY_BEFORE}={window.time()}"
        after = f"{constants.DATA_KEY_AFTER}={window.time() - 3600000}"
        url = f"/history?{docid}&{before}&{after}"
        state.console.write("history", f"[Main] Loading history {constants.ICON_HOUR_GLASS}")
        ltk.get(state.add_token(url), proxy(load_history))


def load_history(history):
    state.console.write("history", f"[History] Loaded history {history.keys()}")
    edits = sorted(
        history[constants.DATA_KEY_EDITS],
        key=lambda edit: edit.get(constants.DATA_KEY_TIMESTAMP, 0),
    )
    load_history_chunk(edits)


def load_history_chunk(edits):
    if edits:
        state.console.write("history", f"[History] Load {len(edits)} edits in history")
        for n, edit in enumerate(edits):
            load_data(edit, False)
        ltk.schedule(lambda: load_history_chunk(edits[1000:]), "load next chunk")


def check_network():
    if ltk.find(".cell").length == 0:
        state.console.write("network-status", "[Network] Error: Cannot reach PySheet's document storage ️️🤬🤬🤬. Try reloading the page...")


def load_file(event=None):
    if state.doc.uid:
        url = f"https://pysheets.app/file?{constants.DATA_KEY_UID}={state.doc.uid}&{constants.DATA_KEY_TIMESTAMP}={state.doc.timestamp}"
        ltk.schedule(check_network, "network-error-3", 3)
        ltk.get(state.add_token(url), proxy(sheet.setup))


def email_to_class(email):
    return email.replace("@", "-").replace(".", "-")



def remove_old_editors():
    now = window.time()
    for editor in ltk.find_list(".other-editor"):
        timestamp = int(editor.attr(constants.DATA_KEY_TIMESTAMP))
        if timestamp and now - timestamp > constants.OTHER_EDITOR_TIMEOUT:
            editor.remove()
            remove_marker(editor.attr(constants.DATA_KEY_EMAIL))


def remove_marker(email):
    ltk.find(f".marker-{email_to_class(email)}").remove()




def get_plot_screenshot():
    src = ltk.find(".preview img").attr("src")
    return src if isinstance(src, str) else "/screenshot.png"


def setup_login():
    ltk.find("#login-email").val(local_storage.getItem(constants.DATA_KEY_EMAIL))

    def get_data():
        return (
            {
                constants.DATA_KEY_EMAIL: ltk.find("#login-email").val(),
                constants.DATA_KEY_PASSWORD: ltk.find("#login-password").val(),
                constants.DATA_KEY_CODE: ltk.find("#login-code").val(),
            },
        )

    def handle_login(data):
        if data and not data.get(constants.DATA_KEY_STATUS) == "error":
            state.login(ltk.find("#login-email").val(), data[constants.DATA_KEY_TOKEN])
            ltk.find("#login-container").css("display", "none")
            setup()
        else:
            error("Email and password do not match our records.")
            ltk.find("#login-password-reset").css("display", "block").on("click", proxy(reset_password))


    def confirm_registration(event):
        ltk.find("#login-confirm").css("display", "none")
        ltk.find(event.target).attr('disabled', True)
        data = get_data()
        if invalid_email(data[0][constants.DATA_KEY_EMAIL]):
            error("The email looks invalid. Please enter a valid email.")
        elif invalid_password(data[0][constants.DATA_KEY_PASSWORD]):
            error(f"The password is too short. PySheets has a {constants.MIN_PASSWORD_LENGTH} character minimum.")
        elif invalid_code(data[0][constants.DATA_KEY_CODE]):
            error(f"This is not a valid 6-digit code. Check your email.")
        else:
            ltk.post(state.add_token("/confirm"), data, proxy(handle_login))


    def login(event):
        data = get_data()
        if invalid_email(data[0][constants.DATA_KEY_EMAIL]) or invalid_password(data[0][constants.DATA_KEY_PASSWORD]):
            error("Please enter valid email/password.")
        else:
            ltk.post(state.add_token(f"/login"), get_data(), proxy(handle_login))

    def invalid_email(email):
        return not re.match(r"^\S+@\S+\.\S+$", email)

    def invalid_password(password):
        return len(password) < constants.MIN_PASSWORD_LENGTH

    def invalid_code(code):
        return not re.match(r"^[1-9][1-9][1-9][1-9][1-9][1-9]$", code)

    def error(message):
        if not message:
            ltk.find("#login-message").css("display", "none").text(message)
        else:
            ltk.find("#login-message").css("display", "block").text(message)

    def enable_register(event):
        ltk.find("#login-title").text("Register a PySheets Account")
        ltk.find("#login-register-link").css("display", "none")
        ltk.find("#login-signin-link").css("display", "block")
        ltk.find("#login-login").css("display", "none")
        ltk.find("#login-register").css("display", "block").on("click", proxy(register))

    def enable_signin(event):
        error("")
        ltk.find("#login-title").text("Sign In to PySheets")
        ltk.find("#login-signin-link").css("display", "none")
        ltk.find("#login-register-link").css("display", "block")
        ltk.find("#login-login").css("display", "block")
        ltk.find("#login-register").css("display", "none")

    def register(event):
        def handle_register(data):
            if not data or data.get(constants.DATA_KEY_STATUS) == "error":
                error("Could not register with that email. Try signing in.")
            else:
                ltk.find("#login-code").css("display", "block")
                ltk.find("#login-login").css("display", "none")
                error("Please check your email and enter the confirmation code.")
                ltk.find("#login-confirm").css("display", "block").on("click", proxy(confirm_registration))

        ltk.find("#login-register").css("display", "none")
        data = get_data()
        if invalid_email(data[0][constants.DATA_KEY_EMAIL]):
            error("The email looks invalid. PySheets needs a valid email.")
        elif invalid_password(data[0][constants.DATA_KEY_PASSWORD]):
            error(f"The password is too short. PySheets has a {constants.MIN_PASSWORD_LENGTH} character minimum.")
        else:
            ltk.post(state.add_token("/register"), data, proxy(handle_register))

    def reset_password_with_code(event):
        error("checking details...")
        data = get_data()
        if invalid_email(data[0][constants.DATA_KEY_EMAIL]):
            error("The email looks invalid. Please enter a valid email.")
        elif invalid_password(data[0][constants.DATA_KEY_PASSWORD]):
            error(f"The password is too short. PySheets has a {constants.MIN_PASSWORD_LENGTH} character minimum.")
        elif invalid_code(data[0][constants.DATA_KEY_CODE]):
            error(f"This is not a valid 6-digit code. Check your email.")
        else:
            ltk.post(state.add_token("/reset_code"), data, proxy(handle_login))

    def reset_password(event):
        def handle_reset_password(event):
            error("")
            ltk.find("#login-code").css("display", "block")
            ltk.find("#login-login").css("display", "none")
            ltk.find("#login-password").val("")
            ltk.find("#login-reset").css("display", "block")
            ltk.find("#login-title").text("Change Password")

        data = get_data()
        if invalid_email(data[0][constants.DATA_KEY_EMAIL]):
            error("The email looks invalid. Please enter a valid email.")
        else:
            error("Resetting password...")
            ltk.find("#login-password-reset").css("display", "none")
            ltk.post(state.add_token("/reset"), get_data(), proxy(handle_reset_password))

    ltk.find("#login-register-link").on("click", proxy(enable_register))
    ltk.find("#login-signin-link").on("click", proxy(enable_signin))
    ltk.find("#login-reset").on("click", proxy(reset_password_with_code))
    ltk.find("#login-login").on("click", proxy(login))

    if not local_storage.getItem(constants.DATA_KEY_EMAIL):
        enable_register(None)


@saveit
def set_name(event):
    state.doc.edits[constants.DATA_KEY_NAME] = state.doc.name = ltk.find("#title").val()


ltk.find("#title").on("change", proxy(set_name))


@saveit
def update_cell(event):
    script = main_editor.get()
    if state.mode == constants.MODE_DEVELOPMENT:
        state.console.write("editor-changed", f"[Edits] Editor change: {repr(script)}")
    cell = sheet.current
    if cell and cell.script != script:
        cell.set(script)
        cell.invalidate("editor changed")
        state.doc.edits[constants.DATA_KEY_CELLS][cell.key] = cell.to_dict()


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


def create_sheet():
    if not state.user.token:
        return

    @saveit
    def resize_editor(*args):
        remove_arrows()
        main_editor.refresh()

    @saveit
    def run_in_main(event):
        show_button()
        ltk.find("#run-in-main").prop("checked", ltk.find(event.target).prop("checked"))

    def show_button(event=None):
        ltk.find("#reload-button").prop("disabled", False)

    sheet = Spreadsheet()
    packages = ltk.get_url_parameter(constants.DATA_KEY_PACKAGES)
    vsp = ltk.VerticalSplitPane(
        ltk.VBox(
            ltk.HBox(
                ltk.Text().attr("id", "selection").text("f(x)").css("width", 130),
                ltk.HBox(
                    ltk.Text("Packages to install:"),
                    ltk.Input("")
                        .attr("id", "packages")
                        .css("width", 250)
                        .on("keyup", proxy(show_button))
                        .val(packages),
                    ltk.Switch("Run in main:", False)
                        .on("change", proxy(run_in_main))
                        .attr("id", "run-in-main"),
                    ltk.Button("reload", proxy(save_packages))
                        .attr("id", "reload-button")
                        .prop("disabled", True),
                ).addClass("packages-container"),
            ),
            main_editor,
        )
        .addClass("editor-container")
        .on("resize", proxy(resize_editor)),
        ltk.VBox(
            ltk.Input("")
                .addClass("console-filter")
                .attr("placeholder", "filter the console"),
            ltk.Div().addClass("console"),
        ).addClass("console-container"),
        "editor-and-console",
    ).addClass("right-panel")
    ltk.find(".main").prepend(
        ltk.HorizontalSplitPane(
            ltk.Div(
                ltk.find(".sheet"),
            ).attr("id", "sheet-container"),
            vsp,
            "sheet-and-editor",
        ).element
    )
    window.createSheet(26, 50, "sheet-container")
    if not ltk.find("#A1").attr("id"):
        debug("Error: createSheet did not add A1")
        raise ValueError("No A1")
    ltk.find("#menu").empty().append(menu.create_menu().element)

    @saveit
    def set_font(index, option):
        cell = sheet.current
        cell.css("font-family", option.text())
        sheet.selection.css("font-family", option.text())
        state.doc.edits[constants.DATA_KEY_CELLS][cell.key] = cell.to_dict()

    @saveit
    def set_font_size(index, option):
        cell = sheet.current
        cell.css("font-size", f"{option.text()}px")
        sheet.selection.css("font-size", f"{option.text()}px")
        state.doc.edits[constants.DATA_KEY_CELLS][cell.key] = cell.to_dict()

    @saveit
    def set_color(event):
        cell = sheet.current
        color = ltk.find(event.target).val()
        cell.css("color", color)
        sheet.selection.css("color", color)
        state.doc.edits[constants.DATA_KEY_CELLS][cell.key] = cell.to_dict()

    @saveit
    def set_background(event):
        cell = sheet.current
        color = ltk.find(event.target).val()
        cell.css("background-color", color)
        sheet.selection.css("background-color", color)
        state.doc.edits[constants.DATA_KEY_CELLS][cell.key] = cell.to_dict()

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
    )
    buttons = ltk.find(".buttons-container")
    if state.mode == constants.MODE_DEVELOPMENT:
        def sync(event):
            state.sync_edits = ltk.find(event.target).prop("checked")
        buttons.append(
            ltk.Label("sync:", ltk.Checkbox(True).element)
            .css("margin-right", 20)
            .on("change", proxy(sync)),
            ltk.Button("restore", restore_history).css("margin-right", 20),
        )
    state.console.setup()
    return sheet

def watch():
    def motion(event):
        ltk.find(".header").css("opacity", 1)
        ltk.schedule(check_edits, "check_edits", 1)

    ltk.jQuery(window.document.body).on("mousemove", proxy(motion))
    ltk.jQuery(js.window).on("popstate", proxy(lambda event: menu.go_home()))


def logout(event=None):
    state.logout()
    menu.go_home()


def setup():
    global sheet
    if state.doc.uid:
        state.clear()
        sheet = create_sheet()
        load_file()
    elif state.user.token:
        list_sheets()
    else:
        state.set_title("")
        ltk.find("#login-container").css("display", "block")


def list_sheets():
    state.clear()
    ltk.find("#main").css("opacity", 1)
    ltk.find(".main").append(
        ltk.Button("New Sheet", proxy(lambda event: None)).addClass("new-button temporary"),
        ltk.Card(ltk.Div().css("width", 204).css("height", 188)).addClass("document-card temporary"),
        ltk.Card(ltk.Div().css("width", 204).css("height", 188)).addClass("document-card temporary"),
        ltk.Card(ltk.Div().css("width", 204).css("height", 188)).addClass("document-card temporary"),
        ltk.Card(ltk.Div().css("width", 204).css("height", 188)).addClass("document-card temporary"),
        ltk.Card(ltk.Div().css("width", 204).css("height", 188)).addClass("document-card temporary"),
    )
    ltk.find(".temporary").css("opacity", 0).animate(ltk.to_js({ "opacity": 1 }), 2000)
    ltk.get(state.add_token("https://pysheets.app/list"), proxy(show_document_list))


def show_document_list(documents):
    state.clear()
    if "error" in documents:
        return logger.error(f"Error: Cannot list documents: {documents['error']}")
    local_storage.setItem("cardCount", len(documents[constants.DATA_KEY_IDS]))

    def create_card(uid, index, runtime, packages, *items):
        def select_doc(event):
            if event.keyCode == 13:
                load_doc_with_packages(event, uid, packages)

        return (
            ltk.Card(*items)
                .on("click", proxy(lambda event=None: load_doc_with_packages(event, uid, runtime, packages)))
                .on("keydown", proxy(select_doc))
                .attr("tabindex", 1000 + index)
                .addClass("document-card")
        )

    sorted_documents = sorted(documents[constants.DATA_KEY_IDS], key=lambda doc: doc[1])
    ltk.find(".main").empty().append(
        ltk.Container(
            *[
                create_card(
                    uid,
                    index,
                    runtime,
                    packages,
                    ltk.VBox(
                        ltk.Image(screenshot, "/screenshot.png"),
                        ltk.Text(name),
                    ),
                )
                for index, (uid, name, screenshot, runtime, packages) in enumerate(
                    sorted_documents
                )
            ]
        ).prepend(
            ltk.Button("New Sheet", proxy(lambda event: menu.new_sheet())).addClass(
                "new-button"
            )
        )
    )
    ltk.find(".document-card").eq(0).focus()
    ltk.find("#menu").empty()
    state.show_message("Select a sheet below or create a new one...")


def load_doc_with_packages(event, uid, runtime, packages):
    url = f"/?{constants.DATA_KEY_UID}={uid}&{constants.DATA_KEY_RUNTIME}={runtime}"
    if packages:
        url += f"&{constants.DATA_KEY_PACKAGES}={packages}"
    ltk.window.location = url


def repeat(function, timeout_seconds=1):
    ms = int(timeout_seconds * 1000)
    window.setInterval(proxy(function), ms)


def resize_selection():
    sheet.select(sheet.current)
    save(True)


def sheet_resized():
    ltk.find(".selection").remove()
    ltk.schedule(resize_selection, "resize-selection", 1)


def column_resized(event):
    column = ltk.find(event.target)
    ltk.find(f".cell.col-{column.attr('col')}").css("max-width", column.width())
    sheet_resized()

def row_resized(event):
    row = ltk.find(event.target)
    ltk.find(f".cell.row-{row.attr('row')}").css("max-height", row.height())
    sheet_resized()

window.columnResized = ltk.proxy(column_resized)
window.rowResized = ltk.proxy(row_resized)

worker = state.start_worker()



def main():
    ltk.inject_css("pysheets.css")
    setup_login()
    ltk.schedule(setup, "setup")
    ltk.subscribe(constants.PUBSUB_SHEET_ID, constants.TOPIC_WORKER_PRINT, print)
    ltk.subscribe(constants.PUBSUB_SHEET_ID, ltk.TOPIC_INFO, print)
    ltk.subscribe(constants.PUBSUB_SHEET_ID, ltk.TOPIC_ERROR, print)


ltk.schedule(watch, "watch", 3)
vm_version = sys.version.split()[0].replace(";", "")
minimized = "minimized" if __name__ != "pysheets" else "full"
message = (
    f"[Main] " +
    f"PyScript:{window.version_pyscript} " +
    f"VM:{state.vm_type(sys.version)} " +
    f"Python:{vm_version} " +
    f"Interpreter:{window.version_interpreter} " +
    f"Mode:{state.mode}-{minimized}."
)
logger.info(message)

version_app = "dev"
state.console.write(
    "welcome",
    f"[General] PySheets {version_app} is in alpha-mode 😱. Use only for experiments 🚧.",
)
state.console.write("pysheets", message)


def convert(value):
    try:
        return float(value) if "." in value else int(value)
    except:
        return value

