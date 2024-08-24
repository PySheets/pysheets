"""
CopyRight (c) 2024 - Chris Laffra - All Rights Reserved.

Tests the `intercept_last_expression` function from the `api` module, which is responsible
for intercepting and modifying the last expression in a given script.
"""

import sys
import unittest

sys.path.append("src")

from tests import mocks # pylint: disable=wrong-import-position,unused-import
from static import api # pylint: disable=wrong-import-position


class TestLastExpression(unittest.TestCase):
    """
    Tests the `intercept_last_expression` function from the `api` module, which is responsible
    for intercepting and modifying the last expression in a given script.
    """

    def test_intercept_empty(self):
        """
        Tests that `intercept_last_expression` correctly handles an empty script.
        """
        script = ''
        actual = api.intercept_last_expression(script)
        expected = ''
        self.assertEqual(actual, expected)

    def test_intercept_multiline_dict(self):
        """
        Tests that `intercept_last_expression` correctly handles a multiline dictionary expression.
        """
        script = "x = {\n    'y':\n     4,\n }"
        actual = api.intercept_last_expression(script)
        expected = "_ = " + script
        self.assertEqual(actual, expected)

    def test_intercept_multiline_call(self):
        """
        Tests that `intercept_last_expression` correctly handles a multiline function call expression.
        """
        script = "print(\n1,\n2,\n3\n)\nprint(\n4,\n3,\n4\n)"
        actual = api.intercept_last_expression(script)
        expected = "print(\n1,\n2,\n3\n)\n_ = print(\n4,\n3,\n4\n)"
        self.assertEqual(actual, expected)

    def test_intercept_multiline(self):
        """
        Tests that `intercept_last_expression` correctly handles a script with multiple lines of assignments.
        """
        script = "x = 1\ny = 2\nz = 3"
        actual = api.intercept_last_expression(script)
        expected = "x = 1\ny = 2\n_ = z = 3"
        self.assertEqual(actual, expected)
