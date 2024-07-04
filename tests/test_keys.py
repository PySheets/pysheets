import mocks
import unittest

import sys
sys.path.append("..")

from static.pysheets import get_col_row_from_key, get_key_from_col_row, get_column_name


class TestKeys(unittest.TestCase):

    def test_0_0(self):
        self.assertEqual(get_key_from_col_row(1, 1), "A1")

    def test_26_0(self):
        self.assertEqual(get_key_from_col_row(27, 2), "AA2")

    def test_28_1(self):
        self.assertEqual(get_key_from_col_row(28, 1), "AB1")

    def test_0_0_inverse(self):
        self.assertEqual(get_col_row_from_key("A1"), (1, 1))

    def test_26_0_inverse(self):
        self.assertEqual(get_col_row_from_key("AA1"), (27, 1))

    def test_28_1_inverse(self):
        self.assertEqual(get_col_row_from_key("AB2"), (28, 2))

    def test_col_name_0(self):
        self.assertEqual(get_column_name(1), "A")

    def test_col_name_1(self):
        self.assertEqual(get_column_name(2), "B")

    def test_col_name_26(self):
        self.assertEqual(get_column_name(27), "AA")

    def test_col_name_28(self):
        self.assertEqual(get_column_name(28), "AB")


