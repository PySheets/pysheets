import mocks
import unittest
from unittest.mock import MagicMock

from static.pysheets import Cell, Spreadsheet


class TestCellValue(unittest.TestCase):

    def test_sheel_cells(self):
        sheet = Spreadsheet()
        cell = sheet.get("B2")
        self.assertEqual(sheet.cells, { "B2": cell })

    def test_cell(self):
        sheet = Spreadsheet()
        cell = sheet.get("B2")
        self.assertEqual(cell.tag, "td")
        self.assertEqual(cell.classes, ["ltk-td"])
        self.assertEqual(cell.column, 1)
        self.assertEqual(cell.running, False)
        self.assertEqual(cell.sheet, sheet)
        self.assertEqual(cell.row, 1)
        self.assertEqual(cell.key, "B2")
        cell.set("=10*10", "hundred")
        self.assertEqual(cell.inputs, set())
        self.assertEqual(cell.script, "=10*10")
        self.assertEqual(cell.preview, None)

    def test_cell_update(self):
        sheet = Spreadsheet()
        cell = sheet.get("B2")
        cell.set("=20 + 30", "fifty")
        cell.update(3.14, 60, "sixty")
        self.assertEqual(sheet.cache, { "B2": 60 })
        self.assertEqual(cell.preview, "sixty")

    def test_cell_evaluate(self):
        sheet = Spreadsheet()
        cell = sheet.get("B2")
        cell.set("=20 + 30", "fifty")
        cell.evaluate()
        self.assertEqual(cell.script, "=20 + 30")
        self.assertEqual(sheet.cache, { "B2": 50 })
        self.assertEqual(cell.preview, None)

    def test_cell_set(self):
        sheet = Spreadsheet()
        cell = sheet.get("B2")
        cell.set( "", "")
        cell.set("=100 / 5", "twenty")
        self.assertEqual(sheet.cache, { "B2": 20 })
        self.assertEqual(cell.preview, None)

    def test_cell_text(self):
        sheet = Spreadsheet()
        cell = sheet.get("B2")
        cell.set( "", "")
        cell.text = MagicMock()
        cell.set("=10*100", "thousand")
        cell.text.assert_called_with("1000")

    def test_edited(self):
        sheet = Spreadsheet()
        A1 = sheet.get("A1")
        A1.edited("50")
        self.assertEqual(sheet.cache, {'A1': 50})

    def test_dag(self):
        sheet = Spreadsheet()
        A1 = sheet.get("A1")
        A1.set( "50", "")
        self.assertEqual(sheet.cache, {'A1': 50})
        B1 = sheet.get("B1")
        B1.set( "50", "")
        self.assertEqual(sheet.cache["B1"], 50)
        C1 = sheet.get("C1")
        C1.set( "=A1+B1", "")
        self.assertEqual(sheet.cache["C1"], 100)
        C2 = sheet.get("C2")
        C2.set( "=C1*2", "")
        self.assertEqual(sheet.cache["C2"], 200)
        A1.set("150")
        self.assertEqual(sheet.cache["A1"], 150)
        self.assertEqual(sheet.cache["B1"], 50)
        self.assertEqual(C1.script, "=A1+B1")
        self.assertEqual(sheet.cache["C1"], 200)
        self.assertEqual(C2.script, "=C1*2")
        self.assertEqual(sheet.cache["C2"], 400)

if __name__ == "__main__":
    unittest.main()