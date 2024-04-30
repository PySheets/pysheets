import mocks
import unittest

from static.pysheets import get_col_row_from_key, get_key_from_col_row


class TestKeys(unittest.TestCase):

    def test_0_0(self):
        self.assertEqual(get_key_from_col_row(0, 0), "A1")

    def test_26_0(self):
        self.assertEqual(get_key_from_col_row(26, 0), "AA1")

    def test_28_1(self):
        self.assertEqual(get_key_from_col_row(28, 1), "AC2")

