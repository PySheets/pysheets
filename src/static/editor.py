"""
Copyright (c) 2024 laffra - All Rights Reserved. 

A wrapper for the CodeMirror editor.
"""

import ltk
import lsp


class Editor(ltk.Div):
    """
    A wrapper for the CodeMirror editor that provides a convenient interface for interacting with a code editor.
    
    The `Editor` class is responsible for creating and managing a CodeMirror editor instance. It provides
    methods for setting the editor's value, getting the current cursor position, focusing
    the editor, refreshing the editor, and handling code completion.
    
    The class also sets up event listeners for the "blur" and "change" events, which 
    trigger the "change" event and clear any marks on the editor, respectively.
    """

    classes = [ "editor" ] # The CSS classes to apply to this ltk.Widget subclass

    def __init__(self, value=""):
        ltk.Div.__init__(self)
        self.editor = None
        self.code_completor = None
        self.set(value)
        self.element.css("height", "100vh")
        ltk.schedule(self.refresh, "force editor redraw", 0.5)

    def create_editor(self):
        """
        Creates a CodeMirror editor instance and sets up event listeners for the editor.
        """
        if self.editor is None:
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
            self.editor.on("change", ltk.proxy(lambda *args: self.clear_mark()))
            self.code_completor = lsp.CodeCompletor(self.editor)

    def get(self):
        """
        Returns the current value of the CodeMirror editor instance.
        """
        return self.editor.getValue()

    def get_cursor(self):
        """
        Returns the current cursor position of the CodeMirror editor instance.
        """
        return self.editor.getCursor()

    def set(self, value):
        """
        Sets the value of the CodeMirror editor instance.
        
        Args:
            value (str): The new value to set for the editor.
        """
        if self.editor and self.editor.hasFocus():
            return self
        self.create_editor()
        self.editor.setValue(str(value))
        return self

    def focus(self):
        """
        Focuses the CodeMirror editor instance. Browser keyboard events will be sent to the editor.
        
        Returns:
            self: The current instance of the editor object.
        """
        self.editor.focus()
        return self

    def refresh(self):
        """
        Refreshes the CodeMirror editor instance. This is needed to redraw the
        editor after the window has been resized.
        
        Returns:
            self: The current instance of the editor object.
        """
        self.editor.refresh()
        return self

    def handle_code_completion(self, completions):
        """
        Handles the code completion functionality for the editor computed by the worker.
        
        Args:
            completions (list): A list of code completion suggestions.
        """
        if self.code_completor:
            self.code_completor.handle_code_completion(completions)

    def clear_mark(self):
        """
        Clears the current line marker from the editor. Used to show the location of syntax errors.
        """
        ltk.window.editorClearLine()

    def mark_line(self, lineno):
        """
        Marks the specified line number in the editor with a visual indicator. 
        Used to show the location of syntax errors.
        
        Args:
            lineno (int): The line number to mark, starting from 1.
        """
        ltk.window.editorMarkLine(lineno - 1)

    def start_running(self):
        """
        Sets the editor in "run" mode.
        """
        self.find(".CodeMirror-scroll").css("background", "#f2f2f2")

    def stop_running(self):
        """
        Sets the editor in "edit" mode.
        """
        self.find(".CodeMirror-scroll").css("background", "#FFF")
