"""
Copyright (c) 2024 laffra - All Rights Reserved. 

Provides code completion functionality in the editor. Listens for key events
in the editor and triggers code completion when appropriate. 
Also handles the display and selection of completion options.
"""

import constants
import ltk

import api


COMPLETION_MAKE_CELL_FUNCTION = f"{constants.ICON_STAR} Make this a Python cell function"
COMPLETION_IMPORT_SHEET = f"{constants.ICON_STAR} Import a sheet"

FORBES = "https://raw.githubusercontent.com/PySheets/pysheets/main/src/datafiles/forbes-ai-50.csv"
MAGIC_COMPLETIONS = {
    COMPLETION_MAKE_CELL_FUNCTION: "=\n\n",
    COMPLETION_IMPORT_SHEET: f"url = \"{FORBES}\"\npysheets.load_sheet(url)",
}


class CodeCompletor():
    """
    Provides a code completion functionality in the editor. Listens for key events in the editor
    and triggers code completion when appropriate. Also handles the display and selection of 
    completion options.
    """

    def __init__(self, editor):
        self.editor = editor
        self.editor.on("keydown",
                ltk.proxy(lambda editor, event: self.keydown(editor, event))) # pylint: disable=unnecessary-lambda
        self.completions = []
        ltk.window.completePython = ltk.proxy(
            lambda text, line, ch: self.complete_python(text, line, ch) # pylint: disable=unnecessary-lambda
        )

    def trigger_completion(self):
        """
        Triggers code completion based on the current state of the editor.
        """
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

    def get_token(self):
        """
        Returns the token at the current cursor position in the editor.
        
        Args:
            self (CodeCompletor): The CodeCompletor instance.
        
        Returns:
            The token at the current cursor position.
        """
        cursor = self.editor.getCursor()
        return self.editor.getTokenAt(cursor)

    def insert(self, string: str):
        """
        Inserts the given string into the editor at the current cursor position,
        replacing the current token if it exists.
        """
        string = MAGIC_COMPLETIONS.get(string, string)
        if "(" in string:
            string = string.split("(")[0] + "()"
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
        """
        Inserts the selected completion into the editor and removes the completion popup.
        
        Args:
            self (CodeCompletor): The CodeCompletor instance.
            event (Event): The click event on the selected completion.
        """
        self.insert(ltk.find(event.target).text())
        hide_completions()
        event.preventDefault()

    def pick_selected(self, event):
        """
        Inserts the selected completion into the editor and removes the completion popup.
        
        Args:
            self (CodeCompletor): The CodeCompletor instance.
            event (Event): The click event on the selected completion.
        """
        self.insert(ltk.find(".completions .selected").text())
        hide_completions()
        event.preventDefault()

    def select(self, choice):
        """
        Selects the given choice in the completion popup and scrolls the popup to ensure the selected choice is visible.
        
        Args:
            self (CodeCompletor): The CodeCompletor instance.
            choice (jQuery): The jQuery object representing the selected completion choice.
        """
        if choice.length:
            ltk.find(".completions .choice").removeClass("selected")
            choice.addClass("selected")
            container = choice.parent()
            top = choice.position().top
            if top < 2 or top > container.height() - choice.height() - 2:
                choice.parent().prop("scrollTop", choice.index() * choice.outerHeight())

    def keydown(self, editor, event): # pylint: disable=unused-argument
        """
        Handles keyboard events for the code completion popup.
        
        Args:
            self (CodeCompletor): The CodeCompletor instance.
            editor (CodeMirror): The CodeMirror editor instance.
            event (Event): The keyboard event.
        """
        key = event.key

        if ltk.find(".completions").length == 0:
            return

        if key in ["Enter", "Tab"]:
            self.pick_selected(event)
        elif key == "Escape":
            hide_completions()
            self.editor.focus()
        elif key == "ArrowUp":
            self.select(ltk.find(".completions .selected").prev())
        elif key == "ArrowDown":
            self.select(ltk.find(".completions .selected").next())
        else:
            hide_completions()
            return
        event.preventDefault()

    def complete_python(self, text, line, ch):
        """
        Requests code completion for the given text, line, and column position.
        
        Args:
            self (CodeCompletor): The CodeCompletor instance.
            text (str): The current text in the editor.
            line (int): The current line number in the editor.
            ch (int): The current column number in the editor.
        """
        ltk.publish(
            "Application",
            "Worker",
            constants.TOPIC_WORKER_CODE_COMPLETE,
            [text, line, ch],
        )

    def handle_code_completion(self, completions):
        """
        Handles the display and interaction of the code completion popup.
        
        When code completions are received, this method creates a popup div with the
        available completion choices. It positions the popup relative to the cursor
        and adds click handlers to each completion choice. It also handles keyboard
        events for navigating and selecting the completion choices.
        """
        self.completions = completions
        token = self.get_token()
        if not completions or token.string in [" ", ":", ";"]:
            return

        cursor_left = ltk.window.parseInt(ltk.find(".CodeMirror-cursor").css("left"))
        gutter_width = ltk.find(".CodeMirror-gutters").width()
        hide_completions()
        ltk.find(".editor").append(
            ltk.create("<div>")
                .addClass("completions")
                .css("left", cursor_left + gutter_width)
                .css("top", ltk.window.parseFloat(ltk.find(".CodeMirror-cursor").css("top")) + 24)
        )
        for choice in self.completions:
            ltk.find(".completions").append(
                ltk.create("<div>")
                    .addClass("choice")
                    .text(choice)
                    .on("mousedown", ltk.proxy(lambda event: self.pick(event))) # pylint: disable=unnecessary-lambda
                )
        ltk.find(".completions").find(".choice").eq(0).addClass("selected")

DEBUG_COMPLETION = False

def fuzzy_parse(text):
    """
    Attempts to parse the given text using a set of fuzzy fixes, returning the fix
    used and the parsed AST if successful.
    
    Args:
        text (str): The text to parse.
    
    Returns:
        Tuple[str, ast.AST | None]: A tuple containing the fix used (if any) and
            the parsed AST (if successful), or (None, None) if parsing failed.
    """
    import ast # pylint: disable=import-outside-toplevel
    import traceback # pylint: disable=import-outside-toplevel
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
        except SyntaxError:
            if DEBUG_COMPLETION:
                traceback.print_exc()
    return None, None


def hide_completions():
    """
    Removes the code completion popup.
    """
    ltk.find(".completions").remove()


def complete_python(text, line, ch, cache, results):  # pylint: disable=too-many-statements
    """
    Attempts to parse the given text using a set of fuzzy fixes, returning the fix used and 
    the parsed AST if successful.
    
    Args:
        text (str): The text to parse.
    
    Returns:
        Tuple[str, ast.AST | None]: A tuple containing the fix used (if any) and the parsed AST
            (if successful), or (None, None) if parsing failed.
    """
    import ast # pylint: disable=import-outside-toplevel
    lines = text[1:].split("\n")[:line + 1]
    lines[-1] = lines[-1][:ch + 1]
    text = "\n".join(lines)
    completions = []
    fix, tree = fuzzy_parse(text)
    if not tree:
        if DEBUG_COMPLETION:
            print("Cannot complete", repr(text), line, ch)
        return []

    class CompletionFinder(ast.NodeVisitor):
        """
        The `CompletionFinder` class is responsible for finding and sorting code completions 
        based on the given text, line, and column position. It uses a set of "fuzzy fixes" 
        to attempt to parse the text, and then visits the resulting AST to extract relevant completion candidates.
        """
        def __init__(self):
            self.context = {}
            self.context.update(cache)
            self.context.update(results)
            self.context["pysheets"] = api.PySheets(None, cache)
            self.token = ""

        def inside(self, node):
            """
            Checks if the given AST node is located within the current line and column range.
            
            Args:
                node (ast.AST): The AST node to check.
                line (int): The current line number.
                ch (int): The current column number.
            
            Returns:
                bool: True if the node is located within the current line and column range, False otherwise.
            """
            return hasattr(node, "lineno") and node.lineno == line + 1 and node.col_offset <= ch <= node.end_col_offset

        def matches(self, lower_attr, lower_match):
            """
            Checks if a given attribute string matches a search string using a fuzzy matching algorithm.
            
            Args:
                lower_attr (str): The lowercase version of the attribute string to match against.
                lower_match (str): The lowercase version of the search string.
            
            Returns:
                bool: True if the attribute string matches the search string, False otherwise.
            """
            if fix and lower_match.endswith(fix):
                lower_match = lower_match[:-len(fix)]
            for c in lower_match:
                try:
                    lower_attr = lower_attr[lower_attr.index(c):]
                except ValueError:
                    return False
            return True

        def get_attributes(self, obj):
            """
            Retrieves the attributes of the given object, including both properties and callable methods.
            """
            from typing import Callable # pylint: disable=import-outside-toplevel

            def is_callable(name):
                try:
                    return isinstance(getattr(obj, name), Callable)
                except AttributeError:
                    return None

            def get_parameters(name):
                import inspect # pylint: disable=import-outside-toplevel
                function = getattr(obj, name)
                try:
                    signature = inspect.signature(function)
                except ValueError:
                    return []
                parameters = []
                for param in signature.parameters.values():
                    param_name = param.name
                    param_type = param.annotation.__name__ if param.annotation != inspect.Parameter.empty else None
                    parameters.append(f"{param_name}:{param_type or 'Any'}")
                return ", ".join(parameters)

            attributes = [
                f"{name}({get_parameters(name)})" if is_callable(name) else name
                for name in dir(obj)
            ]
            if DEBUG_COMPLETION:
                print("   *", type(obj).__name__, "=>", len(attributes), "attributes")
            return attributes

        def add_object(self, obj, match):
            """
            Adds the attributes of the given object to the list of completions if they match the provided search string.
            
            Args:
                obj (object): The object whose attributes should be added to the completions.
                match (str): The search string to match the object's attributes against.
            """
            self.add_attributes(self.get_attributes(obj), match)

        def add_attributes(self, attributes, match):
            """
            Adds the given attributes to the list of completions if they match the provided search string.
            
            Args:
                attributes (list[str]): The list of attributes to add to the completions.
                match (str): The search string to match the attributes against.
            """
            lower_match = match.lower()
            for attr in attributes:
                if self.matches(attr.lower(), lower_match):
                    completions.append(attr)

        def get_value(self, node):
            """
            Evaluates the given AST node and returns its value, using the context dictionary to resolve any references.
            
            Args:
                node (ast.AST): The AST node to evaluate.
            
            Returns:
                Any: The value of the evaluated node, or an empty string if the evaluation fails.
            """
            text = ast.unparse(node)
            if DEBUG_COMPLETION:
                print(" - get_value", repr(text), self.context.keys())
            try:
                return eval(text, self.context, self.context)  # pylint: disable=eval-used
            except NameError:
                # traceback.print_exc()
                function = f"{text}()"
                return self.context.get(function, "")

        def visit_Import(self, node): # pylint: disable=invalid-name
            """
            Handles the import of modules and their aliases in the completion context.
            
            Args:
                node (ast.Import): The AST node representing the import statement.
            """
            for alias in node.names:
                if DEBUG_COMPLETION:
                    print(" - import", ast.dump(alias))
                asname = alias.asname or alias.name
                try:
                    self.context[asname] = __import__(alias.name)
                except ImportError:
                    pass

        def visit_FunctionDef(self, node): # pylint: disable=invalid-name
            """
            Handles the definition of functions in the completion context.
            
            Args:
                node (ast.FunctionDef): The AST node representing the function definition.
            """
            if DEBUG_COMPLETION:
                print(" - function", ast.dump(node))
            def function():
                pass
            self.context[f"{node.name}()"] = function

        def visit_Assign(self, node): # pylint: disable=invalid-name
            """
            Handles the assignment of values to variables in the completion context.
            
            Args:
                node (ast.Assign): The AST node representing the assignment statement.
            """
            if DEBUG_COMPLETION:
                print(" - assign", ast.dump(node))
            for name in node.targets:
                if not isinstance(name, ast.Name):
                    continue
                try:
                    self.context[name.id] = self.get_value(node.value)
                except NameError:
                    # not a constant expression
                    self.context[name.id] = None
            ast.NodeVisitor.generic_visit(self, node)

        def visit_Attribute(self, node): # pylint: disable=invalid-name
            """
            Handles the access of attributes on objects in the completion context.
            
            Args:
                node (ast.Attribute): The AST node representing the attribute access.
            """
            if DEBUG_COMPLETION:
                print(" - attribute", self.inside(node), ast.dump(node))
            if self.inside(node):
                self.add_object(self.get_value(node.value), "" if node.attr == "_" else node.attr)
                self.token = node.attr

        def visit_Subscript(self, node): # pylint: disable=invalid-name
            """
            Handles the access of subscripts on objects in the completion context.
            
            Args:
                node (ast.Subscript): The AST node representing the subscript access.
            """
            if DEBUG_COMPLETION:
                print(" - subscript", self.inside(node), ast.dump(node))
            if self.inside(node):
                if isinstance(node.value, ast.Name):
                    node_slice = eval(ast.unparse(node.slice).lower())  # pylint: disable=eval-used
                    for key in self.context.get(node.value.id, {}):
                        if self.matches(key.lower(), node_slice):
                            completions.append(f'["{key}"]')

        def visit_Name(self, node): # pylint: disable=invalid-name
            """
            Handles the access of names in the completion context.
            
            Args:
                node (ast.Name): The AST node representing the name access.
            """
            if DEBUG_COMPLETION:
                print(" - name", self.inside(node), ast.dump(node))
            if self.inside(node):
                self.add_attributes(self.context.keys(), node.id)
                self.token = ast.unparse(node)

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
