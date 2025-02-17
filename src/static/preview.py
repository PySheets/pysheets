"""
Copyright (c) 2024 laffra - All Rights Reserved. 

Manages the preview views for a sheet in the application.
"""

import re

import constants
import history
import ltk
import models
import selection
import state

previews = {}


class PreviewView(ltk.Div):
    """
    Represents a preview view widget for a sheet in the application.
    """
    def __init__(self, sheet: models.Sheet, preview: models.Preview):
        super().__init__()
        self.sheet = sheet
        self.model = preview
        previews[self.model.key] = self
        try:
            offset = ltk.find(f"#{self.model.key}").offset()
            left, top = offset.left, offset.top
        except AttributeError:
            left, top = 100, 100
        dx = 80 if len(previews) % 2 == 0 else 40
        ltk.find(f".preview-{self.model.key}").remove()
        ltk.find(".sheet-grid").append(self
            .addClass("preview")
            .addClass(f"preview-{self.model.key}")
            .attr("id", f"preview-{self.model.key}")
            .css("position", "absolute")
            .css("left", self.model.left or left + self.width() + dx)
            .css("top", self.model.top or top)
            .css("width", self.model.width or "")
            .css("height", self.model.height or "")
            .on("click", ltk.proxy(self.click))
            .on("mousemove", ltk.proxy(lambda event: self.move()))
            .on("mouseleave", ltk.proxy(lambda event: selection.remove_arrows(0)))
            .on("resizestop", ltk.proxy(lambda event, ui: self.resize(event)))
            .on("dragstop", ltk.proxy(lambda event, ui: self.dragstop(event)))
            .draggable(ltk.to_js({ "containment": ".sheet", "handle": ".preview-header" }))
        )
        self.model.listen(self.model_changed)
        self.set_html(self.model.html)
        self.fix_images()

    def add_filters(self):
        """
        Adds filters to the preview table headers if it was generated from a SQL query.
        """
        cell = state.SHEET.get_cell(self.model.key)
        if not "import duckdb" in cell.script:
            return

        names = []

        def add_all_columns():
            cell.script = re.sub("SELECT .* FROM", "SELECT * FROM", cell.script)

        def remove_column(name):
            index = names.index(name)
            names.remove(name)
            clause = ",".join(names)
            state.UI.select(state.UI.get_cell(self.model.key))
            state.UI.editor.set(re.sub("SELECT .* FROM", f"SELECT {clause} FROM", cell.script))
            self.find("thead").find("th").eq(index + 1).remove()
            self.find("tbody").find("tr").each(
                lambda _, element: ltk.find(element).find("td").eq(index).remove()
            )

        def set_condition(name, operator, value):
            clause = f"{name} {operator} {value}"
            cell.script = re.sub("where = '''.*'''", f"where = '''WHERE {clause}'''", cell.script)

        def edit_column_header(index, element):
            try:
                th = ltk.find(element)
                name = th.text()
                if name:
                    names.append(name)

                    def change_filter(index, option):
                        th.find(".preview-filter-value") \
                            .css("display", "none" if index == 0 else "inline-block") \
                            .focus()
                    
                    def set_value(_event):
                        value = th.find(".preview-filter-value").val()
                        operator = th.find(".preview-filter-filter").prop("value")
                        set_condition(name, operator, value)

                    th.addClass("preview-filter").append(
                        ltk.create("<br>"),
                        ltk.Select(["▼", "<", ">", "=", "!=", "..."], "▼", change_filter)
                            .addClass("preview-filter-filter"),
                        ltk.Input("")
                            .on("change", ltk.proxy(set_value))
                            .css("display", "none")
                            .addClass("preview-filter-value"),
                        ltk.Span("X" if name else "All")
                            .addClass("preview-filter-checkbox")
                            .on("click", ltk.proxy(lambda event: remove_column(name))),
                    )
                else:
                    th.append(
                        ltk.Span("All&nbsp;&nbsp;")
                            .addClass("preview-filter-checkbox")
                            .on("click", ltk.proxy(lambda event: add_all_columns())),
                    )
            except Exception as e:
                print("edit_column_header", e)

        self.find("thead th").each(edit_column_header)

    def model_changed(self, preview, info): # pylint: disable=unused-argument
        """
        Updates the CSS properties of the PreviewView widget based on changes to the corresponding 
        properties in the Preview model.
        
        The `model_changed` method is called whenever the `Preview` model associated with this `PreviewView` 
        instance is updated. It takes the name of the updated property (`name`) and the new value 
        (`getattr(self.model, name)`), and applies the new value to the corresponding CSS property of 
        the `PreviewView` widget.
        """
        name = info["name"] # values are left, top, width, and height
        self.css(name, getattr(self.model, name))

    def dragstop(self, *args): # pylint: disable=unused-argument
        """
        Event handler for when the user stops dragging it.
        """
        history.add(
            models.PreviewPositionChanged(
                self.model.key,
                self.model.left,
                self.model.top,
                self.css("left"),
                self.css("top")
            ).apply(self.sheet.model)
        )

    def resize(self, event, *args): # pylint: disable=unused-argument
        """
        Event handler for when the user resizes the preview.
        """
        ltk.find(event.target) \
            .find("img, iframe") \
            .css("width", "100%") \
            .css("height", f"calc(100% - {constants.PREVIEW_HEADER_HEIGHT})")
        history.add(
            models.PreviewDimensionChanged(
                self.model.key,
                self.model.width,
                self.model.height,
                self.css("width"),
                self.css("height")
            ).apply(self.sheet.model)
        )

    def move(self):
        """
        Event handler for when the user moves the preview by dragging the header.
        """
        self.draw_arrows()

    def click(self, event):
        """
        Event handler for when the user click inside the preview header.
        """
        if event.target.tagName in ["TD", "TH", "DIV"]:
            self.appendTo(self.parent())  # raise

    def toggle_size(self, event):
        """
        Event handler for when the user toggles the size of the preview widget between a minimized and expanded state.
        """
        minimize = self.height() > constants.PREVIEW_HEADER_HEIGHT
        width = constants.PREVIEW_HEADER_WIDTH if minimize else ""
        height = constants.PREVIEW_HEADER_HEIGHT if minimize else ""
        self \
            .attr("minimized", minimize) \
            .height(height) \
            .width(width) \
            .find(".ui-resizable-handle") \
                .css("display", "none" if minimize else "block")
        ltk.find(event.target).text("+" if minimize else "-")

    def draw_arrows(self):
        """
        Draws an arrow pointing to the preview key.
        """
        selection.remove_arrows(0)
        self.sheet.get_cell(self.model.key).draw_arrows([])
        ltk.window.addArrow(ltk.find(f"#{self.model.key}"), self.element.find(".preview-header"), self.model.key)

    def set_html(self, html):
        """
        Sets the HTML content of the preview widget and updates the UI accordingly.
        """
        self.model.html = self.fix_html(html)
        toggle_size_label = "-" if self.height() > constants.PREVIEW_HEADER_HEIGHT or self.height() == 0 else "+"
        cell = state.SHEET.get_cell(self.model.key)
        self.empty().append(
            ltk.HBox(
                ltk.Text(f"{self.model.key} - {cell.value}").addClass("preview-key"),
                ltk.Button(toggle_size_label, ltk.proxy(lambda event: self.toggle_size(event))).addClass("toggle") # pylint: disable=unnecessary-lambda
            ).addClass("preview-header"),
            ltk.create(self.model.html).addClass("preview-content")
        )
        self.make_resizable()
        self.draw_arrows()

    def fix_html(self, html):
        """
        Fixes the HTML content of the preview widget to ensure it is properly formatted.
        
        Args:
            html (str): The HTML content to be fixed.
        
        Returns:
            str: The fixed HTML content.
        """
        html = html.replace("script src=", "script crossorigin='anonymous' src=")
        if not html.startswith("<"):
            html = f"<div>{html}</div>"

        return html

    def make_resizable(self):
        """
        Makes the preview widget resizable using jQuery UI `resizable`.
        """
        preview = ltk.find(f"#preview-{self.model.key}")
        preview.find("img, iframe") \
            .css("width", "100%") \
            .css("height", f"calc(100% - {constants.PREVIEW_HEADER_HEIGHT})")
        preview.resizable(ltk.to_js({"handles": "se"}))
        display = "block" if preview.height() > constants.PREVIEW_HEADER_HEIGHT else "none"
        preview.find(".ui-resizable-handle") \
            .css("display", display)

    def fix_images(self):
        """
        Fix images by setting the `crossorigin` attribute of all `img` elements to `anonymous`.
        """
        def fix():
            self.find("iframe").contents() \
                .find("img") \
                .each(lambda index, img: ltk.find(img).attr("crossorigin", "anonymous"))
        ltk.repeat(fix, f"fix images in {self.model.key}", 1)

def load(sheet):
    """
    Loads the preview views for each key in the sheet's model previews dictionary.
    
    Args:
        sheet (Sheet): The sheet object containing the previews.
    """
    for preview in sheet.model.previews.values():
        PreviewView(sheet, preview)


def add(sheet, key, html):
    """
    Adds a new preview view to the previews dictionary, or updates an existing one.
    
    Args:
        sheet (Sheet): The sheet object containing the previews.
        key (str): The key associated with the preview.
        html (str): The HTML content to be displayed in the preview.
    """
    if not html or html == "None":
        ltk.find(f".preview-{key}").remove()
        remove(key)
        return
    if not key in previews:
        PreviewView(sheet, sheet.model.get_preview(key, html=html))
        old_html = ""
    else:
        old_html = previews[key].model.html
    previews[key].set_html(html)
    previews[key].add_filters()
    if old_html != html:
        history.add(models.PreviewValueChanged(key, html))
    return previews[key]


def remove(key):
    """
    Removes a preview view from the previews dictionary.
    
    Args:
        key (str): The key associated with the preview to be removed.
    """
    if key in previews:
        del previews[key]
