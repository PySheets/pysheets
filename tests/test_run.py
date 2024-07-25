import sys
import unittest

import sys
sys.path.append("..")

from static.api import intercept_last_expression


class TestEditScript(unittest.TestCase):
    def test_empty(self):
        input = ""
        expected = ""
        self.assertEquals(intercept_last_expression(input), expected)

    def test_function(self):
        input = "def foo():\n  return 4\n\nfoo()"
        expected = "def foo():\n  return 4\n\n_ = foo()"
        self.assertEquals(intercept_last_expression(input), expected)

    def test_multiline_expression(self):
        input = "x=4\n'a' + '''b\nc'''"
        expected = "x=4\n_ = 'a' + '''b\nc'''"
        self.assertEquals(intercept_last_expression(input), expected)

    def test_call(self):
        input = "C11.plot()"
        expected = "_ = C11.plot()"
        self.assertEquals(intercept_last_expression(input), expected)

    def test_expression(self):
        input = "foo()"
        expected = "_ = foo()"
        self.assertEquals(intercept_last_expression(input), expected)

    def test_assignment(self):
        input = "x = 1 + 2"
        expected = "_ = x = 1 + 2"
        self.assertEquals(intercept_last_expression(input), expected)

    def test_loop(self):
        input = "while x:\n  pass"
        expected = input + "\n_ = None"
        self.assertEquals(intercept_last_expression(input), expected)

    def test_import(self):
        input = "import sys"
        expected = input + "\n_ = None"
        self.assertEquals(intercept_last_expression(input), expected)

    def test_intercept_last_expression_with_invalid_syntax(self):
        script = "x = 1 +)"
        with self.assertRaises(SyntaxError):
            intercept_last_expression(script)
