"""
CopyRight (c) 2024 - Chris Laffra - All Rights Reserved.

Represents a multi-selection of cells in a sheet. Provides methods for selecting,
copying, pasting, and modifying the selected cells.
"""

import json

import api
import constants
import history
import ltk
import models
import state


class MultiSelection(): # pylint: disable=too-many-instance-attributes
    """
    Represents a multi-selection of cells in a sheet. Provides methods for selecting,
    copying, pasting, and modifying the selected cells.
    """

    def __init__(self, sheet):
        self.sheet = sheet
        self.started = False
        self.line_top = ltk.Div().addClass("multi-select top")
        self.line_left = ltk.Div().addClass("multi-select left")
        self.line_bottom = ltk.Div().addClass("multi-select bottom")
        self.line_right = ltk.Div().addClass("multi-select right")
        self.dimensions = [0, 0, 0, 0]
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

    def skip(self, event):
        """
        Skips the current event.
        
        This method is a placeholder for event handlers that are not implemented. It does nothing and
        simply returns without performing any actions.
        """

    def handle(self, event):
        """
        Handles keyboard shortcuts for the MultiSelection class. 
        """
        self.handler_by_shortcut.get(event.key, self.skip)(event)

    def select(self, cell):
        """
        Selects a single cell in the sheet and sets it as the start and end of the multi-selection.
        
        Args:
            cell (Cell): The cell to select.
        """
        self.cell1 = self.cell2 = cell
        self.stop(cell)

    def draw(self):
        """
            Draws the multi-selection overlay on the sheet grid. The overlay is composed of four divs
            representing the top, left, bottom, and right borders of the selected area. The positions
            and dimensions of these divs are calculated based on the positions of the start
            and end cells of the multi-selection.
        """
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
        """
        Sets the dimensions of the multi-selection based on the positions of the start and end cells.
        
        The dimensions are calculated as follows:
        - The left column is the minimum of the start and end cell column indices.
        - The right column is the maximum of the start and end cell column indices.
        - The top row is the minimum of the start and end cell row indices.
        - The bottom row is the maximum of the start and end cell row indices.
        
        The dimensions are stored in the `self.dimensions` attribute as a list in the format
        `[from_col, to_col, from_row, to_row]`.
        """
        pos1, pos2 = self.cell1.position(), self.cell2.position()
        assert self.cell1.model.column, f"Column should be >= 1, not {self.cell1.model.column} for {self.cell1}"
        self.dimensions = [
            self.cell1.model.column if pos1.left < pos2.left else self.cell2.model.column,
            self.cell2.model.column if pos1.left < pos2.left else self.cell1.model.column,
            self.cell1.model.row if pos1.top < pos2.top else self.cell2.model.row,
            self.cell2.model.row if pos1.top < pos2.top else self.cell1.model.row,
        ]

    def highlight_col_row(self):
        """
        Highlights the column and row range specified by the `self.dimensions` attribute.
        """
        ltk.window.highlightColRow(*self.dimensions)


    def css(self, name, value):
        """
        Sets the CSS style of the selected cells in the sheet.
        
        Args:
            name (str): The name of the CSS property to set.
            value (str): The value to set for the CSS property.
        """
        keys = ",".join([f"#{cell}" for cell in self.cells])
        ltk.find(keys).css(name, value)
        self.sheet.selection.css(name, value)
        with history.SingleEdit(f"Update '{name}' to '{value}' for {','.join(self.cells)}"):
            for model in [self.sheet.get_cell(key).model for key in self.cells]:
                _style = model.style.copy()
                model.style[name] = value
                history.add(models.CellStyleChanged(model.key, _style, model.style))
        self.draw()

    def undo(self, event):
        """
        Undoes the last action performed on the sheet.
        """
        history.undo(self.sheet.model)
        event.preventDefault()

    def bold(self, event): # pylint: disable=unused-argument
        """
        Toggles the font weight of the first selected cell between normal (400) and bold (700).
        """
        if not self.cells:
            return
        cell = self.sheet.get_cell(self.cells[0])
        self.css("font-weight", {"400": "700", "700": "400"}[cell.css("font-weight")])

    def italicize(self, event): # pylint: disable=unused-argument
        """
        Toggles the font style of the first selected cell between normal and italic.
        """
        if not self.cells:
            return
        cell = self.sheet.get_cell(self.cells[0])
        self.css("font-style", {"normal":"italic", "italic":"normal"}[cell.css("font-style")])

    def copy(self, event): # pylint: disable=unused-argument
        """
        Copies the selected cells in the sheet to the clipboard as both text and HTML.
        """
        from_col, to_col, from_row, to_row = self.dimensions

        def get_cell(col, row):
            return self.sheet.get_cell(api.get_key_from_col_row(col, row))

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
        """
        Pastes the contents of the clipboard into the current cell of the sheet.
        If the clipboard contains text, it is pasted as plain text.
        If the clipboard contains HTML, it is pasted as HTML.
        The pasted content is inserted at the current cell's position, and the sheet
        is reselected after the paste operation is complete.
        """
        current = self.sheet.current

        def paste_done(infos, text):
            start = ltk.get_time()
            def find_cells(infos):
                state.console.write("paste", f"[Paste] Loading {len(infos)} pasted cells")
                for key, new_script, new_style in infos[:constants.MAX_EDITS_PER_SYNC]:
                    cell_view = self.sheet.get_cell(key)
                    cell_view.set(new_script)
                    cell_model = cell_view.model
                    cell_model.style = json.loads(new_style)
                infos = infos[constants.MAX_EDITS_PER_SYNC:]
                if infos:
                    ltk.schedule(lambda: find_cells(infos), "handle more pasted cells")
                else:
                    state.console.write("paste",
                            f"[Paste] Pasting {len(text):,} bytes took {ltk.get_time() - start:.3f}s")
                self.sheet.select(self.sheet.current)

            infos = list(infos)
            with history.SingleEdit(f"Paste {len(infos)} cells"):
                find_cells(infos)
            self.sheet.reselect()

        def process_clipboard(text):
            state.console.write("paste", f"[Paste] Pasting {len(text):,} bytes from the clipboard...")
            def paste_text():
                ltk.window.pasteText(
                    text,
                    current.model.column,
                    current.model.row,
                    ltk.proxy(lambda keys: paste_done(keys, text))
                )
            def paste_html():
                ltk.window.pasteHTML(text,
                    current.model.column,
                    current.model.row,
                    ltk.proxy(lambda keys: paste_done(keys, text))
                )
            if event.shiftKey:
                paste_text()
            else:
                paste_html()

        state.console.write("paste", "[Paste] Pasting from the clipboard...")
        def get_clipboard():
            ltk.window.getClipboard(ltk.proxy(process_clipboard), not event.shiftKey)
        ltk.schedule(get_clipboard, "getting clipboard")

    def cut(self, event):
        """
        Cuts the selected cells from the sheet.
        """
        self.copy(event)
        self.clear()

    def clear(self):
        """
        Clears the selected cells in the sheet.
        """
        with history.SingleEdit(f"Clear {len(self.cells)} cells"):
            for key in self.cells:
                if key in self.sheet.model.cells:
                    self.sheet.get_cell(key).clear()
        self.draw()

    def start(self, cell):
        """
        Starts the selection process by focusing the main element, selecting the provided cell,
        setting the start and end cells to the provided cell, updating the selection, 
        and marking the selection as started.
        """
        ltk.find("#main").focus()
        self.sheet.select(cell)
        self.cell1 = self.cell2 = cell
        self.update()
        self.started = True

    def extend(self, cell, force=False):
        """
        Extends the current selection to the provided cell.
        """
        if not force and not self.started:
            return
        self.cell2 = cell
        self.update()
        self.highlight_col_row()

    def select_all(self, event):
        """
        Selects all cells in the sheet and updates the selection.
        """
        cells = self.sheet.cells.values()
        if cells:
            min_col = min(cell.column for cell in cells)
            max_col = max(cell.column for cell in cells)
            min_row = min(cell.row for cell in cells)
            max_row = max(cell.row for cell in cells)
            self.cell1 = self.sheet.get_cell(api.get_key_from_col_row(min_col, min_row))
            self.cell2 = self.sheet.get_cell(api.get_key_from_col_row(max_col, max_row))
            self.update()
        event.preventDefault()

    def stop(self, cell): # pylint: disable=unused-argument
        """
        Stops the selection process, updates the selection, and highlights the column and row.
        """
        self.started = False
        self.update()
        self.highlight_col_row()

    def update(self):
        """
        Updates the selection by setting the dimensions, getting the cell keys within 
        those dimensions, and drawing the selection.
        """
        self.set_dimensions()
        self.cells = self.sheet.model.get_cell_keys(*self.dimensions)
        self.draw()


def remove_arrows(delay=1000):
    """
    Removes any visible arrows or input markers from the UI after a delay of 1 second.
    """
    def dissolve_arrow(arrow):
        arrow.animate({ "opacity": 0 }, delay, ltk.proxy(lambda: arrow.remove())) # pylint: disable=unnecessary-lambda
    for arrow in ltk.find_list(".leader-line, .inputs-marker"):
        if arrow.css("opacity") == "1":
            dissolve_arrow(arrow)
    ltk.find(".arrow").removeClass("arrow")


def scroll(cell):
    """
        Schedules the `scroll_now` function to be executed after a short delay.
        This allows the scrolling to be performed asynchronously, which 
        improves the responsiveness of the user interface.
    """
    ltk.schedule(lambda: scroll_now(cell), "scroll later")


def scroll_now(cell):
    """
    Scrolls the sheet grid to ensure the given cell is visible within the sheet container.
    
    This function is responsible for calculating the necessary margin adjustments to the sheet grid
    in order to center the given cell within the visible area of the sheet container. It uses
    animation to smoothly transition the grid to the new position.
    
    Args:
        cell (object): The cell object that should be made visible.
    """
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

    def step(*args): # pylint: disable=unused-argument
        ltk.schedule(lambda: ltk.window.adjustSheetPosition(), "adjust sheet position") # pylint: disable=unnecessary-lambda

    grid.animate(
        ltk.to_js(style),
        {
            "duration": constants.ANIMATION_DURATION_FAST,
            "step": ltk.proxy(step)
        }
    )
