import constants
import history
import ltk
import json
import models
import state


class MultiSelection():

    def __init__(self, sheet):
        self.sheet = sheet
        self.started = False
        self.line_top = ltk.Div().addClass("multi-select top")
        self.line_left = ltk.Div().addClass("multi-select left")
        self.line_bottom = ltk.Div().addClass("multi-select bottom")
        self.line_right = ltk.Div().addClass("multi-select right")
        self.cells = []
        self.cell1 = self.cell2 = None

        self.handler_by_shortcut = {
            "a": self.select_all,
            "b": self.bold,
            "c": self.copy,
            "i": self.italicize,
            "v": self.paste,
            "x": self.cut,
            "z": self.undo
        }
        
    def select(self, cell):
        self.cell1 = self.cell2 = cell
        self.stop(cell)

    def draw(self):
        ltk.find(".multi-select").remove()
        if not self.cell1 or not self.cell2 or self.cell1 is self.cell2:
            return
        pos1, pos2 = self.cell1.position(), self.cell2.position()
        if not pos1 or not pos2:
            return
        left = min(pos1.left, pos2.left)
        top = min(pos1.top, pos2.top) - 1
        right = max(pos1.left + self.cell1.outerWidth(), pos2.left + self.cell2.outerWidth()) - 1
        bottom = max(pos1.top + self.cell1.outerHeight(), pos2.top + self.cell2.outerHeight()) - 2
        ltk.find(".sheet-grid").append(
            self.line_top.css("left", left).css("top", top).css("width", right - left),
            self.line_left.css("left", left).css("top", top).css("height", bottom - top),
            self.line_bottom.css("left", left).css("top", bottom).css("width", right - left + 2),
            self.line_right.css("left", right).css("top", top).css("height", bottom - top),
        )

    def set_dimensions(self):
        pos1, pos2 = self.cell1.position(), self.cell2.position()
        assert self.cell1.model.column, f"Column should be >= 1, not {self.cell1.model.column} for {self.cell1}"
        self.dimensions = [
            self.cell1.model.column if pos1.left < pos2.left else self.cell2.model.column,
            self.cell2.model.column if pos1.left < pos2.left else self.cell1.model.column,
            self.cell1.model.row if pos1.top < pos2.top else self.cell2.model.row,
            self.cell2.model.row if pos1.top < pos2.top else self.cell1.model.row,
        ]

    def highlight_col_row(self):
        ltk.window.highlightColRow(*self.dimensions)


    def css(self, name, value):
        keys = ",".join([f"#{cell}" for cell in self.cells])   
        ltk.find(keys).css(name, value)
        self.sheet.selection.css(name, value)
        for model in [self.sheet.get_cell(key).model for key in self.cells]:
            _style = model.style.copy()
            model.style[name] = value
            history.add(models.CellStyleChanged(model.key, _style, model.style))
        self.draw()

    def undo(self, event):
        history.undo(self.sheet.model)
        event.preventDefault()

    def bold(self, event):
        if not self.cells:
            return
        cell = self.sheet.get_cell(self.cells[0])
        self.css("font-weight", {"400": "700", "700": "400"}[cell.css("font-weight")])

    def italicize(self, event):
        if not self.cells:
            return
        cell = self.sheet.get_cell(self.cells[0])
        self.css("font-style", {"normal":"italic", "italic":"normal"}[cell.css("font-style")])

    def copy(self, event):
        from_col, to_col, from_row, to_row = self.dimensions

        def get_cell(col, row):
            return self.sheet.get_cell(models.get_key_from_col_row(col, row))
        
        def get_script(col, row):
            return get_cell(col, row).model.script

        def get_td(col, row):
            cell = get_cell(col, row)
            return ltk.TableData(cell.model.script).attr("style", cell.attr("style"))

        text = "\n".join([
                "\t".join([
                    get_script(col, row)
                    for col in range(from_col, to_col + 1)
                ])
                for row in range(from_row, to_row + 1)
            ])

        html = ltk.Div(ltk.Table( *[
            ltk.TableRow(*[
                get_td(col, row)
                for col in range(from_col, to_col + 1)
            ])
            for row in range(from_row, to_row + 1)
        ])).html()

        ltk.window.clipboardWrite(text, html)

    def paste(self, event):
        current = self.sheet.current

        def paste_done(keys, text):
            start = ltk.get_time()
            def find_cells(keys):
                state.console.write("paste", f"[Paste] Loading {len(keys)} pasted cells")
                for key, new_script, new_style in keys[:constants.MAX_EDITS_PER_SYNC]:
                    model = self.sheet.model.cells.get(key)
                    if not model:
                        model = self.sheet.model.cells[key] = models.Cell(key)
                    old_script = model.script
                    old_style = model.style
                    model.script = model.value = new_script
                    model.style = json.loads(new_style)
                    cell = self.sheet.get_cell(key)
                    if old_script != new_script:
                        history.add(models.CellScriptChanged(key, old_script, new_script))
                    if old_style != new_style:
                        history.add(models.CellStyleChanged(key, cell.model.style, json.loads(new_style)))
                keys = keys[constants.MAX_EDITS_PER_SYNC:]
                if keys:
                    ltk.schedule(lambda: find_cells(keys), "handle more keys")
                else:
                    state.console.write("paste", f"[Paste] Pasting {len(text):,} bytes took {ltk.get_time() - start:.3f}s")
                self.sheet.select(self.sheet.current)

            find_cells(list(keys))
            self.sheet.reselect()

        def process_clipboard(text):
            state.console.write("paste", f"[Paste] Pasting {len(text):,} bytes from the clipboard...")
            def paste_text():
                ltk.window.pasteText(text, current.model.column, current.model.row, ltk.proxy(lambda keys: paste_done(keys, text)))
            def paste_html():
                ltk.window.pasteHTML(text, current.model.column, current.model.row, ltk.proxy(lambda keys: paste_done(keys, text)))
            if event.shiftKey:
                paste_text()
            else:
                paste_html()

        state.console.write("paste", f"[Paste] Pasting from the clipboard...")
        def get_clipboard():
            ltk.window.getClipboard(ltk.proxy(process_clipboard), not event.shiftKey)
        ltk.schedule(get_clipboard, "getting clipboard")

    def cut(self, event):
        self.copy(event)
        self.clear()

    def clear(self):
        for key in self.cells:
            if key in self.sheet.model.cells:
                self.sheet.get_cell(key).clear()
        self.draw()

    def start(self, cell):
        ltk.find("#main").focus()
        self.sheet.select(cell)
        self.cell1 = self.cell2 = cell
        self.update()
        self.started = True

    def extend(self, cell, force=False):
        if not force and not self.started:
            return
        self.cell2 = cell
        self.update()
        self.highlight_col_row()

    def select_all(self, event):
        cells = self.sheet.cells.values()
        if cells:
            min_col = min([cell.column for cell in cells])
            max_col = max([cell.column for cell in cells])
            min_row = min([cell.row for cell in cells])
            max_row = max([cell.row for cell in cells])
            self.cell1 = self.sheet.get_cell(models.get_key_from_col_row(min_col, min_row))
            self.cell2 = self.sheet.get_cell(models.get_key_from_col_row(max_col, max_row))
            self.update()
        event.preventDefault()

    def stop(self, cell):
        self.started = False
        self.update()
        self.highlight_col_row()
    
    def update(self):
        self.set_dimensions()
        self.cells = self.sheet.model.get_cell_keys(*self.dimensions)
        self.draw()


def remove_arrows(delay=1000):
    def dissolve_arrow(arrow):
        arrow.animate({ "opacity": 0 }, delay, ltk.proxy(lambda: arrow.remove()))
    for arrow in ltk.find_list(".leader-line, .inputs-marker"):
        if arrow.css("opacity") == "1":
            dissolve_arrow(arrow)
    ltk.find(".arrow").removeClass("arrow")


def scroll(cell):
    ltk.schedule(lambda: scroll_now(cell), "scroll later")


def scroll_now(cell):
    container = ltk.find("#sheet-container")
    if not container.length:
        return
    grid = ltk.find(".sheet-grid")
    margin_left = ltk.window.parseInt(grid.css("margin-left"))
    margin_top = ltk.window.parseInt(grid.css("margin-top"))
    offset = cell.position()
    style = {}
    if offset.left + margin_left - 61 < 0:
        style["margin-left"] = -offset.left + 61
    elif offset.left + margin_left + 61 > container.width():
        style["margin-left"] = -offset.left + container.width() - cell.width() - 4
    if offset.top + margin_top - 30 < 0:
        style["margin-top"] = -offset.top + 30
    elif offset.top + margin_top + 30 > container.height():
        style["margin-top"] = -offset.top + container.height() - cell.height() - 4
    grid.animate(
        ltk.to_js(style), 
        {
            "duration": constants.ANIMATION_DURATION_FAST,
            "step": ltk.proxy(lambda *args: ltk.schedule(lambda: ltk.window.adjustSheetPosition(), "adjust sheet position")),
        }
    )