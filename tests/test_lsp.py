import sys
sys.path.append("static")

import ast
import lsp
import unittest
from unittest.mock import patch

import sys
sys.path.append("static")
sys.path.append("tests")

from static import worker

DEBUG_COMPLETION = True

orig_fuzzy_parse = lsp.fuzzy_parse
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
    lsp.fuzzy_parse = fuzzy_parse
lsp.DEBUG_COMPLETION = DEBUG_COMPLETION

class TestCompletePython(unittest.TestCase):

    def set_text(self, text):
        lines = text.split("\n")
        line = len(lines) - 1
        pos = len(lines[-1])
        return text, line, pos

    def test_completes_attributes(self):
        text, line, pos = self.set_text("=\nimport math\nmath.s")
        completions = worker.complete_python(text, line, pos, {})
        self.assertIn("sin()", completions)
        self.assertIn("sqrt()", completions)

    def test_completes_imported_modules(self):
        text, line, pos = self.set_text("=\nimport math\nma")
        completions = worker.complete_python(text, line, pos, {})
        self.assertIn("math", completions)

    def test_completes_variables_in_scope(self):
        text, line, pos = self.set_text("=\nx1 = x2 = 10\nx")
        completions = worker.complete_python(text, line, pos, {})
        self.assertIn("x1", completions)
        self.assertIn("x2", completions)

    def test_function_in_scope(self):
        text, line, pos = self.set_text("=\ndef function(): pass\nf")
        completions = worker.complete_python(text, line, pos, {})
        self.assertIn("function()", completions)

    def test_function_attributes(self):
        text, line, pos = self.set_text("=\ndef function(): pass\nfunction.")
        completions = worker.complete_python(text, line, pos, {})
        self.assertIn("__name__", completions)

    def test_match_ld(self):
        text, line, pos = self.set_text("=\nx = 'hello'\nx.cap")
        completions = worker.complete_python(text, line, pos, {})
        self.assertIn("capitalize()", completions)
        self.assertIn("isspace()", completions)

    def test_cache_list(self):
        worker.cache["D13"] = []
        text, line, pos = self.set_text("=\nD13.")
        completions = worker.complete_python(text, line, pos, worker.cache)
        self.assertIn("append()", completions)
        self.assertIn("insert()", completions)
        self.assertIn("clear()", completions)

    def test_cache_dict(self):
        worker.cache["D14"] = { "dogs": 0, "cats": 1 }
        text, line, pos = self.set_text("=\nD14[")
        completions = worker.complete_python(text, line, pos, worker.cache)
        self.assertIn('["cats"]', completions)
        self.assertIn('["dogs"]', completions)

    def test_dict_assign(self):
        text, line, pos = self.set_text("=\nmy_dict = { 'dogs': 0, 'cats': 1 }\nmy")
        completions = worker.complete_python(text, line, pos, {})
        self.assertIn('my_dict', completions)

    def test_dict_subscript(self):
        text, line, pos = self.set_text("=\nmy_dict = { 'dogs': 0, 'cats': 1 }\nmy_dict[")
        completions = worker.complete_python(text, line, pos, {})
        self.assertIn('["dogs"]', completions)
        self.assertIn('["cats"]', completions)

    def test_dataframe(self):
        import pandas as pd
        import numpy as np
        worker.cache["A1"] = pd.DataFrame(
            np.array(([1, 2, 3], [4, 5, 6])),
            index=['mouse', 'rabbit'],
            columns=['one', 'two', 'three']
        )
        text, line, pos = self.set_text("=\nA1.")
        completions = worker.complete_python(text, line, pos, worker.cache)
        self.assertIn('align()', completions)
        self.assertIn('fillna()', completions)
        self.assertIn('merge()', completions)



if __name__ == "__main__":
    unittest.main()