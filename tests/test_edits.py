import json
import unittest

import sys
sys.path.append("..")

from static.models import CellScriptChanged, CellStyleChanged, CellValueChanged
import static.history as history
import static.constants as constants


class TestCellValue(unittest.TestCase):

    def test_add(self):
        for n in range(105):
            history.add(CellValueChanged(f"A{n}", "before", "after"))
        self.assertEqual(len(history.history), 105)

    def test_style_changed(self):
        old_style = {"color": "red"}
        new_style = {"color": "blue", "font-size": "14px", "font-family": ""}
        edit = CellStyleChanged(f"A1", old_style, new_style)
        buffer = []
        edit.encode(buffer)
        actual = "".join(buffer)
        expected = '{"_":"d","key":"A1","style":{"color": "blue"}}'
        self.assertEquals(actual, expected)

    def test_script_changed(self):
        old_script = "=hello()"
        new_script = "=world()"
        edit = CellScriptChanged(f"A1", old_script, new_script)
        buffer = []
        edit.encode(buffer)
        actual = "".join(buffer)
        expected = '{"_":"c","key":"A1","script":"=world()"}'
        self.assertEquals(actual, expected)
