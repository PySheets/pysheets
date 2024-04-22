import ltk
import lsp

ltk_Div = ltk.Div

class Editor(ltk_Div):
    classes = [ "editor" ]

    def __init__(self, value=""):
        ltk.Div.__init__(self)
        self.editor = None
        self.set(value)
        self.element.css("height", "100vh")
        ltk.schedule(self.refresh, "force editor redraw", 0.5)
    
    def create_editor(self):
        if self.editor == None:
            self.editor = ltk.window.create_codemirror_editor(self.element[0], ltk.to_js({
                "mode": {
                    "name": "python",
                    "version": 3,
                    "singleLineStringErrors": False
                },
                "lineNumbers": True,
                "indentUnit": 4,
                "extraKeys": {
                    "Ctrl-Space": "autocomplete"
                },
                "matchBrackets": True,
            }))
            self.editor.setSize("100%", "100%")
            self.editor.on("blur", ltk.proxy(lambda *args: self.trigger("change")))
            self.code_completor = lsp.CodeCompletor(self.editor)

    def get(self):
        return self.editor.getValue()

    def get_cursor(self):
        return self.editor.getCursor()

    def set(self, value):
        self.create_editor()
        self.editor.setValue(str(value))
        return self

    def focus(self):
        self.editor.focus()
        return self

    def refresh(self):
        self.editor.refresh()
        return self

    def handle_code_completion(self, completions):
        if self.code_completor:
            self.code_completor.handle_code_completion(completions)

