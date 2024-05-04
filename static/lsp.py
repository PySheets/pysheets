import constants
import ltk

from pyscript import window # type: ignore


COMPLETION_MAKE_CELL_FUNCTION = f"{constants.ICON_STAR} Make this a Python cell function"
COMPLETION_IMPORT_SHEET = f"{constants.ICON_STAR} Import a sheet"

magic_completions = {
    COMPLETION_MAKE_CELL_FUNCTION: "=\n\n",
    COMPLETION_IMPORT_SHEET: "url = \"https://chrislaffra.com/forbes_ai_50_2024.csv\"\npysheets.load_sheet(url)",
}


class CodeCompletor():
    def __init__(self, editor):
        self.editor = editor
        self.editor.on("keydown", ltk.proxy(self.keydown))
        self.completions = []
        window.completePython = ltk.proxy(lambda text, line, ch: self.complete_python(text, line, ch))
        # editor.on("cursorActivity", ltk.proxy(lambda *args: self.trigger_completion()))
        # editor.on("focus", ltk.proxy(lambda *args: self.trigger_completion()))

    def trigger_completion(self):
        if not self.editor.getValue():
            self.handle_code_completion([
                COMPLETION_MAKE_CELL_FUNCTION,
            ])
        else:
            cursor = self.editor.getCursor()
            if cursor.ch == 0:
                self.handle_code_completion([
                    COMPLETION_IMPORT_SHEET,
                ])

    def getToken(self):
        cursor = self.editor.getCursor()
        return self.editor.getTokenAt(cursor)

    def insert(self, string):
        string = magic_completions.get(string, string)
        cursor = self.editor.getCursor()
        token = self.editor.getTokenAt(cursor)
        length = 0 if token.string == "." else len(token.string)
        self.editor.replaceRange(
            string,
            ltk.to_js({
                "line": cursor.line,
                "ch": cursor.ch - length,
            }),
            ltk.to_js({
                "line": cursor.line,
                "ch": cursor.ch,
            }),
        )
        if string.endswith(")"):
            self.editor.execCommand("goCharLeft")

    def pick(self, event):
        self.insert(ltk.find(".completions .selected").text())
        ltk.find(".completions").remove()
        event.preventDefault()

    def select(self, choice):
        if choice.length:
            ltk.find(".completions .choice").removeClass("selected")
            choice.addClass("selected")
            container = choice.parent()
            top = choice.position().top
            if top < 2 or top > container.height() - choice.height() - 2:
                choice.parent().prop("scrollTop", choice.index() * choice.outerHeight())

    def keydown(self, editor, event):
        key = event.key
        
        if ltk.find(".completions").length == 0:
            return
        elif key == "Enter" or key == "Tab":
            self.pick(event)
        elif key == "Escape":
            ltk.find(".completions").remove()
            self.editor.focus()
        elif key == "ArrowUp":
            self.select(ltk.find(".completions .selected").prev())
        elif key == "ArrowDown":
            self.select(ltk.find(".completions .selected").next())
        else:
            return
        event.preventDefault()

    def complete_python(self, text, line, ch):
        ltk.publish(
            "Application",
            "Worker",
            constants.TOPIC_WORKER_CODE_COMPLETE,
            [text, line, ch],
        )

    def handle_code_completion(self, completions):
        self.completions = completions
        ltk.find(".completions").remove()
        token = self.getToken()
        if not completions or token.string in [" ", ":", ";"]:
            return
        ltk.find(".CodeMirror-code").append(
            ltk.create("<div>")
                .addClass("completions")
                .css("left", ltk.find(".CodeMirror-cursor").css("left"))
                .css("top", window.parseFloat(ltk.find(".CodeMirror-cursor").css("top")) + 24)
        )
        for choice in self.completions:
            ltk.find(".completions").append(
                ltk.create("<div>")
                    .addClass("choice")
                    .text(choice)
                    .on("click", ltk.proxy(lambda event: self.pick(event)))
                )
        ltk.find(".completions").find(".choice").eq(0).addClass("selected")

DEBUG_COMPLETION = False

def fuzzy_parse(text):
    import ast
    import traceback
    fuzzy_fixes = [
        "",
        " :pass",
        "_:pass",
        "_",
        ")",
        " in []:pass",
        "))",
        ")))",
        "))))",
        ")))))",
        "\"\"]",
        "\"]",
        "']",
        "]",
    ]
    for fix in fuzzy_fixes:
        try:
            return fix, ast.parse(f"{text}{fix}")
        except:
            if DEBUG_COMPLETION:
                traceback.print_exc()
    return None, None



def complete_python(text, line, ch, cache):
    import ast
    lines = text[1:].split("\n")[:line + 1]
    lines[-1] = lines[-1][:ch + 1]
    text = "\n".join(lines)
    completions = []
    fix, tree = fuzzy_parse(text)
    if not tree:
        if DEBUG_COMPLETION:
            print("Cannot complete", repr(text), line, ch)
        return

    class CompletionFinder(ast.NodeVisitor):
        def __init__(self):
            self.context = {}
            self.context.update(cache)
            self.token = ""

        def inside(self, node):
            return hasattr(node, "lineno") and node.lineno == line + 1 and node.col_offset <= ch and ch <= node.end_col_offset

        def matches(self, lower_attr, lower_match):
            if fix and lower_match.endswith(fix):
                lower_match = lower_match[:-len(fix)]
            for c in lower_match:
                try:
                    lower_attr = lower_attr[lower_attr.index(c):]
                except:
                    return False
            return True

        def get_attributes(self, obj):
            from typing import Callable

            def is_callable(name):
                try:
                    return isinstance(getattr(obj, name), Callable) 
                except:
                    pass

            attributes = [
                f"{name}()" if is_callable(name) else name
                for name in dir(obj)
            ]
            if DEBUG_COMPLETION:
                print("   *", type(obj).__name__, "=>", len(attributes), "attributes")
            return attributes

        def add_object(self, obj, match):
            self.add_attributes(self.get_attributes(obj), match)

        def add_attributes(self, attributes, match):
            lower_match = match.lower()
            for attr in attributes:
                if self.matches(attr.lower(), lower_match):
                    completions.append(attr)
        
        def get_value(self, node):
            text = ast.unparse(node)
            if DEBUG_COMPLETION:
                print(" - get_value", repr(text), self.context.keys())
            try:
                return eval(text, self.context, self.context)
            except:
                # traceback.print_exc()
                function = f"{text}()"
                return self.context.get(function, "")

        def visit_Import(self, node):
            for alias in node.names:
                if DEBUG_COMPLETION:
                    print(" - import", ast.dump(alias))
                asname = alias.asname or alias.name
                try:
                    self.context[asname] = __import__(alias.name)
                except:
                    pass

        def visit_FunctionDef(self, node):
            if DEBUG_COMPLETION:
                print(" - function", ast.dump(node))
            def function(): pass
            self.context[f"{node.name}()"] = function

        def visit_Assign(self, node):
            if DEBUG_COMPLETION:
                print(" - assign", ast.dump(node))
            for name in node.targets:
                if not isinstance(name, ast.Name):
                    continue
                try:
                    self.context[name.id] = self.get_value(node.value)
                except:
                    # not a constant expression
                    self.context[name.id] = None
            ast.NodeVisitor.generic_visit(self, node)

        def visit_Attribute(self, node):
            if DEBUG_COMPLETION:
                print(" - attribute", self.inside(node), ast.dump(node))
            if self.inside(node):
                self.add_object(self.get_value(node.value), "" if node.attr == "_" else node.attr)
                self.token = node.attr

        def visit_Subscript(self, node):
            if DEBUG_COMPLETION:
                print(" - subscript", self.inside(node), ast.dump(node))
            if self.inside(node):
                slice = eval(ast.unparse(node.slice).lower())
                if isinstance(node.value, ast.Name):
                    for key in self.context.get(node.value.id, {}):
                        if self.matches(key.lower(), slice):
                            completions.append(f'["{key}"]')

        def visit_Name(self, node):
            if DEBUG_COMPLETION:
                print(" - name", self.inside(node), ast.dump(node))
            if self.inside(node):
                self.add_attributes(self.context.keys(), node.id)
                self.token = ast.unparse(node)

        def generic_visit(self, node):
            if DEBUG_COMPLETION:
                print(" - generic", ast.dump(node))
            ast.NodeVisitor.generic_visit(self, node)

    if DEBUG_COMPLETION:
        print("Visit:")
    finder = CompletionFinder()
    finder.visit(tree)

    def sort(completions):
        public = [attr for attr in completions if not attr.startswith("_")]
        prefix = sorted([attr for attr in public if attr.startswith(finder.token)], key=lambda s: s.lower())
        rest = sorted([attr for attr in public if not attr.startswith(finder.token)], key=lambda s: s.lower())
        private = sorted([attr for attr in completions if attr.startswith("_")], key=lambda s: s.lower())
        if DEBUG_COMPLETION:
            print("=> prefix", finder.token, prefix)
            print("=> rest", finder.token, rest)
        return prefix + rest + private

    return sort(completions)

