import constants
import history
import ltk
import models
import selection
import state

previews = {}

class PreviewView(ltk.Div):
    def __init__(self, sheet: models.Sheet, preview: models.Preview):
        super().__init__()
        self.sheet = sheet
        self.model = preview
        previews[self.model.key] = self 
        offset = ltk.find(f"#{self.model.key}").offset()
        dx = 80 if len(previews) % 2 == 0 else 40
        ltk.find(f".preview-{self.model.key}").remove()
        ltk.find(".sheet-grid").append(self
            .addClass("preview")
            .addClass(f"preview-{self.model.key}")
            .attr("id", f"preview-{self.model.key}")
            .css("position", "absolute")
            .css("left", self.model.left or offset.left + self.width() + dx)
            .css("top", self.model.top or offset.top)
            .css("width", self.model.width or "fit-content")
            .css("height", self.model.height or "fit-content")
            .on("click", ltk.proxy(lambda event: self.click()))
            .on("mousemove", ltk.proxy(lambda event: self.move()))
            .on("mouseleave", ltk.proxy(lambda event: selection.remove_arrows()))
            .on("resizestop", ltk.proxy(lambda event, ui: self.resize(event)))
            .on("dragstop", ltk.proxy(lambda event, ui: self.dragstop(event)))
            .draggable(ltk.to_js({ "containment": ".sheet" }))
        )
        self.model.listen(self.model_changed)
        self.set_html(self.model.html)

    def model_changed(self, preview, info):
        name = info["name"]
        self.css(name, getattr(self.model, name))

    def dragstop(self, *args):
        history.add(models.PreviewPositionChanged(self.model.key, self.css("left"), self.css("top")))

    def resize(self, event, *args):
        ltk.find(event.target).find("img, iframe").css("width", "100%").css("height", f"calc(100% - {constants.PREVIEW_HEADER_HEIGHT})")
        history.add(models.PreviewDimensionChanged(self.model.key, self.css("width"), self.css("height")))
    
    def move(self):
        self.draw_arrows()
        
    def click(self):
        self.appendTo(self.parent())  # raise

    def toggle_size(self, event):
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

    def toggle_embed(self, event):
        self.model.embed = "" if self.model.embed else "embed"
        history.add(models.CellEmbedChanged(self.model.key, self.model.embed))

    def draw_arrows(self):
        self.sheet.get_cell(self.model.key).draw_arrows()
        ltk.window.addArrow(ltk.find(f"#{self.model.key}"), self.element.find(".preview-key"))

    def set_html(self, html):
        html = self.fix_html(html)
        url = f"/embed?{constants.DATA_KEY_UID}={state.doc.uid}&{constants.DATA_KEY_CELL}={self.model.key}"
        embed = ltk.Link(url, "embed") if self.model.embed else ltk.Div("embed")
        toggle_size_label = "-" if self.height() > constants.PREVIEW_HEADER_HEIGHT or self.height() == 0 else "+"
        self.empty().append(
            ltk.HBox(
                ltk.Text(self.model.key).addClass("preview-key"),
                ltk.Checkbox(self.model.embed).on("change", ltk.proxy(lambda event: self.toggle_embed(event))),
                ltk.Div(embed.addClass("embed")),
                ltk.Button(toggle_size_label, ltk.proxy(lambda event: self.toggle_size(event))).addClass("toggle")
            ).addClass("preview-header"),
            ltk.Div(
                ltk.create(html)
            ).addClass("preview-content")
        )
        self.make_resizable()
        self.draw_arrows()
        self.fix_images()

    def fix_html(self, html):
        html = html.replace("script src=", "script crossorigin='anonymous' src=")
        if not html.startswith("<"):
            html = f"<div>{html}</div>"
        return html

    def fix_images(self):
        script = f"""
            $("img").each(function () {{
                $(this).attr("crossorigin", "anonymous").attr("src", $(this).attr("src"))
            }});
        """
        self.find("iframe").contents().find("body").append(
            ltk.create("<script>").html(script)
        )

    def make_resizable(self):
        preview = ltk.find(f"#preview-{self.model.key}")
        height = preview.height()
        preview.find("img, iframe").css("width", "100%").css("height", f"calc(100% - {constants.PREVIEW_HEADER_HEIGHT})")
        preview.resizable(ltk.to_js({"handles": "se"}))
        try:
            display = "block" if height > constants.PREVIEW_HEADER_HEIGHT else "none"
        except:
            display = "block"
        preview.find(".ui-resizable-handle").css("display", display)


def load(sheet):
    for key, preview in list(sheet.model.previews.items()):
        PreviewView(sheet, sheet.model.get_preview(**preview))


def add(sheet, key, html):
    if not key in previews:
        PreviewView(sheet, sheet.model.get_preview(key, html=html))
    previews[key].set_html(html)
    history.add(models.PreviewValueChanged(key, html))