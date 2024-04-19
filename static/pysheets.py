import api
import collections
import constants
import js  # type: ignore
import ltk
import logging
import menu
import random
import re
import state
import editor
import sys

from pyscript import window  # type: ignore

state.console.write("pysheets", f"[Main] Pysheets starting {constants.ICON_HOUR_GLASS}")

sheet = None
previews = {}
completion_cache = {}
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
        if ltk.find(".person").length == 0
        else constants.SAVE_DELAY_MULTIPLE_EDITORS
    )
    ltk.schedule(lambda: sheet.save_edits(force), "send edits to server", delay)


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
        self.selection_edited = False
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
        self.counts = collections.defaultdict(int)
        self.current = None

    def load_cell_css(self, cell, settings):
        cell.css("background-color", settings.get(constants.DATA_KEY_VALUE_FILL, constants.DEFAULT_FILL))
        cell.css("font-family", settings.get(constants.DATA_KEY_VALUE_FONT_FAMILY, constants.DEFAULT_FONT_FAMILY))
        cell.css("color", settings.get(constants.DATA_KEY_VALUE_COLOR, constants.DEFAULT_COLOR))
        cell.css("font-size", settings.get(constants.DATA_KEY_VALUE_FONT_SIZE, constants.DEFAULT_FONT_SIZE))

    def load_cell_value(self, cell, settings):
        embed = settings.get(constants.DATA_KEY_VALUE_EMBED, "")
        data = settings[constants.DATA_KEY_VALUE]
        script = data.get(constants.DATA_KEY_VALUE_FORMULA, "")
        preview = data.get(constants.DATA_KEY_VALUE_PREVIEW, "")
        kind = data.get(constants.DATA_KEY_VALUE_KIND, "")
        cell.load(script, kind, preview, embed)

    def load_cell(self, cell, settings):
        if cell is self.current:
            return
        debug(f"Load cell {cell.key}")
        self.load_cell_value(cell, settings)
        self.load_cell_css(cell, settings)

    def load_cells(self, cells):
        for key, settings in cells.items():
            try:
                self.load_cell(self.get(key), settings)
            except Exception as e:
                state.console.write("sheet", f"Error: Cannot load cell {key}: {e}")
        return cells.keys()

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
            key = result["key"]
            cell: Cell = self.get(key)
            if not cell.script:
                return
            cell.update(result["duration"], result["value"], result["preview"])
            cell.running = False
            cell.notify()
            debug("Worker", key, "=>", result["value"])
            if result["error"]:
                state.console.write(key, f"[Error] {key}: {result['error']}")
                cell.update(result["duration"], result["error"])
        except Exception as e:
            state.console.write(key, f"[Error] Cannot handle worker result: {type(e)}: {e}")

    def notify(self, cell):
        for other in self.cells.values():
            if other.key != cell.key and cell.key in other.inputs:
                other.evaluate()

    def setup(self, data, is_doc=True):
        self.load_data(data, is_doc)
        self.setup_selection()

    def load_data(self, data, is_doc=True):
        url_packages = ltk.get_url_parameter(constants.DATA_KEY_PACKAGES)
        if is_doc:
            if not isinstance(data, dict):
                state.console.write("network-status", "[I/O] Error: Timeout. PySheet's document storage is unreachable 😵‍💫😵‍💫😵‍💫️️. Please reload the page...")
                return
            bytes = window.JSON.stringify(ltk.to_js(data), None, 4)

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
        cells = self.load_cells(data.get(constants.DATA_KEY_CELLS, {}))
        current = data.get(constants.DATA_KEY_CURRENT, "A1")
        ltk.schedule(lambda: self.select(self.get(current)), "select-later", 0.1)
        if is_doc:
            sheet.find_frames()
            sheet.find_urls()
        state.console.write("network-status", f'[I/O] Loaded sheet "{state.doc.name}", {len(bytes)} bytes ✅')
        ltk.find("#main").animate(ltk.to_js({"opacity": 1}), 400)
        return cells

    def find_frames(self):
        visited = set()
        def get_width(cell):
            col = cell.column
            while True:
                col += 1
                key = get_key_from_col_row(col, cell.row)
                visited.add(key)
                if not key in self.cells:
                    break
            return col - cell.column

        def get_height(cell):
            row = cell.row
            while True:
                row += 1
                key = get_key_from_col_row(cell.column, row)
                visited.add(key)
                if not key in self.cells:
                    break
            return row - cell.row

        def add_frame(key, width, height):
            for col in range(cell.column, cell.column + width):
                for row in range(cell.row, cell.row + height):
                    other_key = get_key_from_col_row(col, row)
                    visited.add(other_key)
            prompt = f"""
Convert the spreadsheet cells in range "{key}:{other_key}" into a Pandas dataframe.
To load a Dataframe from cells, use "pysheets.sheet(pysheets.load(url))".
Make the last expression refer to the dataframe.
The pysheets module is already imported.
Generate Python code.
"""
            text = f"""
# Create a Pandas DataFrame from values found in the current sheet
pysheets.sheet("{key}:{other_key}")
"""
            add_completion_button(cell.key, lambda: insert_completion(key, prompt, text, { "total": 0 }))

        for key in sorted(self.cells.keys()):
            cell = self.cells[key]
            if cell.key in visited:
                continue
            width = get_width(cell)
            height = get_height(cell)
            if width > 1 and height > 1:
                add_frame(cell.key, width, height)

    def is_a_dependent(self, key):
        for cell in self.cells.values():
            if key in cell.inputs:
                return True
        return False

    def get_url_keys(self):
        return [
            key
            for key, cell in self.cells.items()
            if cell.text().startswith("https:")
        ]

    def find_urls(self):
        for key in self.get_url_keys():
            if self.is_a_dependent(key):
                state.console.remove(f"ai-{key}")
            else:
                prompt = f"""
Load the data URL already stored in variable {key} into a Pandas Dataframe.
To load a Dataframe from a url, use "pysheets.load_sheet(url)".
Make the last expression refer to the dataframe.
Generate Python code.
"""
                request_completion(key, prompt.strip())

    def setup_selection(self):
        def select(event):
            target = ltk.find(event.target)
            if target.hasClass("selection"):
                self.selection.css("caret-color", "black").focus()
                self.selection_edited = True
            elif target.hasClass("cell"):
                debug("sheet.setup.selection", target.attr("id"))
                self.save_selection()
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
            ltk.schedule(self.copy_selection_to_main_editor, "copy-to-editor")
            return
        ltk.find("#main").focus()

    def save_selection(self, event=None):
        debug("sheet.save_selection", self.selection_edited, self.selection.val(), self.current and self.current.text())
        if self.selection_edited and self.current and self.selection.val() != self.current.text():
            self.current.edited(self.selection.val())
        self.find_urls()
    
    def copy_selection_to_main_editor(self):
        debug("copy", self.selection.val())
        main_editor.set(self.selection.val())

    def navigate_main(self, event):
        if not self.current:
            return
        column, row = self.current.column, self.current.row
        if event.key == "Tab":
            column += -1 if event.shiftKey else 1 
        elif event.key == "Delete" or event.key == "Backspace":
            self.current.edited("")
        elif event.key == "ArrowLeft":
            column = max(0, column - 1)
        elif event.key == "ArrowRight":
            column += 1
        elif event.key == "ArrowUp":
            row = max(0, row - 1)
        elif event.key == "ArrowDown" or event.key == "Enter":
            row += 1
        if len(event.key) == 1:
            if event.ctrlKey and event.key == "v":
                self.selection.focus()
            if event.metaKey or event.ctrlKey:
                return
            self.selection_edited = True
            self.selection.css("caret-color", "black").val("").focus()
            ltk.schedule(self.copy_selection_to_main_editor, "copy-to-editor")
        else:
            if self.current and (column != self.current.column or row != self.current.row):
                self.save_selection()
            self.select(self.get(get_key_from_col_row(column, row)))
            event.preventDefault()

    @saveit
    def select(self, cell):
        if not cell or not cell.hasClass("cell"):
            return
        state.console.write("sheet-selection", f"[Sheet] Select {cell}")
        cell.select()
        self.selection_edited = False
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
        self.selection.css("caret-color", "transparent")
        self.current = cell

        # remove highlights
        ltk.find(".column-label").css("background-color", "white")
        ltk.find(".row-label").css("background-color", "white")
        ltk.find(f".cell.highlighted").removeClass("highlighted")
        # highlight the column 
        ltk.find(f".column-label.col-{cell.column + 1}").css("background-color", "#d3e2fc")
        # highlight the row
        ltk.find(f".row-label.row-{cell.row + 1}").css("background-color", "#d3e2fc")

    def worker_ready(self, data):
        for cell in self.cells.values():
            cell.worker_ready()
        self.find_urls()

    def save_file(self, done=None):
        try:
            now = ltk.get_time()
            state.doc.timestamp = now
            cells = dict(
                (key, cell.to_dict())
                for key, cell in self.cells.items()
                if cell.script != "" and ltk.find(f"#{key}").length
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
                constants.DATA_KEY_CURRENT: self.current.key,
            }

            def save_done(data):
                if not isinstance(data, dict):
                    message = f"Full document backup failed {data}"
                else:
                    status = data[constants.DATA_KEY_STATUS]
                    if "error" in status:
                        message = f"Full document backup failed {data}"
                    else:
                        message = f"Full document backed up ✅"
                        state.doc.dirty = False
                state.console.write("save-response", f"[Edits] {message}")
                if done:
                    done()

            url = f"/file?{constants.DATA_KEY_UID}={state.doc.uid}"
            ltk.post(state.add_token(url), data, proxy(save_done))
        except Exception as e:
            logger.error("Error saving file %s", e)
            raise e

    def save_edits(self, force=False):
        if not force and (not state.sync_edits or not any(state.doc.edits.values())):
            return
        for key, cell in list(state.doc.edits[constants.DATA_KEY_CELLS].items()):
            state.doc.edits[constants.DATA_KEY_CELLS][key] = cell if isinstance(cell, dict) else cell.to_dict()
        for key in list(state.doc.edits[constants.DATA_KEY_PREVIEWS]):
            state.doc.edits[constants.DATA_KEY_PREVIEWS][key] = previews[key]
        edits = {}
        for key, edit in list(state.doc.edits.items()):
            if edit:
                edits[key] = edit
        state.doc.edit_count += len(edits)
        debug(f"[Edits] Sent edits: {edits}")
        ltk.post(
            state.add_token(f"/edit"),
            {
                constants.DATA_KEY_UID: state.doc.uid,
                constants.DATA_KEY_EDIT: edits,
                constants.DATA_KEY_CURRENT: self.current.key,
            },
            proxy(lambda response: state.doc.empty_edits()),
        )
        self.save_file()

class Cell(ltk.TableData):

    def __init__(self, sheet: Spreadsheet, column: int, row: int, script: str, preview: str):
        ltk.TableData.__init__(self, "")
        self.sheet= sheet
        self.key = get_key_from_col_row(column, row)
        debug("Cell", self.key, column, row, script)
        self.element = ltk.find(f"#{self.key}")
        if not self.element.attr("id"):
            debug("Error: Cell has no element", self)
        self.column = column
        self.row = row
        self.on("mouseenter", proxy(lambda event: self.enter()))
        self.setup_menu()
        self.running = False
        self.needs_worker = False
        self.inputs = []
        self.script = ""
        self.preview = None
        self.embed = ""
        if script != "" or preview:
            self.set(script, preview)
        
    def enter(self):
        self.draw_cell_arrows()
        self.raise_preview()
    
    def show_history(self, event):
        def load_history(history):
            state.console.write("history", f"[History] Loaded history {history.keys()}")
            all_edits = sorted(
                history[constants.DATA_KEY_EDITS],
                key=lambda edit: -edit.get(constants.DATA_KEY_TIMESTAMP, 0),
            )
            edits = [
                (edit[constants.DATA_KEY_TIMESTAMP], value[constants.DATA_KEY_VALUE][constants.DATA_KEY_VALUE_FORMULA])
                for edit in all_edits
                if constants.DATA_KEY_CELLS in edit
                for key, value in edit[constants.DATA_KEY_CELLS].items()
                if key == self.key
            ]
            def get_copy_button(edit):
                def copy():
                    window.navigator.clipboard.writeText(edit)
                return ltk.Button("copy", lambda event: copy())
            ltk.VBox(*[
                ltk.HBox(
                    ltk.Span(ts).addClass("timestamp"),
                    get_copy_button(edit).addClass("copy"),
                    ltk.Span(edit).addClass("formula")
                )
                for ts, edit in edits
            ]).addClass("history").dialog({ "width": 800, "title": f"Edit history for cell {self.key} (most recent first):" })

        docid = f"{constants.DATA_KEY_UID}={state.doc.uid}"
        before = f"{constants.DATA_KEY_BEFORE}={window.time()}"
        after = f"{constants.DATA_KEY_AFTER}={window.time() - 3600000}"
        url = f"/history?{docid}&{before}&{after}"
        state.console.write("history", f"[History] Loading history {constants.ICON_HOUR_GLASS}")
        ltk.get(state.add_token(url), proxy(load_history))
        ltk.find("#main").css("opacity", 1)

    def setup_menu(self):
        def show_menu(event):
            ltk.MenuPopup(
                ltk.MenuItem("+", f"show history", None, proxy(self.show_history)),
            ).show(self)
            event.preventDefault()

        self.on("contextmenu", proxy(show_menu))

    def set(self, script, preview=None):
        debug("set", self.key, "script:", repr(script))
        self.script = script
        if script == "":
            self.clear()
        self.add_preview(preview)
        self.evaluate()
        if self.sheet.current == self:
            main_editor.set(self.script)
            self.sheet.select(self)
    
    def load(self, script, kind, preview, embed):
        self.embed = embed
        self.set(script, preview)
        self.text(kind)
        debug("load", self.key, kind, script, "=>", repr(self.text()))

    def update(self, duration, value, preview=None):
        debug("update value", self.key, value)
        self.sheet.cache[self.key] = convert(value) if value != "" else 0
        self.add_preview(preview or self.get_preview(value))
        if self.script:
            count = self.sheet.counts[self.key]
            if count:
                speed = '🐌' if duration > 1.0 else '🚀'
                if isinstance(value, str) and not "Error" in value:
                    state.console.write(self.key, f"[Sheet] {self.key}: runs: {count}, {duration:.3f}s {speed}")
        self.notify()
        self.find(".loading-indicator").remove()
        children = self.children()
        self.text(str(value))
        self.append(children)
        if self.sheet.current == self:
            self.sheet.selection.val(self.text())
    
    def get_preview(self, value):
        if type(value) is dict:
            return api.get_dict_table(value)

    def notify(self):
        debug("notify", self.key)
        self.sheet.notify(self)
    
    def worker_ready(self):
        if self.needs_worker:
            debug(f"[Worker] Worker ready, run {self.key}")
            if self.key in self.sheet.cache:
                del self.sheet.cache[self.key]
            self.running = False
            self.evaluate()

    def store_edit(self):
        state.doc.edits[constants.DATA_KEY_CELLS][self.key] = self
        state.doc.last_edit = window.time()

    def get_inputs(self, script):
        if not isinstance(script, str) or not script or script[0] != "=" or "no-inputs" in script:
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
                    elif key != self.key:
                        inputs.append(key)
            index += 1
        debug("get inputs", self.key, inputs)
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
        debug("select", self.key)
        remove_arrows()
        self.sheet.current = self
        main_editor.set(self.script)
        ltk.find("#selection").text(f"Cell: {self.key}")
        ltk.find("#cell-attributes-container").css("display", "block")
        try:
            self.set_css_editors()
        except:
            pass
        return self
    
    def set_css_editors(self):
        ltk.find("#cell-font-family").val(self.css("font-family") or constants.DEFAULT_FONT_FAMILY)
        ltk.find("#cell-font-size").val(round(window.parseFloat(self.css("font-size"))) or constants.DEFAULT_FONT_SIZE)
        ltk.find("#cell-font-color").val(rgb_to_hex(self.css("color")) or constants.DEFAULT_COLOR)
        ltk.find("#cell-fill").val(rgb_to_hex(self.css("background-color")) or constants.DEFAULT_FILL)

    def clear(self):
        self.inputs = []
        self.css("color", "")
        self.css("font-size", "")
        self.css("font-family", "")
        self.css("background-color", "")
        ltk.find(f"#preview-{self.key}").remove()
        ltk.find(f"#completion-{self.key}").remove()
        state.console.remove(f"ai-{self.key}")
        del self.sheet.cells[self.key]
        if self.key in previews:
            del previews[self.key]

    def draw_cell_arrows(self):
        remove_arrows()
        self.draw_arrows()
        self.adjust_arrows()
    
    def raise_preview(self):
        preview = ltk.find(f"#preview-{self.key}")
        preview.appendTo(preview.parent())

    def draw_arrows(self):
        if state.mobile():
            return
        if self.preview:
            window.addArrow(self.element, ltk.find(f"#preview-{self.key} .ltk-text"))
        if not self.inputs:
            return
        try:
            inputs = list(sorted(self.inputs))
            first = self.sheet.get(inputs[0])
            last = self.sheet.get(inputs[-1])
        except Exception as e:
            state.console.write(f"arrows-{self.key}", f"[Error] Error in draw_arrows: {e}")
            return
        window.addArrow(create_marker(first, last, "inputs-marker arrow"), self.element)
        self.addClass("arrow")
        first.draw_arrows()

    def adjust_arrows(self):
        ltk.find(".leader-line").appendTo(ltk.find("#sheet-scrollable"))
        container = ltk.find("#sheet-container")
        scroll_left = container.scrollLeft()
        scroll_top = container.scrollTop()
        for arrow_line in ltk.find_list(".leader-line"):
            arrow_line \
                .css("top", window.parseFloat(arrow_line.css("top")) + scroll_top - 49) \
                .css("left", window.parseFloat(arrow_line.css("left")) + scroll_left)

    def add_preview(self, preview):
        self.preview = preview
        if not preview:
            ltk.find(f"#preview-{self.key}").remove()
            return
        debug(f"add preview ", self.key, preview)

        def get_dimension():
            return (
                window.parseInt(preview.css("left")),
                window.parseInt(preview.css("top")),
                window.parseInt(preview.css("width")),
                window.parseInt(preview.css("height"))
            )
        
        @saveit
        def save_preview():
            previews[self.key] = get_dimension()
            state.doc.edits[constants.DATA_KEY_PREVIEWS][self.key] = preview
            state.doc.last_edit = window.time()
            debug(f"[Sheet] Preview position for {self} saved: {previews[self.key]}")

        def dragstop(*args):
            ltk.schedule(save_preview, "save-preview", 3)

        def resize(event, *args):
            preview = ltk.find(event.target)
            preview.find("img, iframe").css("width", "100%").css("height", f"calc(100% - {constants.PREVIEW_HEADER_HEIGHT})")
            ltk.schedule(save_preview, "save-preview", 3)
        
        def move():
            self.draw_cell_arrows()
            
        def click():
            preview.appendTo(preview.parent())  # raise

        left, top, width, height = previews.get(
            self.key,
            (
                self.offset().left + self.width() + 30,
                self.offset().top + 30,
                "fit-content",
                "fit-content",
            ),
        )

        ltk.find(f".preview-{self.key}").remove()
        if "# no-preview" in self.script:
            return

        preview = (
            ltk.create("<div>")
            .addClass("preview")
            .addClass(f"preview-{self.key}")
            .attr("id", f"preview-{self.key}")
            .css("position", "absolute")
            .css("left", left)
            .css("top", top)
            .css("width", width)
            .css("height", height)
            .on("click", proxy(lambda event: click()))
            .on("mousemove", proxy(lambda event: move()))
            .on("mouseleave", proxy(lambda event: remove_arrows()))
            .on("resize", proxy(resize))
            .on("dragstop", proxy(dragstop))
            .draggable(ltk.to_js({ "containment": ".sheet" }))
        )

        def toggle(event):
            minimize = preview.height() > constants.PREVIEW_HEADER_HEIGHT
            height = constants.PREVIEW_HEADER_HEIGHT if minimize else "fit-content"
            width = constants.PREVIEW_HEADER_WIDTH if minimize else "fit-content"
            preview \
                .attr("minimized", minimize) \
                .height(height) \
                .width(width) \
                .find(".ui-resizable-handle") \
                    .css("display", "none" if minimize else "block")
            ltk.find(event.target).text("+" if minimize else "-")
            ltk.schedule(save_preview, "save-preview", 3)

        @saveit
        def toggle_embed(event):
            self.embed = "" if self.embed else "embed"
            self.add_preview(self.preview)
            state.doc.edits[constants.DATA_KEY_CELLS][self.key] = self.to_dict()
            state.doc.last_edit = window.time()

        try:
            html = self.fix_preview_html(preview, self.preview)
            url = f"/embed?{constants.DATA_KEY_UID}={state.doc.uid}&{constants.DATA_KEY_CELL}={self.key}"
            embed = ltk.Link(url, "embed") if self.embed else ltk.Div("embed")
            ltk.find("#sheet-scrollable").append(
                preview.append(
                    ltk.HBox(
                        ltk.Text(self.key),
                        ltk.Checkbox(self.embed != "").on("change", ltk.proxy(toggle_embed)),
                        ltk.Div(embed.addClass("embed")),
                        ltk.Button("-" if preview.height() > constants.PREVIEW_HEADER_HEIGHT or preview.height() == 0 else "+", ltk.proxy(toggle)).addClass("toggle")
                    ).addClass("preview-header"),
                    ltk.Div(
                        ltk.create(html)
                    ).addClass("preview-content")
                )
            )
        except Exception as e:
            state.console.write("sheet", f"[Error] No preview for {self}: {e}")
            pass
            
        debug("add preview", self.key)
        self.make_resizable()
        self.draw_arrows()
        try:
            for td in ltk.find_list(f"#preview-{self.key} .dataframe td"):
                content = td.text()
                td.empty().append(ltk.Div().text(content))
            ltk.find(f"#preview-{self.key} .dataframe tr th:first-child").remove()
        except Exception as e:
            state.console.write("sheet", "[Error] Cannot add preview for", self, e)
        if state.mobile():
            ltk.find(".dataframe").closest(".preview").remove()


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
        height = preview.height()
        preview.find("img, iframe").css("width", "100%").css("height", f"calc(100% - {constants.PREVIEW_HEADER_HEIGHT})")
        preview.resizable(ltk.to_js({"handles": "se"}))
        try:
            display = "block" if height > constants.PREVIEW_HEADER_HEIGHT else "none"
        except:
            display = "block"
        preview.find(".ui-resizable-handle").css("display", display)

    def is_int(self, value):
        try:
            int(value)
            return True
        except:
            return False

    @saveit
    def edited(self, script):
        debug("edited", self.key, script)
        self.set(script)
        self.store_edit()

    def evaluate(self):
        debug("evaluate", self.key, self.script)
        script = self.script
        is_formula = isinstance(script, str) and script and script[0] == "="
        expression = api.edit_script(self.script[1:]) if is_formula else script
        if is_formula:
            try:
                self.inputs = self.get_inputs(script)
            except Exception as e:
                state.console.write("sheet", f"[Error] Cannot get inputs for {self.key}", e)
                self.inputs = set()
            cache_keys = set(self.sheet.cache.keys())
            if not self.inputs.issubset(cache_keys):
                state.console.write(self.key, f"[Warning] While running {self.key}. No value for inputs {self.inputs - cache_keys}")
                return
        state.console.remove(self.key)
        if is_formula:
            try:
                self.evaluate_locally(expression)
            except Exception as e:
                if state.pyodide:
                    state.console.write(self.key, f"[Error] {self.key}: {e}")
                if "no-worker" in self.script:
                    state.console.write(self.key, f"[Error] {self.key}: {e}")
                    self.update(0, str(e))
                else:
                    self.evaluate_in_worker(expression)
        else:
            self.update(0, self.script, self.preview)
        
    def evaluate_locally(self, expression):
        debug("evaluate locally", self.key, expression)
        inputs = {}
        inputs["pysheets"] = api.PySheets(self.sheet, self.sheet.cache)
        inputs.update(self.sheet.cache)
        start = ltk.get_time()
        exec(expression, inputs)
        duration = ltk.get_time() - start
        self.update(duration, inputs["_"])
    
    def show_loading(self):
        self.find(".loading-indicator").remove()
        self.append(ltk.Span(constants.ICON_HOUR_GLASS).addClass("loading-indicator"))

    def evaluate_in_worker(self, expression):
        if self.running:
            return
        debug("evaluate in worker", self.key, expression)
        self.sheet.counts[self.key] += 1
        self.running = True
        self.needs_worker = True
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
            constants.DATA_KEY_VALUE_EMBED: self.embed,
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
    left = first_offset.left + 1 + ltk.find("#sheet-container").scrollLeft()
    top = first_offset.top - 49 + ltk.find("#sheet-container").scrollTop()
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
        .appendTo(ltk.find("#sheet-scrollable"))
    )

def handle_edits(data):
    if "Error" in data or not constants.DATA_KEY_EDITS in data:
        return
    edits = data[constants.DATA_KEY_EDITS]
    for edit in edits:
        email = edit[constants.DATA_KEY_EMAIL]
        timestamp = edit[constants.DATA_KEY_TIMESTAMP]
        edit[constants.DATA_KEY_UID] = data[constants.DATA_KEY_UID]
        edit[constants.DATA_KEY_CURRENT] = None
        sheet.load_data(edit)
    if edits:
        state.create_user_image(email, timestamp)


def check_edits():
    if state.doc.uid and state.sync_edits:
        debug(f"Check edits since {state.doc.last_edit}")
        url = f"/edits?{constants.DATA_KEY_UID}={state.doc.uid}&{constants.DATA_KEY_TIMESTAMP}={round(state.doc.last_edit)}"
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




def load_history_chunk(edits):
    if edits:
        state.console.write("history", f"[History] Load {len(edits)} edits in history")
        for n, edit in enumerate(edits):
            sheet.load_data(edit, False)
        ltk.schedule(lambda: load_history_chunk(edits[1000:]), "load next chunk")


def check_network():
    if ltk.find(".cell").length == 0:
        state.console.write("network-status", "[I/O] Error: Cannot reach PySheet's document storage ️️🤬🤬🤬. Try reloading the page...")


def load_file(event=None):
    if state.doc.uid:
        url = f"/file?{constants.DATA_KEY_UID}={state.doc.uid}&{constants.DATA_KEY_TIMESTAMP}={state.doc.timestamp}"
        ltk.schedule(check_network, "network-error-3", 3)
        ltk.get(state.add_token(url), proxy(sheet.setup))


def email_to_class(email):
    return email.replace("@", "-").replace(".", "-")



def remove_old_editors():
    now = window.time()
    for editor in ltk.find_list(".person"):
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
    state.doc.last_edit = window.time()


ltk.find("#title").on("change", proxy(set_name))


@saveit
def update_cell(event=None):
    script = main_editor.get()
    cell = sheet.current
    if cell and cell.script != script:
        cell.set(script)
        cell.evaluate()
        state.doc.edits[constants.DATA_KEY_CELLS][cell.key] = cell.to_dict()
        state.doc.last_edit = window.time()
        sheet.selection.css("height", cell.height())
    sheet.find_urls()


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
        return Spreadsheet()

    @saveit
    def resize_editor(*args):
        remove_arrows()
        main_editor.refresh()

    @saveit
    def run_in_main(event):
        show_button()
        ltk.find("#run-in-main").prop("checked", ltk.find(event.target).prop("checked"))

    def show_button(event=None):
        ltk.find("#reload-button").css("display", "block").addClass("small-button")

    def run_current(event=None):
        remove_arrows()
        sheet.current.evaluate()

    sheet = Spreadsheet()
    packages = ltk.get_url_parameter(constants.DATA_KEY_PACKAGES)
    vsp = ltk.VerticalSplitPane(
        ltk.VBox(
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
                    ltk.Switch("PyOdide:", False)
                        .on("change", proxy(run_in_main))
                        .attr("id", "run-in-main"),
                    ltk.Button("Reload", proxy(save_packages))
                        .attr("id", "reload-button")
                        .css("display", "none"),
                    ltk.Button("run", proxy(run_current))
                        .addClass("small-button")
                        .attr("id", "run-button"),
                    ltk.Button(constants.ICON_STAR, proxy(lambda event: insert_completion(sheet.current.key if sheet.current else "", "", "", { "total": 0 })))
                        .addClass("small-button completion-button"),
                ).addClass("packages-container"),
            ),
            main_editor,
        )
        .addClass("editor-container")
        .on("resize", proxy(resize_editor)),
        ltk.VBox(
            ltk.HBox(
                ltk.Input("")
                    .addClass("console-filter")
                    .attr("placeholder", "filter the console"),
                ltk.Button("clear", proxy(lambda event: state.console.clear()))
                    .addClass("console-clear")
                    .attr("title", "Clear the console")
            ),
            ltk.Div(ltk.Table()).addClass("console"),
        ).addClass("console-container"),
        "editor-and-console",
    ).addClass("right-panel")
    if state.mobile():
        ltk.find("#main").prepend(
            ltk.VerticalSplitPane(
                ltk.Div(
                    ltk.Div(
                        ltk.find(".sheet"),
                    ).attr("id", "sheet-scrollable")
                ).attr("id", "sheet-container"),
                vsp.css("height", "30%"),
                "sheet-and-editor",
            ).css("height", "100%")
        )
    else:
        ltk.find("#main").prepend(
            ltk.HorizontalSplitPane(
                ltk.Div(
                    ltk.Div(
                        ltk.find(".sheet"),
                    ).attr("id", "sheet-scrollable")
                ).attr("id", "sheet-container"),
                vsp,
                "sheet-and-editor",
            ).css("height", "calc(100vh - 51px)")
        )
    window.createSheet(26, 50, "sheet-scrollable")
    if not ltk.find("#A1").attr("id"):
        debug("Error: createSheet did not add A1")
        raise ValueError("No A1")
    ltk.find("#menu").empty().append(menu.create_menu().element)
    ltk.find("#main").focus()

    @saveit
    def set_font(index, option):
        cell = sheet.current
        cell.css("font-family", option.text())
        sheet.selection.css("font-family", option.text())
        state.doc.edits[constants.DATA_KEY_CELLS][cell.key] = cell.to_dict()
        state.doc.last_edit = window.time()

    @saveit
    def set_font_size(index, option):
        cell = sheet.current
        cell.css("font-size", f"{option.text()}px")
        sheet.selection.css("font-size", f"{option.text()}px")
        state.doc.edits[constants.DATA_KEY_CELLS][cell.key] = cell.to_dict()
        state.doc.last_edit = window.time()

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
        state.doc.last_edit = window.time()

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
    ltk.find("#main").append(
        ltk.Button("New Sheet", proxy(lambda event: None)).addClass("new-button temporary"),
        ltk.Card(ltk.Div().css("width", 204).css("height", 188)).addClass("document-card temporary"),
        ltk.Card(ltk.Div().css("width", 204).css("height", 188)).addClass("document-card temporary"),
        ltk.Card(ltk.Div().css("width", 204).css("height", 188)).addClass("document-card temporary"),
        ltk.Card(ltk.Div().css("width", 204).css("height", 188)).addClass("document-card temporary"),
        ltk.Card(ltk.Div().css("width", 204).css("height", 188)).addClass("document-card temporary"),
    )
    ltk.find(".temporary").css("opacity", 0).animate(ltk.to_js({ "opacity": 1 }), 2000)
    ltk.get(state.add_token("/list"), proxy(show_document_list))


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
    ltk.find("#main").empty().append(
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
        ).css("overflow", "auto").css("height", "100%")
    )
    ltk.find(".document-card").eq(0).focus()
    ltk.find("#menu").empty()
    state.show_message("Select a sheet below or create a new one...")


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
        state.console.write("ai-complete", "[AI] Received completion from OpenAI...", completion)
        import json
        key = completion["key"]
        text = completion["text"]
        prompt = completion["prompt"]
        if not "CompletionBudgetException" in text:
            text = cleanup_completion(text)
            text = f"# The following code is entirely AI-generated. Please check it for errors.\n\n{text}"
        debug("PySheets: handle completion", key, text)

        if ltk.find("#ai-text").length:
            ltk.find("#ai-text").text(text)
            ltk.find("#ai-insert").removeAttr("disabled")
            return

        if sheet.cells[key].script == "":
            # state.console.write("ai-complete", f"[AI] Completion canceled for {key}")
            return
        completion_cache[key] = (text, completion.get("budget"))
        ltk.find(f"#completion-{key}").remove()
        text, budget = completion_cache[key]
        # state.console.write("ai-complete", f"[AI] OpenAI completion received for {key}; Budget: {budget['total']}/100")
        add_completion_button(key, lambda: insert_completion(key, prompt, text, budget))
    except Exception as e:
        state.console.write("ai-complete", "[Error] Could not handle completion from OpenAI...", e)


def request_completion(key, prompt):
    # state.console.write("ai-complete", f"[AI] Sending a completion request for {key} to OpenAI...")
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
        debug("Generate")
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
    cell: Cell = sheet.get(key)
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
        ltk.schedule(sheet.find_urls, "find-urls", 1)
        
    ltk.find(f"#completion-{key}").remove()
    ltk.find(".packages-container").append(
        ltk.Button(f"{constants.ICON_STAR} {key}", proxy(run))
            .addClass("small-button completion-button")
            .attr("id", f"completion-{key}")
    )
    if key:
        cell_contents = api.shorten(sheet.cells[key].text(), 12)
        message = f'[AI] AI suggestion available for [{key}: "{cell_contents}"]. {constants.ICON_STAR}'
        state.console.write(
            f"ai-{key}",
            message,
            action=ltk.Button(f"{constants.ICON_STAR}{key}", proxy(run)).addClass("small-button completion-button")
        )


def load_doc_with_packages(event, uid, runtime, packages):
    url = f"/?{constants.DATA_KEY_UID}={uid}&{constants.DATA_KEY_RUNTIME}={runtime}"
    if packages:
        url += f"&{constants.DATA_KEY_PACKAGES}={packages}"
    ltk.window.location = url


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
    ltk.subscribe(constants.PUBSUB_SHEET_ID, constants.TOPIC_WORKER_COMPLETION, handle_completion_request)
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
state.console.write("pysheets", message)
logger.info(message)

version_app = "dev"
state.console.write(
    "discord",
    f"[Main] Meet the PySheets community on our Discord server.",
    action=ltk.Button(
        "💬 Join",
        lambda event: ltk.window.open("https://discord.gg/4jjFF6hj")
    ).addClass("small-button")
)
state.console.write(
    "welcome",
    f"[Main] PySheets {version_app} is in early beta-mode 😱. Use only for experiments.",
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
        sheet.find_urls()
        set_random_color()
    else:
        lambda: state.console.write(
            "insert-tip",
            f"[AI] To import a sheet, select an empty cell first. Then enter a URL. {constants.ICON_STAR}", 
            action=ltk.Button(f"{constants.ICON_STAR} Try", insert_url).addClass("small-button completion-button")
        )

ltk.schedule(
    lambda: sheet and not sheet.get_url_keys() and state.console.write(
        "insert-tip",
        f"[AI] To import a sheet, enter a URL into a cell. {constants.ICON_STAR}", 
        action=ltk.Button(f"{constants.ICON_STAR} Try", insert_url).addClass("small-button completion-button")
    ),
    "give a tip",
    3.0
)


def convert(value):
    try:
        return float(value) if "." in value else int(value)
    except:
        return value


