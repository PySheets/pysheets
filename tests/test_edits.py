"""
CopyRight (c) 2024 - Chris Laffra - All Rights Reserved.

This module contains unit tests for cell edits in the `models` module.
"""

import sys
import unittest

sys.path.append("..")

from tests import mocks # pylint: disable=wrong-import-position,unused-import
from static import models # pylint: disable=wrong-import-position
from static import history # pylint: disable=wrong-import-position


class TestCellValue(unittest.TestCase):
    """
    Tests the functionality of cell edits in the `models` module.
    """

    def test_add(self):
        """
        Tests the addition of CellValueChanged edits to the history.
        """
        for n in range(105):
            history.add(models.CellValueChanged(f"A{n}", "before", "after"))
        self.assertEqual(len(history.history), 105)

    def test_style_changed(self):
        """
        Tests the functionality of changing the style of a cell in the `models` module.
        
        This test verifies that the `CellStyleChanged` edit is correctly encoded when the style
        of a cell is changed correctly.
        """
        old_style = {"color": "red"}
        new_style = {"color": "blue", "font-size": "12px", "font-family": ""}
        edit = models.CellStyleChanged("A1", old_style, new_style)
        buffer = []
        edit.encode(buffer)
        actual = "".join(buffer)
        expected = '{"_":"d","key":"A1","style":{"color": "blue"}}'
        self.assertEqual(actual, expected)

    def test_script_changed(self):
        """
        Tests the functionality of changing the script of a cell in the `models` module.
        
        This test verifies that the `CellScriptChanged` edit is correctly encoded when the script
        of a cell is changed correctly.
        """
        old_script = "=hello()"
        new_script = "=world()"
        edit = models.CellScriptChanged("A1", old_script, new_script)
        buffer = []
        edit.encode(buffer)
        actual = "".join(buffer)
        expected = '{"_":"c","key":"A1","script":"=world()"}'
        self.assertEqual(actual, expected)
