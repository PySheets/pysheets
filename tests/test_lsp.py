"""
CopyRight (c) 2024 - Chris Laffra - All Rights Reserved.

This module contains unit tests for the Language Server Protocol (LSP) implementation in the `lsp` module.
"""

import sys
import unittest
import unittest.mock

sys.path.append("..")

from tests import mocks # pylint: disable=wrong-import-position,unused-import
from static import lsp # pylint: disable=wrong-import-position
from static import worker # pylint: disable=wrong-import-position

orig_fuzzy_parse = lsp.fuzzy_parse


class TestCompletePython(unittest.TestCase):
    """
    This class contains unit tests for the Language Server Protocol (LSP) implementation in
    the `lsp` module. The tests cover various aspects of the LSP completion functionality.
    """

    def set_text(self, text):
        """
        Helper function to set the text, line, and position for the current test case.
        """
        lines = text.split("\n")
        line = len(lines) - 1
        pos = len(lines[-1])
        return text, line, pos

    def test_completes_attributes(self):
        """
        Tests completion of attributes of imported modules.
        """
        text, line, pos = self.set_text("=\nimport math\nmath.s")
        completions = lsp.complete_python(text, line, pos, {}, {})
        self.assertIn("sin(x:Any)", completions)
        self.assertIn("sqrt(x:Any)", completions)

    def test_completes_imported_modules(self):
        """
        Tests completion of names of imported modules.
        """
        text, line, pos = self.set_text("=\nimport math\nma")
        completions = lsp.complete_python(text, line, pos, {}, {})
        self.assertIn("math", completions)

    def test_completes_variables_in_scope(self):
        """
        Tests completion of variables available in the current scope.
        """
        text, line, pos = self.set_text("=\nx1 = x2 = 10\nx")
        completions = lsp.complete_python(text, line, pos, {}, {})
        self.assertIn("x1", completions)
        self.assertIn("x2", completions)

    def test_function_in_scope(self):
        """
        Tests completion of function names available in the current scope.
        """
        text, line, pos = self.set_text("=\ndef function(): pass\nf")
        completions = lsp.complete_python(text, line, pos, {}, {})
        self.assertIn("function()", completions)

    def test_function_attributes(self):
        """
        Tests completion of function attributes available in the current scope.
        """
        text, line, pos = self.set_text("=\ndef function(): pass\nfunction.")
        completions = lsp.complete_python(text, line, pos, {}, {})
        self.assertIn("__name__", completions)

    def test_match_cap(self):
        """
        Tests completion of specific string methods available on a string.
        
        This test case checks that the code completion of "ca" on a string
        includes `capitalize()`, `isdecimal()`, and `casefold()`.
        """
        text, line, pos = self.set_text("=\nx = 'hello'\nx.ca")
        completions = lsp.complete_python(text, line, pos, {}, {})
        self.assertIn("capitalize()", completions)
        self.assertIn("isdecimal()", completions)
        self.assertIn("casefold()", completions)

    def test_cache_list(self):
        """
        Tests completion of list methods available on a list stored in the worker cache.
        """
        worker.cache["D13"] = []
        text, line, pos = self.set_text("=\nD13.")
        completions = lsp.complete_python(text, line, pos, worker.cache, {})
        self.assertIn("append(object:Any)", completions)
        self.assertIn("insert(index:Any, object:Any)", completions)
        self.assertIn("clear()", completions)

    def test_cache_dict(self):
        """
        Tests completion of dictionary keys available in the current scope.
        """
        worker.cache["D14"] = { "dogs": 0, "cats": 1 }
        text, line, pos = self.set_text("=\nD14[")
        completions = lsp.complete_python(text, line, pos, worker.cache, {})
        self.assertIn('["cats"]', completions)
        self.assertIn('["dogs"]', completions)

    def test_dict_assign(self):
        """
        Tests completion of dictionary keys available in the current scope.
        """
        text, line, pos = self.set_text("=\nmy_dict = { 'dogs': 0, 'cats': 1 }\nmy")
        completions = lsp.complete_python(text, line, pos, {}, {})
        self.assertIn('my_dict', completions)

    def test_str_isdecimal(self):
        """
        Tests completion of the `isdecimal()` string method on a string.
        """
        text, line, pos = self.set_text("=\ns='abc'\ns.isd")
        completions = lsp.complete_python(text, line, pos, {}, {})
        self.assertIn('isdecimal()', completions)
        self.assertNotIn('capitalize()', completions)

    def test_sorting(self):
        """
        Tests completion of the `center()` string method on a string.
        """
        text, line, pos = self.set_text("=\ns='abc'\ns.ce")
        completions = lsp.complete_python(text, line, pos, {}, {})
        self.assertEqual("center(width:Any, fillchar:Any)", completions[0])

    def test_if(self):
        """
        Tests completion of the `center()` string method on a string.
        """
        text, line, pos = self.set_text("=\ns='abc'\nif s.")
        completions = lsp.complete_python(text, line, pos, {}, {})
        self.assertIn("center(width:Any, fillchar:Any)", completions)

    def test_for(self):
        """
        Tests completion of variables available in the current scope when using a for loop.
        """
        text, line, pos = self.set_text("=\nstring1='abc'\nstring2='def'\nfor s")
        completions = lsp.complete_python(text, line, pos, {}, {})
        self.assertIn("string1", completions)
        self.assertIn("string2", completions)

    def test_for_in(self):
        """
        Tests completion of variables available in the current scope when using a for loop.
        """
        text, line, pos = self.set_text("=\nstring1='abc'\nstring2='def'\nfor s in s")
        completions = lsp.complete_python(text, line, pos, {}, {})
        self.assertIn("string1", completions)
        self.assertIn("string2", completions)

    def test_dict_subscript(self):
        """
        Tests completion of dictionary keys available in the current scope.
        """
        text, line, pos = self.set_text("=\nmy_dict = { 'dogs': 0, 'cats': 1 }\nmy_dict[")
        completions = lsp.complete_python(text, line, pos, {}, {})
        self.assertIn('["dogs"]', completions)
        self.assertIn('["cats"]', completions)
