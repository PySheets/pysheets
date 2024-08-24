"""
Copyright (c) 2024 laffra - All Rights Reserved. 

Manages the preview views for a sheet in the application.
"""

import constants
import history
import ltk
import models
import selection

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
            .css("width", self.model.width or "fit-content")
            .css("height", self.model.height or "fit-content")
            .on("click", ltk.proxy(lambda event: self.click()))
            .on("mousemove", ltk.proxy(lambda event: self.move()))
            .on("mouseleave", ltk.proxy(lambda event: selection.remove_arrows(0)))
            .on("resizestop", ltk.proxy(lambda event, ui: self.resize(event)))
            .on("dragstop", ltk.proxy(lambda event, ui: self.dragstop(event)))
            .draggable(ltk.to_js({ "containment": ".sheet", "handle": ".preview-header" }))
        )
        self.model.listen(self.model_changed)
        self.set_html(self.model.html)

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

    def click(self):
        """
        Event handler for when the user click inside the preview header.
        """
        self.appendTo(self.parent())  # raise

    def toggle_size(self, event):
        """
        Event handler for when the user toggles the size of the preview widget between a minimized and expanded state.
        """
        minimize = self.height() > constants.PREVIEW_HEADER_HEIGHT
        height = constants.PREVIEW_HEADER_HEIGHT if minimize else "fit-content"
        width = constants.PREVIEW_HEADER_WIDTH if minimize else "fit-content"
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
        self.empty().append(
            ltk.HBox(
                ltk.Text(self.model.key).addClass("preview-key"),
                ltk.Button(toggle_size_label, ltk.proxy(lambda event: self.toggle_size(event))).addClass("toggle") # pylint: disable=unnecessary-lambda
            ).addClass("preview-header"),
            ltk.Div(
                ltk.create(self.model.html)
            ).addClass("preview-content")
        )
        self.make_resizable()
        self.draw_arrows()
        self.fix_images()

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

    def fix_images(self):
        """
        Fixes the `src` attribute of all `img` elements in the preview content
        to include the `crossorigin="anonymous"` attribute.
        """
        script = """
            $("img").each(function () {
                $(this).attr("crossorigin", "anonymous").attr("src", $(this).attr("src"))
            });
        """
        self.find("iframe").contents().find("body").append(
            ltk.create("<script>").html(script)
        )

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
        return
    if not key in previews:
        PreviewView(sheet, sheet.model.get_preview(key, html=html))
        old_html = ""
    else:
        old_html = previews[key].model.html
    previews[key].set_html(html)
    if old_html != html:
        history.add(models.PreviewValueChanged(key, html))

def remove(key):
    """
    Removes a preview view from the previews dictionary.
    
    Args:
        key (str): The key associated with the preview to be removed.
    """
    if key in previews:
        del previews[key]
