import constants
import ltk
import time

from pyscript import window # type: ignore


class CodeCompletor():
    def __init__(self, editor):
        self.editor = editor
        self.editor.on("keydown", ltk.proxy(self.keydown))
        self.completions = []
        window.completePython = ltk.proxy(lambda text, line, ch: self.complete_python(text, line, ch))

    def getToken(self):
        cursor = self.editor.getCursor()
        return self.editor.getTokenAt(cursor)

    def insert(self, string):
        cursor = self.editor.getCursor()
        token = self.editor.getTokenAt(cursor)
        length = len(token.string) if string.startswith(token.string) else 0
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
        if not completions or token.string == " ":
            return
        ltk.find(".CodeMirror-code").append(
            ltk.find("<div>")
                .addClass("completions")
                .css("left", ltk.find(".CodeMirror-cursor").css("left"))
                .css("top", window.parseFloat(ltk.find(".CodeMirror-cursor").css("top")) + 24)
        )
        for choice in self.completions:
            ltk.find(".completions").append(
                ltk.find("<div>")
                    .addClass("choice")
                    .text(choice)
                    .on("click", self.pick)
                )
        ltk.find(".completions").find(".choice").eq(0).addClass("selected")

DEBUG_COMPLETION = False

def fuzzy_parse(text):
    import ast
    import traceback
    fuzzy_fixes = [
        "",
        "_",
        ")",
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
            return ast.parse(f"{text}{fix}")
        except:
            if DEBUG_COMPLETION:
                traceback.print_exc()
    return None


def complete_python(text, line, ch, cache):
    import ast
    lines = text[1:].split("\n")[:line + 1]
    lines[-1] = lines[-1][:ch + 1]
    text = "\n".join(lines)
    completions = []
    tree = fuzzy_parse(text)
    if not tree:
        return

    class CompletionFinder(ast.NodeVisitor):
        def __init__(self):
            self.context = {}
            self.context.update(cache)

        def inside(self, node):
            return hasattr(node, "lineno") and node.lineno == line + 1 and node.col_offset <= ch and ch <= node.end_col_offset

        def get_attributes(self, obj):
            from typing import Callable
            attributes = [
                f"{name}()" if isinstance(getattr(obj, name), Callable) else name
                for name in dir(obj)
            ]
            if DEBUG_COMPLETION:
                print("   *", type(obj).__name__, "=>", len(attributes), "attributes")
            return attributes

        def add_object(self, obj, match):
            self.add_attributes(self.get_attributes(obj), match)

        def matches(self, lower_attr, lower_match):
            for c in lower_match:
                if not c in lower_attr:
                    return False
            return True

        def add_attributes(self, attributes, match):
            lower_match = match.lower()
            for attr in attributes:
                if self.matches(attr.lower(), lower_match):
                    completions.append(attr)
        
        def get_value(self, node):
            start = time.time()
            try:
                value = eval(ast.unparse(node), self.context, self.context)
            except:
                # traceback.print_exc()
                value = ""
            return value

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

        def visit_Subscript(self, node):
            if DEBUG_COMPLETION:
                print(" - subscript", self.inside(node), ast.dump(node))
            if self.inside(node):
                slice = eval(ast.unparse(node.slice).lower())
                for key in self.context.get(node.value.id, {}):
                    if self.matches(key.lower(), slice):
                        completions.append(f'["{key}"]')

        def visit_Name(self, node):
            if DEBUG_COMPLETION:
                print(" - name", self.inside(node), isinstance(node.ctx, ast.Load), ast.dump(node))
            if self.inside(node) and isinstance(node.ctx, ast.Load):
                self.add_attributes(self.context.keys(), node.id)

        def generic_visit(self, node):
            if DEBUG_COMPLETION:
                print(" - generic", ast.dump(node))
            ast.NodeVisitor.generic_visit(self, node)

    if DEBUG_COMPLETION:
        print("Visit:")
    finder = CompletionFinder()
    finder.visit(tree)

    def sort(completions):
        public = sorted([attr for attr in completions if not attr.startswith("_")], key=lambda s: s.lower())
        private = sorted([attr for attr in completions if attr.startswith("_")], key=lambda s: s.lower())
        return public + private

    return sort(completions)