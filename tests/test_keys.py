"""
CopyRight (c) 2024 - Chris Laffra - All Rights Reserved.

Tests for the key-related utility functions in the static.api module.
"""

import sys
import unittest
import unittest.mock

sys.path.append("..")

from tests import mocks # pylint: disable=wrong-import-position,unused-import
from static import api # pylint: disable=wrong-import-position


class TestKeys(unittest.TestCase):
    """
    Tests the key-related utility functions in the static.api module.
    """

    def test_get_key(self):
        """
        Tests the `get_key_from_col_row` function, which generates a spreadsheet-style
        cell reference (e.g. "A1", "AA2", "AB1") from a given column and row numbers.
        """
        self.assertEqual(api.get_key_from_col_row(1, 1), "A1")
        self.assertEqual(api.get_key_from_col_row(27, 2), "AA2")
        self.assertEqual(api.get_key_from_col_row(28, 1), "AB1")

    def test_get_col_row(self):
        """
        Tests the `get_col_row_from_key` function, which extracts the column and row
        numbers from a spreadsheet-style cell reference (e.g. "A1", "AA2", "AB1").
        """
        self.assertEqual(api.get_col_row_from_key("A1"), (1, 1))
        self.assertEqual(api.get_col_row_from_key("AA1"), (27, 1))
        self.assertEqual(api.get_col_row_from_key("AB2"), (28, 2))

    def test_col_name(self):
        """
        Tests the `get_column_name` function, which generates a spreadsheet-style column
        name (e.g. "A", "B", "AA", "AB") from a given column number.
        """
        self.assertEqual(api.get_column_name(1), "A")
        self.assertEqual(api.get_column_name(2), "B")
        self.assertEqual(api.get_column_name(27), "AA")
        self.assertEqual(api.get_column_name(28), "AB")
