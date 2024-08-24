"""
CopyRight (c) 2024 - Chris Laffra - All Rights Reserved.

This module contains unit tests for the `history.add()` function, which is
used to add edits to the undo-history.
"""


import sys
import unittest

sys.path.append("..")

from tests import mocks # pylint: disable=wrong-import-position,unused-import
from static import constants # pylint: disable=wrong-import-position,unused-import
from static import models # pylint: disable=wrong-import-position,unused-import
from static import history # pylint: disable=wrong-import-position,unused-import
from static import state # pylint: disable=wrong-import-position,unused-import
from static import timeline # pylint: disable=wrong-import-position,unused-import

class TestHistoryAdd(unittest.TestCase):
    """
    This class contains unit tests for the `history.add()` function, which is used to add edits to the undo-history.
    """

    def setUp(self):
        history.history.clear()
        history.flush = unittest.mock.MagicMock()

    def test_add_single_edit(self):
        """
        Add one edit and see if it gets recorded correctly.
        """
        history.add(models.CellValueChanged("A1", "old", "new"))
        self.assertEqual(len(history.history), 1)
        self.assertIsInstance(history.history[0], models.CellValueChanged)

    def test_undo_cell_value(self):
        """
        Tests undo of one edit.
        """
        sheet = models.Sheet()
        cell = sheet.get_cell("A1")
        edit = models.CellValueChanged("A1", "old", "new")
        edit.apply(sheet)
        self.assertEqual(cell.value, "new")
        history.add(edit)
        self.assertEqual(len(history.history), 1)
        history.undo(sheet)
        self.assertEqual(cell.value, "old")
        self.assertEqual(len(history.history), 0)

    def test_undo_row_height(self):
        """
        Tests undo of row height change.
        """
        sheet = models.Sheet()
        edit = models.RowChanged(7, 136)
        edit.apply(sheet)
        self.assertEqual(sheet.rows['7'], 136)
        history.add(edit)
        self.assertEqual(len(history.history), 1)
        history.undo(sheet)
        self.assertEqual(sheet.rows['7'], constants.DEFAULT_ROW_HEIGHT)
        self.assertEqual(len(history.history), 0)

    def test_undo_column_width(self):
        """
        Tests undo of column width change.
        """
        sheet = models.Sheet()
        edit = models.ColumnChanged(5, 256)
        edit.apply(sheet)
        self.assertEqual(sheet.columns['5'], 256)
        history.add(edit)
        self.assertEqual(len(history.history), 1)
        history.undo(sheet)
        self.assertEqual(sheet.columns['5'], constants.DEFAULT_COLUMN_WIDTH)
        self.assertEqual(len(history.history), 0)

    def test_undo_style(self):
        """
        Tests undo of cell style change.
        """
        sheet = models.Sheet()
        cell = sheet.get_cell("A1")
        cell.style = {"color": "green"}
        edit = models.CellStyleChanged("A1", cell.style, {"color": "red"})
        edit.apply(sheet)
        self.assertEqual(cell.style["color"], "red")
        history.add(edit)
        self.assertEqual(len(history.history), 1)
        history.undo(sheet)
        self.assertEqual(cell.style["color"], "green")
        self.assertEqual(len(history.history), 0)

    def test_undo_preview_resize(self):
        """
        Tests undo of preview resize.
        """
        sheet = models.Sheet()
        edit = models.PreviewDimensionChanged("A1", 50, 50, 100, 100)
        edit.apply(sheet)
        preview = sheet.previews["A1"]
        self.assertEqual(preview.width, 100)
        self.assertEqual(preview.height, 100)
        history.add(edit)
        self.assertEqual(len(history.history), 1)
        history.undo(sheet)
        self.assertEqual(preview.width, 50)
        self.assertEqual(preview.height, 50)
        self.assertEqual(len(history.history), 0)

    def test_add_multiple_edits(self):
        """
        Add two edits and see if they get recorded correctly.
        """
        edit1 = models.CellValueChanged("A1", "old1", "new1")
        edit2 = models.CellValueChanged("A2", "old2", "new2")
        history.add(edit1)
        history.add(edit2)
        self.assertEqual(len(history.history), 2)

    def test_add_edit_group(self):
        """
        This test verifies that when a group of edits is added to the undo history using
        the `history.SingleEdit` context manager, the entire group is recorded as a 
        single entry in the history.
        """
        with history.SingleEdit("test 1 edit"):
            history.add(models.CellValueChanged("A1", "old", "new"))
            history.add(models.CellValueChanged("A2", "old", "new"))
            history.add(models.CellValueChanged("A3", "old", "new"))
        self.assertEqual(len(history.history), 1)
        self.assertEqual(len(history.history[0].edits), 3)

    @unittest.mock.patch('static.history.schedule_flush')
    def test_schedule_flush_called(self, mock_schedule_flush):
        """
        Verifies that the `schedule_flush` function is called when an edit is added to the history.
        """
        edit = models.CellValueChanged("A1", "old", "new")
        history.add(edit)
        mock_schedule_flush.assert_called_once()
