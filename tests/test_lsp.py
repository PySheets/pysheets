import ast
import unittest
from unittest.mock import patch

import sys
sys.path.append("static")
sys.path.append("tests")

from static import worker

completions = []


def clear_completions():
    completions.clear()

def add_completion(label):
    completions.append(label)

DEBUG_COMPLETION = True

orig_fuzzy_parse = worker.fuzzy_parse
worker.worker_print = worker.orig_print

def fuzzy_parse(text):
    print(f"Fuzzyparse: {repr(text)}")
    print("=" * 80)
    tree = orig_fuzzy_parse(text)
    print("-" * 80)
    print(ast.dump(tree, indent=4))
    print("=" * 80)
    return tree

if DEBUG_COMPLETION:
    worker.fuzzy_parse = fuzzy_parse
worker.clear_completions = clear_completions
worker.add_completion = add_completion
worker.DEBUG_COMPLETION = DEBUG_COMPLETION

class TestCompletePython(unittest.TestCase):
    completions = []

    def setUp(self) -> None:
        completions.clear()
        return super().setUp()
        
    def set_text(self, text):
        lines = text.split("\n")
        line = len(lines) - 1
        pos = len(lines[-1])
        return text, line, pos

    def test_completes_attributes(self):
        text, line, pos = self.set_text("=\nimport math\nmath.s")
        worker.complete_python(text, line, pos)
        self.assertIn("sin", completions)
        self.assertIn("sqrt", completions)

    def test_completes_imported_modules(self):
        text, line, pos = self.set_text("=\nimport math\nma")
        worker.complete_python(text, line, pos)
        self.assertIn("math", completions)

    def test_completes_variables_in_scope(self):
        text, line, pos = self.set_text("=\nx1 = x2 = 10\nx")
        worker.complete_python(text, line, pos)
        self.assertIn("x1", completions)
        self.assertIn("x2", completions)

    def test_function_in_scope(self):
        text, line, pos = self.set_text("=\ndef function(): pass\nf")
        worker.complete_python(text, line, pos)
        self.assertIn("function", completions)

    def test_function_attributes(self):
        text, line, pos = self.set_text("=\ndef function(): pass\nfunction.")
        worker.complete_python(text, line, pos)
        self.assertIn("__name__", completions)

    def test_pysheets(self):
        text, line, pos = self.set_text("=\npysheets.")
        worker.complete_python(text, line, pos)
        self.assertIn("cell", completions)
        self.assertIn("load", completions)
        self.assertIn("load_sheet", completions)
        self.assertIn("sheet", completions)

    def test_match_ld(self):
        text, line, pos = self.set_text("=\npysheets.ld")
        worker.complete_python(text, line, pos)
        expected = ['load', 'load_sheet', '__delattr__', '__module__']
        self.assertEquals(completions, expected)

    def test_cache_list(self):
        worker.cache["D13"] = []
        text, line, pos = self.set_text("=\nD13.")
        worker.complete_python(text, line, pos)
        self.assertIn("append", completions)
        self.assertIn("insert", completions)
        self.assertIn("clear", completions)

    def test_cache_dict(self):
        worker.cache["D14"] = { "dogs": 0, "cats": 1 }
        text, line, pos = self.set_text("=\nD14[")
        worker.complete_python(text, line, pos)
        self.assertIn('"cats"]', completions)
        self.assertIn('"dogs"]', completions)

    def test_dict_assign(self):
        text, line, pos = self.set_text("=\nmy_dict = { 'dogs': 0, 'cats': 1 }\nmy")
        worker.complete_python(text, line, pos)
        self.assertIn('my_dict', completions)

    def test_dict_assign_partial(self):
        text, line, pos = self.set_text("=\nmy_dict = { 'dogs': 0, 'cats': 1 }\nmy_dict['d")
        worker.complete_python(text, line, pos)
        self.assertIn('"dogs"]', completions)
        self.assertNotIn('"cats"]', completions)

    def test_match_dict_partial_d(self):
        worker.cache["D33"] = { "dogs": 0, "cats": 1 }
        text, line, pos = self.set_text("=\nD33['d'")
        worker.complete_python(text, line, pos)
        self.assertEquals(completions, ['"dogs"]'])

    def test_match_dict_partial_s(self):
        worker.cache["D33"] = { "dogs": 0, "cats": 1 }
        text, line, pos = self.set_text("=\nD33[\"s\"")
        worker.complete_python(text, line, pos)
        self.assertEquals(completions, ['"dogs"]', '"cats"]'])


if __name__ == "__main__":
    unittest.main()