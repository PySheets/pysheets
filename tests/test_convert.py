import mocks
import unittest

from static.pysheets import convert


class TestConvert(unittest.TestCase):

    def test_convert_float(self):
        self.assertEqual(convert("1.5"), 1.5)

    def test_convert_int(self):
        self.assertEqual(convert("5"), 5)

    def test_convert_string(self):
        self.assertEqual(convert("hello"), "hello")

    def test_convert_empty(self):
        self.assertEqual(convert(""), "")
