"""
CopyRight (c) 2024 - Chris Laffra - All Rights Reserved.

Tests the `intercept_last_expression` function from the `static.api` module.
"""


import sys
import unittest
import unittest.mock

sys.path.append("..")

from tests import mocks # pylint: disable=wrong-import-position,unused-import
from static import api # pylint: disable=wrong-import-position


class TestEditScript(unittest.TestCase):
    """
    Tests the `intercept_last_expression` function from the `static.api` module.
    """

    def test_empty(self):
        """
        Tests an empty script.
        """
        script = ""
        expected = ""
        self.assertEqual(api.intercept_last_expression(script), expected)

    def test_function(self):
        """
        Tests a function call.
        """
        script = "def foo():\n  return 4\n\nfoo()"
        expected = "def foo():\n  return 4\n\n_ = foo()"
        self.assertEqual(api.intercept_last_expression(script), expected)

    def test_multiline_expression(self):
        """
        Tests multiple expressions.
        """
        script = "x=4\n'a' + '''b\nc'''"
        expected = "x=4\n_ = 'a' + '''b\nc'''"
        self.assertEqual(api.intercept_last_expression(script), expected)

    def test_call(self):
        """
        Tests a call on a cell reference.
        """
        script = "C11.plot()"
        expected = "_ = C11.plot()"
        self.assertEqual(api.intercept_last_expression(script), expected)

    def test_expression(self):
        """
        Tests a simple expression.
        """
        script = "foo()"
        expected = "_ = foo()"
        self.assertEqual(api.intercept_last_expression(script), expected)

    def test_assignment(self):
        """
        Tests an assignment statement.
        """
        script = "x = 1 + 2"
        expected = "_ = x = 1 + 2"
        self.assertEqual(api.intercept_last_expression(script), expected)

    def test_loop(self):
        """
        Tests a while loop.
        """
        script = "while x:\n  pass"
        expected = script + "\n_ = None"
        self.assertEqual(api.intercept_last_expression(script), expected)

    def test_import(self):
        """
        Tests an import statement.
        """
        script = "import sys"
        expected = script + "\n_ = None"
        self.assertEqual(api.intercept_last_expression(script), expected)

    def test_intercept_last_expression_with_invalid_syntax(self):
        """
        Tests a Syntax Error.
        """
        script = "x = 1 +)"
        with self.assertRaises(SyntaxError):
            api.intercept_last_expression(script)
