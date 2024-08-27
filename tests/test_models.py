"""
CopyRight (c) 2024 - Chris Laffra - All Rights Reserved.

This module contains unit tests for the `models` module, which defines the data models used in the application.
"""

import json
import sys
import unittest
import unittest.mock

sys.path.append("..")

from tests import mocks # pylint: disable=wrong-import-position,unused-import
from static import history # pylint: disable=wrong-import-position
from static import models # pylint: disable=wrong-import-position


class Animal(models.Model):
    """
    Represents an Animal data model with a count and kind property.
    """
    def __init__(self, count=0, kind="", _class="Animal"):
        super().__init__()
        self.count = count
        self.kind = kind

    def encode_fields(self, buffer:list):
        buffer.append('"_class":"Animal",')
        buffer.append(f'"count":{json.dumps(self.count)},')
        buffer.append(f'"kind":{json.dumps(self.kind)}')


# create an Animal and let the `models` module know it exists
models.A = Animal
models.SHORT_CLASS_NAMES["Animal"] = "A"


class TestAnimal(unittest.TestCase):
    """
    Tests the `Animal` data model.
    """

    def setUp(self) -> None:
        """
        Creates an `Animal` instance and a marshalled/unmarshalled version of it.
        """
        self.model1 = Animal(count=2, kind="dog")
        self.encoding = models.encode(self.model1)
        self.model2 = models.decode(self.encoding)

    def test_class(self):
        """
        Tests that the `Animal` class is correctly instantiated and decoded.
        """
        self.assertEqual(self.model1.__class__, Animal)
        self.assertEqual(self.model2.__class__, Animal)

    def test_count(self):
        """
        Tests that the `count` property of the `Animal` model is correctly decoded.
        """
        self.assertEqual(self.model2.count, 2)

    def test_kind(self):
        """
        Tests that the `kind` property of the `Animal` model is correctly decoded.
        """
        self.assertEqual(self.model2.kind, "dog")

    def test_equal(self):
        """
        Tests that the original and decoded versions of the `Animal` model are equal.
        """
        self.assertEqual(self.model1, self.model2)


class TestCell(unittest.TestCase):
    """
    Tests the `models.Cell` data model.
    """

    def setUp(self) -> None:
        """
        Sets up test data for the `Cell` data model.
        
        Creates a `Cell` instance, a marshalled/unmarshalled version of it, and one created user a constructor.
        """
        self.cell1 = models.Cell()
        self.cell1.column = 1
        self.cell1.row = 12
        self.cell1.key = "A12"
        self.cell1.value = 32

        self.encoding = models.encode(self.cell1)
        self.cell2 = models.decode(self.encoding)

        self.cell3 = models.Cell(column=1, row=12, key="A12", value=32)

    def test_class(self):
        """
        Tests that the `Cell` class is correctly instantiated and decoded.
        """
        self.assertEqual(self.cell1.__class__, models.Cell)
        self.assertEqual(self.cell2.__class__, models.Cell)
        self.assertEqual(self.cell3.__class__, models.Cell)

    def test_class_key(self):
        """
        Tests that the `key` property of the `Cell` class is correctly decoded.
        """
        self.assertEqual(self.cell1.key, "A12")
        self.assertEqual(self.cell2.key, "A12")
        self.assertEqual(self.cell3.key, "A12")

    def test_column(self):
        """
        Tests that the `column` property of the `Cell` class is correctly decoded.
        """
        self.assertEqual(self.cell1.column, 1)
        self.assertEqual(self.cell2.column, 1)
        self.assertEqual(self.cell3.column, 1)

    def test_row(self):
        """
        Tests that the `row` property of the `Cell` class is correctly decoded.
        """
        self.assertEqual(self.cell1.row, 12)
        self.assertEqual(self.cell2.row, 12)
        self.assertEqual(self.cell3.row, 12)

    def test_key(self):
        """
        Tests that the `key` property of the `Cell` class is correctly decoded.
        """
        self.assertEqual(self.cell1.key, "A12")
        self.assertEqual(self.cell2.key, "A12")
        self.assertEqual(self.cell3.key, "A12")

    def test_value(self):
        """
        Tests that the `value` property of the `Cell` class is correctly decoded.
        """
        self.assertEqual(self.cell1.value, 32)
        self.assertEqual(self.cell2.value, 32)
        self.assertEqual(self.cell3.value, 32)

    def test_listener(self):
        """
        Tests the listener functionality of the `Cell` class.

        This test verifies that the `Cell` class correctly notifies a registered listener
        when the `value` or `row` properties are updated. It creates a `Cell` instance,
        registers a mock callback, and then updates the `value` and `row` properties to
        ensure the callback is called as expected.
        """
        cell = models.Cell(column=1, row=12, key="A12", value=32)
        self.assertEqual(cell.value, 32)
        self.assertEqual(cell.row, 12)

        callback = unittest.mock.Mock()
        cell.listen(callback)

        cell.value = 42
        self.assertEqual(cell.value, 42)
        callback.assert_called_once()

        cell.row = 2
        self.assertEqual(cell.row, 2)
        callback.assert_called()
        self.assertEqual(callback.call_count, 2)



class TestSheet(unittest.TestCase):
    """
    Tests the `models.Sheet` class.
    """

    def setUp(self) -> None:
        """
        Initialize the necessary data for running tests on the Sheet and Cell classes.
        """
        self.cells = {
            "A1": models.Cell(column=1, row=1, key="A1", value=1),
            "C4": models.Cell(column=3, row=4, key="C4", value=4),
            "AB24": models.Cell(column=28, row=24, key="AB24", value="Hello"),
        }
        self.columns = {
            1: 92,
            26: 13,
        }
        self.rows = {
            4: 112,
            24: 19,
        }

        self.sheet1 = models.Sheet()
        self.sheet1.uid = "abc123"
        self.sheet1.name = "Sample Sheet"
        self.sheet1.selected = "A1"
        self.sheet1.screenshot = "urlencodedsnapshot"
        self.sheet1.cells = self.cells
        self.sheet1.rows = self.rows
        self.sheet1.columns = self.columns

        self.encoding = models.encode(self.sheet1)
        self.sheet2 = models.decode(self.encoding)

    def test_class(self):
        """
        Tests that the `Sheet` class is correctly instantiated and decoded.
        """
        self.assertEqual(self.sheet1.__class__, models.Sheet)
        self.assertEqual(self.sheet2.__class__, models.Sheet)

    def test_uid(self):
        """
        Tests that the `uid` field is correctly instantiated and decoded.
        """
        self.assertEqual(self.sheet1.uid, "abc123")
        self.assertEqual(self.sheet2.uid, "abc123")

    def test_cells(self):
        """
        Tests that all cells are correctly decoded.
        """
        for key in self.sheet1.cells:
            self.assertIn(key, self.sheet2.cells)

    def test_cell(self):
        """
        Tests that a given cell is correctly decoded.
        """
        cell = self.sheet2.cells["C4"]
        self.assertEqual(cell.column, 3)
        self.assertEqual(cell.row, 4)
        self.assertEqual(cell.key, "C4")
        self.assertEqual(cell.script, 4)
        self.assertEqual(cell, models.Cell(column=3, row=4, key="C4", script=4))

    def test_equal(self):
        """
        Tests that original and clone are equal.
        """
        self.assertEqual(self.sheet1, self.sheet2)


class TestEdits(unittest.TestCase):
    """
    Tests the functionality of the `Sheet` class and its associated `Cell` and `Change` classes.
    """

    def test_selection_changed(self):
        """
        Tests that the `SelectionChanged` class correctly applies changes to a `Sheet` instance.
        """
        sheet = models.Sheet()
        change = models.SelectionChanged(key="A1")
        change.apply(sheet)
        self.assertEqual(sheet.selected, "A1")

    def test_script_changed(self):
        """
        Tests that the `CellScriptChanged` class correctly applies changes to a cell in a `Sheet` instance.
        """
        sheet = models.Sheet()
        change = models.CellScriptChanged("A1", "Hello", "World")
        change.apply(sheet)
        self.assertIn("A1", sheet.cells)
        cell = sheet.cells["A1"]
        self.assertEqual(cell.script, "World")

    def test_script_undo(self):
        """
        Tests the undo functionality of the `CellScriptChanged` class, which is responsible
        for applying changes to the script of a cell in a `Sheet` instance.
        """
        sheet = models.Sheet()
        change1 = models.CellScriptChanged("A1", "Hello", "World")
        change1.apply(sheet)
        a1 = sheet.cells["A1"]
        self.assertEqual(a1.script, "World")
        change2 = models.CellScriptChanged("A1", "World", "!")
        change2.apply(sheet)
        self.assertEqual(a1.script, "!")
        change2.undo(sheet)
        self.assertEqual(a1.script, "World")
        change1.undo(sheet)
        self.assertEqual(a1.script, "Hello")

    def test_history(self):
        """
        Tests the functionality of the `history` module, which is responsible for managing
        the history of changes made to a `Sheet` instance.
        """
        sheet = models.Sheet()
        change1 = models.CellScriptChanged("A1", "Hello", "World")
        change1.apply(sheet)
        a1 = sheet.cells["A1"]
        self.assertEqual(a1.script, "World")
        history.add(change1)

        change2 = models.CellScriptChanged("A1", "World", "!")
        change2.apply(sheet)
        self.assertEqual(a1.script, "!")
        history.add(change2)

        history.undo(sheet)
        self.assertEqual(a1.script, "World")
        history.undo(sheet)
        self.assertEqual(a1.script, "Hello")
