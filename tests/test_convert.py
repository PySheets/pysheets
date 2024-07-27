"""
CopyRight (c) 2024 - Chris Laffra - All Rights Reserved.

Tests the `convert` function from the `static.api` module.
"""

import unittest

import sys
sys.path.append("..")

from tests import mocks # pylint: disable=wrong-import-position,unused-import
from static import api # pylint: disable=wrong-import-position


class TestConvert(unittest.TestCase):
    """
    This test suite verifies the behavior of the `convert` function, which is 
    responsible for converting string input to the appropriate data type (float, int, or string).
    """

    def test_convert_float(self):
        """
        Tests that the `convert` function correctly converts a string representation of a float to a float.
        """
        self.assertEqual(api.convert("1.5"), 1.5)

    def test_convert_int(self):
        """
        Tests that the `convert` function correctly converts a string representation of an integer to an integer.
        """
        self.assertEqual(api.convert("5"), 5)

    def test_convert_string(self):
        """
        Tests that the `convert` function correctly converts a string representation of a string to a string.
        """
        self.assertEqual(api.convert("hello"), "hello")

    def test_convert_empty(self):
        """
        Tests that the `convert` function correctly converts an empty string to 0.
        """
        self.assertEqual(api.convert(""), 0)
