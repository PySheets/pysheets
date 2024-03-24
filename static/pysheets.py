import dag
import js  # type: ignore
import json
import ltk
import logging
import menu
from pyscript import window  # type: ignore
import re
import state
import editor
import sys
import constants

state.console.write("pysheets", f"[Main] Pysheets starting {constants.ICON_HOUR_GLASS}")

previews = {}

logger = logging.getLogger("root")
logger.setLevel(
    logging.DEBUG if state.mode == constants.MODE_DEVELOPMENT else logging.INFO
)
local_storage = window.localStorage
proxy = ltk.proxy


def save():
    state.doc.dirty = True
    delay = (
        constants.SAVE_DELAY_SINGLE_EDITOR
        if ltk.find(".other-editor").length == 0
        else constants.SAVE_DELAY_MULTIPLE_EDITORS
    )
    ltk.schedule(save_changes, "send changes to server", delay)


def saveit(func):
    def inner(*args):
        save()
        return func(*args)

    return inner


def rgb_to_hex(rgb):
    r, g, b = map(int, rgb[4:-1].split(", "))
    return f"#{r:02x}{g:02x}{b:02x}"


class SpreadsheetCell(ltk.Input):
    cells = {}
    current = None

    def __init__(self, value, column, row):
        ltk.Input.__init__(self, "")
        self.key = dag.get_key_from_col_row(column, row)
        self.column = column
        self.row = row
        self.element = ltk.find(f"#{self.key}")
        SpreadsheetCell.cells[self.key] = self
        (
            self.on("focus", proxy(lambda event: self.select()))
            .on("change", proxy(lambda event: self.changed()))
            .on("keydown", proxy(lambda event: self.keydown(event)))
            .on("mouseenter", proxy(lambda event: self.draw_cell_arrows()))
        )
        self.set(value)

    @classmethod
    @saveit
    def node_changed(cls, key):
        node = dag.Node.nodes[key]
        cell = cls.cells[node.key]
        cell.update_input()
        cell.add_preview()
        ltk.publish(
            constants.PUBSUB_SHEET_ID,
            constants.PUBSUB_DAG_ID,
            constants.TOPIC_CELL_CHANGED,
            cell.key,
        )

    def set(self, value):
        if False and self.val():
            state.console.write(self.key, f"{self.key}: set to {repr(value)}")
        self.value = dag.create(self.key, value)
        ltk.schedule(self.update_input, f"update_input {self.key}")

    def format(self, value):
        try:
            return value if isinstance(value, str) else json.dumps(value)
        except:
            return value.__class__.__name__

    def update_input(self):
        self.element.val(self.format(self.value.get()))

    @saveit
    def select(self):
        SpreadsheetCell.current = self
        main_editor.set(self.value.script)
        ltk.find("#selection").text(f"Selected cell: {self.key}")
        ltk.find("#cell-font-family").val(self.css("font-family"))
        ltk.find("#cell-font-size").val(self.css("font-size").replace("px", ""))
        ltk.find("#cell-font-color").val(rgb_to_hex(self.css("color")))
        ltk.find("#cell-fill").val(rgb_to_hex(self.css("background-color")))
        ltk.find("#cell-attributes-container").css("display", "block")
        return self

    @classmethod
    def clear(cls):
        cls.cells = {}
        cls.current = None

    @classmethod
    def get_cell(cls, key):
        if key in SpreadsheetCell.cells:
            return SpreadsheetCell.cells[key]
        column, row = dag.get_col_row_from_key(key)
        cell = SpreadsheetCell.cells[key] = SpreadsheetCell("", column, row)
        return cell

    @classmethod
    def create_spreadsheet(cls, column_count, row_count):
        window.createSheet(column_count, row_count, "sheet-container")
        ltk.find(".cell").on(
            "focus",
            proxy(
                lambda event: SpreadsheetCell.get_cell(
                    ltk.find(event.target).attr("id")
                )
            ),
        )
        # ltk.find(".column-label").on("contextmenu", proxy(lambda event: cls.show_column_menu(event)))
        # ltk.find(".row-label").on("contextmenu", proxy(lambda event: cls.show_row_menu(event)))

    @classmethod
    def clear(cls, cell):
        cell.set("")
        cell.css("font-family", "")
        cell.css("font-size", "")
        cell.css("color", "")
        cell.css("background-color", "")

    @classmethod
    def copy(cls, from_cell, to_cell):
        to_cell.set(from_cell.value.script)
        to_cell.value.get()
        to_cell.store_edit()
        from_cell.store_edit()
        to_cell.css("font-family", from_cell.css("font-family"))
        to_cell.css("font-size", from_cell.css("font-size"))
        to_cell.css("color", from_cell.css("color"))
        to_cell.css("background-color", from_cell.css("background-color"))

    @classmethod
    def show_column_menu(cls, event):
        label = ltk.find(event.target)
        selected_column = int(label.attr("col")) - 1

        @saveit
        def insert_column(event):
            for cell in sorted(SpreadsheetCell.cells.values(), key=lambda cell: -cell.column):
                if cell.column >= selected_column:
                    next_key = dag.get_key_from_col_row(cell.column + 1, cell.row)
                    cls.copy(cell, SpreadsheetCell.get_cell(next_key))
                if cell.column == selected_column:
                    cls.clear(cell)
                if cell.column > 1:
                    previous_key = dag.get_key_from_col_row(cell.column - 1, cell.row)
                    if not previous_key in SpreadsheetCell.cells:
                        cls.clear(cell)

        @saveit
        def delete_column(event):
            for cell in sorted(SpreadsheetCell.cells.values(), key=lambda cell: cell.column):
                next_key = dag.get_key_from_col_row(cell.column + 1, cell.row)
                if cell.column >= selected_column:
                    if not next_key in SpreadsheetCell.cells:
                        cls.clear(cell)
                    cls.copy(SpreadsheetCell.get_cell(next_key), cell)

        ltk.MenuPopup(
            ltk.MenuItem("+", f"insert column", None, proxy(insert_column)),
            ltk.MenuItem("-", f"delete column {dag.get_column_name(selected_column)}", None, proxy(delete_column)),
        ).show(label)
        event.preventDefault()

    @classmethod
    def show_row_menu(cls, event):
        label = ltk.find(event.target)
        selected_row = int(label.attr("row")) - 1

        @saveit
        def insert_row(event):
            for cell in sorted(SpreadsheetCell.cells.values(), key=lambda cell: -cell.row):
                if cell.row >= selected_row:
                    next_key = dag.get_key_from_col_row(cell.column, cell.row + 1)
                    cls.copy(cell, SpreadsheetCell.get_cell(next_key))
                if cell.row == selected_row:
                    cls.clear(cell)
                if cell.row > 1:
                    previous_key = dag.get_key_from_col_row(cell.column, cell.row - 1)
                    if not previous_key in SpreadsheetCell.cells:
                        cls.clear(cell)

        @saveit
        def delete_row(event):
            for cell in sorted(SpreadsheetCell.cells.values(), key=lambda cell: cell.row):
                next_key = dag.get_key_from_col_row(cell.column, cell.row + 1)
                if cell.row >= selected_row:
                    if not next_key in SpreadsheetCell.cells:
                        cls.clear(cell)
                    cls.copy(SpreadsheetCell.get_cell(next_key), cell)

        ltk.MenuPopup(
            ltk.MenuItem("+", f"insert row", None, proxy(insert_row)),
            ltk.MenuItem("-", f"delete row {selected_row + 1} ", None, proxy(delete_row)),
        ).show(label)
        event.preventDefault()

    def draw_cell_arrows(self):
        remove_arrows()
        self.draw_arrows()

    def draw_arrows(self):
        if self.value.preview:
            window.addArrow(self.element, ltk.find(f"#preview-{self.key}"))
        if not self.value.inputs:
            return
        try:
            first = self.cells[self.value.inputs[0]]
            last = self.cells[self.value.inputs[-1]]
        except:
            return
        window.addArrow(
            self.create_marker(first, last, "inputs-marker arrow", "#ff7f0e"),
            self.element,
        )
        self.addClass("arrow")
        first.draw_arrows()

    def create_marker(self, first, last, clazz, color):
        left = first.offset().left
        top = first.offset().top
        width = last.offset().left - first.offset().left + last.parent().width()
        height = last.offset().top - first.offset().top + last.parent().height()

        def add_marker(x, y, w, h, z_index=100):
            return (
                ltk.Div()
                .css("position", "absolute")
                .css("left", x)
                .css("top", y)
                .width(w)
                .height(h)
                .addClass(clazz)
                .css("background-color", color)
                .css("z-index", z_index)
                .appendTo(ltk.jQuery(window.document.body))
            )

        add_marker(left, top, 1, height),  # left
        add_marker(left + width, top, 1, height),  # right
        add_marker(left, top, width, 1),  # top
        add_marker(left, top + height, width, 1),  # bottom
        return add_marker(left, top, width, height, 0)

    def add_preview(self):
        if not self.value.preview:
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
            html = self.fix_preview_html(preview, self.value.preview)
            ltk.find(".sheet").append(preview.append(ltk.create(html)))
        except Exception as e:
            print(e)
            pass
        ltk.schedule(self.make_resizable, f"resizable {self.key}")

        self.draw_arrows()

    def fix_preview_html(self, preview, html):
        try:
            html = html.replace(
                "script src=",
                "script crossorigin='anonymous' src=",
            )
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

    def keydown(self, event):
        if self.is_int(self.element.val()):
            value = int(self.element.val())
            increment = 10 if event.shiftKey else 1
            if event.keyCode == 38:
                self.element.val(str(value + increment))
                self.edited()
                event.preventDefault()
            elif event.keyCode == 40:
                self.element.val(str(value - increment))
                self.edited()
                event.preventDefault()

    def changed(self):
        self.edited()
        self.select()

    @saveit
    def edited(self):
        if isinstance(self.value, dag.Formula):
            return
        value = self.val()
        self.set(value)
        self.store_edit()
        self.notify()
        
    def store_edit(self):
        if self.value.script != "":
            state.doc.edits[constants.DATA_KEY_CELLS][self.key] = self.to_dict()

    def notify(self):
        ltk.publish(
            constants.PUBSUB_SHEET_ID,
            constants.PUBSUB_DAG_ID,
            constants.TOPIC_CELL_CHANGED,
            self.key,
        )

    def to_dict(self):
        result = {
            constants.DATA_KEY_VALUE: self.value.to_dict(),
        }
        if self.css("font-family") != constants.DEFAULT_FONT_FAMILY:
            result[constants.DATA_KEY_VALUE_FONT_FAMILY] = self.css("font-family")
        if self.css("font-size") != constants.DEFAULT_FONT_SIZE:
            result[constants.DATA_KEY_VALUE_FONT_SIZE] = self.css("font-size")
        if self.css("color") != constants.DEFAULT_COLOR:
            result[constants.DATA_KEY_VALUE_COLOR] = self.css("color")
        if self.css("background-color") != constants.DEFAULT_FILL:
            result[constants.DATA_KEY_VALUE_FILL] = self.css("background-color")
        return result

    def __repr__(self):
        return f"cell[{self.key}]"


def handle_edits(data):
    if "Error" in data or not constants.DATA_KEY_EDITS in data:
        return
    edits = data[constants.DATA_KEY_EDITS]
    for edit in edits:
        edit[constants.DATA_KEY_UID] = data[constants.DATA_KEY_UID]
        edit[constants.DATA_KEY_CURRENT] = data.get(constants.DATA_KEY_CURRENT, "")
        changed_cells = load_data(edit)
        for key in changed_cells:
            if False and state.mode == constants.MODE_DEVELOPMENT:
                state.console.write(f"edit-received-{key}", f"{key} received {str(SpreadsheetCell.cells[key])}")
            SpreadsheetCell.cells[key].notify()
        update_editor(edit, changed_cells)
    state.doc.last_edit = window.time()


def check_edits():
    if state.doc.uid and state.sync_edits:
        url = f"/edits?{constants.DATA_KEY_UID}={state.doc.uid}&{constants.DATA_KEY_TIMESTAMP}={state.doc.last_edit}"
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


def load_cells(cells):
    state.console.write("sheet", f"[Main] Loading [{','.join(cells.keys())}].")
    for key, settings in cells.items():
        cell = SpreadsheetCell.get_cell(key)
        value = settings[constants.DATA_KEY_VALUE]
        if value:
            cell.set(value)
        cell.css(
            ltk.to_js(
                {
                    "font-family": settings.get(
                        constants.DATA_KEY_VALUE_FONT_FAMILY,
                        constants.DEFAULT_FONT_FAMILY,
                    ),
                    "font-size": settings.get(
                        constants.DATA_KEY_VALUE_FONT_SIZE, constants.DEFAULT_FONT_SIZE
                    ),
                    "color": settings.get(
                        constants.DATA_KEY_VALUE_COLOR, constants.DEFAULT_COLOR
                    ),
                    "background-color": settings.get(
                        constants.DATA_KEY_VALUE_FILL, constants.DEFAULT_FILL
                    ),
                }
            )
        )
        if cell.value.preview:
            ltk.schedule(cell.add_preview, f"add preview {key}")
        if cell is SpreadsheetCell.current:
            main_editor.set(cell.value.script)
    return [key for key in cells]


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


def load_data(data, is_doc=True):
    url_packages = ltk.get_url_parameter(constants.DATA_KEY_PACKAGES)
    data_packages = data.get(constants.DATA_KEY_PACKAGES)
    if data_packages and not url_packages:
        reload_with_packages(data_packages)

    # print("load", window.JSON.stringify(ltk.to_js(data), None, 4))
    SpreadsheetCell.create_spreadsheet(26, 50)
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
    print("LOAD RUNTIME", data.get(constants.DATA_KEY_RUNTIME))
    if data.get(constants.DATA_KEY_RUNTIME) == "pyodide":
        ltk.find("#run-in-main").prop("checked", True)
    if not ltk.find("#title:focus").length:
        state.set_title(state.doc.name)
        window.document.title = state.doc.name
    load_previews(data.get(constants.DATA_KEY_PREVIEWS, {}))
    for row, settings in data.get(constants.DATA_KEY_ROWS, {}).items():
        ltk.find(f".row-{row}").css("height", settings[constants.DATA_KEY_HEIGHT])
    for column, settings in data.get(constants.DATA_KEY_COLUMNS, {}).items():
        ltk.find(f".col-{column}").css("width", settings[constants.DATA_KEY_WIDTH])
    if constants.DATA_KEY_EDITOR_WIDTH in data:
        ltk.find(".main-editor-container").width(data[constants.DATA_KEY_EDITOR_WIDTH])
    ltk.schedule(lambda: remove_arrows(1000), "remove arrows", 2.5)
    if constants.DATA_KEY_CURRENT in data and data[constants.DATA_KEY_CURRENT]:
        SpreadsheetCell.get_cell(data[constants.DATA_KEY_CURRENT]).select().focus()
    if is_doc:
        ltk.find(".cell").on(
            "focus",
            proxy(lambda event: SpreadsheetCell.get_cell(event.target.id).select()),
        )
    return load_cells(data.get(constants.DATA_KEY_CELLS, {}))


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
        with dag.layer:
            for n, edit in enumerate(edits):
                load_data(edit, False)
        ltk.schedule(lambda: load_history_chunk(edits[1000:]), "load next chunk")


def load_file(event=None):
    if state.doc.uid:
        url = f"/file?{constants.DATA_KEY_UID}={state.doc.uid}&{constants.DATA_KEY_TIMESTAMP}={state.doc.timestamp}"
        ltk.get(state.add_token(url), proxy(load_data))


def email_to_class(email):
    return email.replace("@", "-").replace(".", "-")


def update_editor(edit, changed_cells):
    email = edit[constants.DATA_KEY_EMAIL]
    if email == state.user.email:
        return
    state.create_user_image(email, edit[constants.DATA_KEY_TIMESTAMP])
    current = edit[constants.DATA_KEY_CURRENT] or changed_cells and changed_cells.pop()
    if current:
        cell = SpreadsheetCell.cells[current]
        color = constants.IMAGE_COLORS[
            ord(email[0].upper()) % len(constants.IMAGE_COLORS)
        ]
        cell.create_marker(
            cell, cell, f"current-marker marker-{email_to_class(email)}", color
        )


def remove_old_editors():
    now = window.time()
    for editor in ltk.find_list(".other-editor"):
        timestamp = int(editor.attr(constants.DATA_KEY_TIMESTAMP))
        if timestamp and now - timestamp > constants.OTHER_EDITOR_TIMEOUT:
            editor.remove()
            remove_marker(editor.attr(constants.DATA_KEY_EMAIL))


def remove_marker(email):
    ltk.find(f".marker-{email_to_class(email)}").remove()


def save_edits():
    if not state.sync_edits or not any(state.doc.edits.values()):
        return
    edits = {}
    for key, edit in list(state.doc.edits.items()):
        if edit:
            edits[key] = edit
            if state.mode == constants.MODE_DEVELOPMENT:
                state.console.write(f"edit-sent-{key}", f"{key} sent {edit}")
    state.doc.edit_count += len(edits)
    state.console.write("edits-sent", f"[Edits] Sent to server: {state.doc.edit_count}.")
    print("save edits", state.sync_edits, len(state.doc.edits))
    ltk.post(
        state.add_token(f"/edit"),
        {
            constants.DATA_KEY_UID: state.doc.uid,
            constants.DATA_KEY_EDIT: edits,
            constants.DATA_KEY_CURRENT: SpreadsheetCell.current.key
            if SpreadsheetCell.current
            else "",
        },
        proxy(lambda response: state.doc.empty_edits()),
    )


def save_file(done=None):
    try:
        now = ltk.get_time()
        state.doc.timestamp = now
        cells = dict(
            (key, cell.to_dict())
            for key, cell in SpreadsheetCell.cells.items()
            # if cell.value.value
        )
        columns = dict(
            (n, {constants.DATA_KEY_WIDTH: column.width()})
            for n, column in enumerate(ltk.find_list(".column-label"), 1)
            if round(column.width()) != constants.DEFAULT_COLUMN_WIDTH
        )
        rows = dict(
            (n, {constants.DATA_KEY_HEIGHT: row.height()})
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
            constants.DATA_KEY_RUNTIME: "pyodide" if ltk.find("#run-in-main").prop("checked") else "micropython",
            constants.DATA_KEY_PREVIEWS: previews,
            constants.DATA_KEY_EDITOR_WIDTH: main_editor.width(),
            constants.DATA_KEY_CURRENT: SpreadsheetCell.current.key if SpreadsheetCell.current else "",
        }

        def save_done(response):
            state.console.write("save-response", f"[Edits] Save: {response[constants.DATA_KEY_STATUS]}")
            state.doc.dirty = False
            if done:
                done()

        url = f"/file?{constants.DATA_KEY_UID}={state.doc.uid}"
        ltk.post(state.add_token(url), data, proxy(save_done))
    except Exception as e:
        logger.error("Error saving file %s", e)


def save_changes():
    save_edits()
    save_file()


def get_plot_screenshot():
    src = ltk.find(".preview img").attr("src")
    return src if isinstance(src, str) else "/screenshot.png"


def setup_login():
    ltk.find("#login-email").val(local_storage.getItem(constants.DATA_KEY_EMAIL) or "")

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
    value = main_editor.get()
    if state.mode == constants.MODE_DEVELOPMENT:
        state.console.write("editor-changed", f"[Edits] Editor change: {repr(value)}")
    cell = SpreadsheetCell.current
    if cell and cell.val() != value:
        cell.set(value)
        cell.val(value)
        cell.edited()
        cell.value.get()
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
    save_file(lambda: reload_with_packages(packages))


def create_topbar():
    if not state.user.token:
        return

    @saveit
    def resize_editor(*args):
        remove_arrows()
        main_editor.refresh()

    @saveit
    def run_in_main(event):
        print("RUNTIME:", ltk.find(event.target).prop("checked"), "pyodide" if ltk.find(event.target).prop("checked") else "micropython")
        show_button()
        ltk.find("#run-in-main").prop("checked", ltk.find(event.target).prop("checked"))

    def show_button(event=None):
        ltk.find("#reload-button").prop("disabled", False)

    packages = ltk.get_url_parameter(constants.DATA_KEY_PACKAGES)
    SpreadsheetCell.create_spreadsheet(26, 50)
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
        ltk.Div().addClass("console"),
        "editor-and-console",
    )
    ltk.schedule(getattr(vsp, "resize"), "resize vsp", 0.5)
    ltk.find(".main").prepend(
        ltk.HorizontalSplitPane(
            ltk.Div(
                ltk.find(".sheet"),
            ).attr("id", "sheet-container"),
            vsp,
            "sheet-and-editor",
        ).element
    )
    ltk.find("#menu").empty().append(menu.create_menu().element)

    @saveit
    def set_font(index, option):
        cell = SpreadsheetCell.current
        cell.css("font-family", option.text())
        state.doc.edits[constants.DATA_KEY_CELLS][cell.key] = cell.to_dict()

    @saveit
    def set_font_size(index, option):
        cell = SpreadsheetCell.current
        cell.css("font-size", f"{option.text()}px")
        state.doc.edits[constants.DATA_KEY_CELLS][cell.key] = cell.to_dict()

    @saveit
    def set_color(event):
        cell = SpreadsheetCell.current
        cell.css("color", ltk.find(event.target).val())
        state.doc.edits[constants.DATA_KEY_CELLS][cell.key] = cell.to_dict()

    @saveit
    def set_background(event):
        cell = SpreadsheetCell.current
        cell.css("background-color", ltk.find(event.target).val())
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
    if state.doc.uid:
        print(f"Setup: Loading document {state.doc.uid}")
        state.clear()
        create_topbar()
        load_file()
    elif state.user.token:
        print(f"Setup: Loading document list")
        list_sheets()
    else:
        print(f"Setup: Show login UI")
        state.set_title("")
        ltk.find("#login-container").css("display", "block")
    ltk.find(".main").css("opacity", 1)


def list_sheets():
    state.clear()
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
    ltk.find(".main").append(
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


def load_doc_with_packages(event, uid, runtime, packages):
    url = f"/?{constants.DATA_KEY_UID}={uid}&{constants.DATA_KEY_RUNTIME}={runtime}"
    if packages:
        url += f"&{constants.DATA_KEY_PACKAGES}={packages}"
    ltk.window.location = url


def repeat(function, timeout_seconds=1):
    ms = int(timeout_seconds * 1000)
    window.setInterval(proxy(function), ms)


window.sheetResized = lambda column: save()


def main():
    ltk.inject_css("pysheets.css")
    setup_login()
    ltk.schedule(setup, "setup")

    ltk.subscribe(constants.PUBSUB_SHEET_ID, ltk.TOPIC_INFO, print)
    ltk.subscribe(constants.PUBSUB_SHEET_ID, ltk.TOPIC_ERROR, print)
    ltk.subscribe(
        "Application", constants.TOPIC_NODE_CHANGED, SpreadsheetCell.node_changed
    )


ltk.schedule(watch, "watch", 3)
vm_version = sys.version.split()[0].replace(";", "")
minimized = "minimized" if __name__ != "pysheets" else "full"
message = f"[Main] Python={vm_version}. VM={state.vm_type(sys.version)}. Mode={state.mode}-{minimized}."
logger.info(message)

app_version = "dev" 
state.console.write(
    "welcome",
    f"[General] PySheets {app_version} is in alpha-mode. Use only for experiments.",
)
state.console.write("pysheets", message)