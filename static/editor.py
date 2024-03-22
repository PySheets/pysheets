import ltk


class Editor(ltk.Div):
    classes = [ "editor" ]

    def __init__(self, value=""):
        ltk.Div.__init__(self)
        self.editor = None
        self.set(value)
        self.element.css("height", "100vh")
        ltk.schedule(self.refresh, "force editor redraw", 0.5)
    
    def create_editor(self):
        if self.editor == None:
            self.editor = ltk.window.CodeMirror(self.element[0], ltk.to_js({
                "mode": "python",
                "lineNumbers": True,
            }))
            self.editor.setSize("100%", "100%")
            self.editor.on("blur", ltk.proxy(lambda *args: self.trigger("change")))

    def get(self):
        return self.editor.getValue()

    def set(self, value):
        self.create_editor()
        self.editor.setValue(str(value))

    def refresh(self):
        self.editor.refresh()

from ltk import schedule, window, TableRow, TableData, to_js, proxy, VBox, HBox

