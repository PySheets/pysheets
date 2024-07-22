import json
import unittest
import sys
sys.path.append("static")
sys.path.append("..")

import static.history as history
import static.models as models
import static.pysheets as pysheets


class Animal(models.Model):
    def __init__(self, count=0, kind="", _class="Animal"):
        super().__init__()
        self.count = count
        self.kind = kind

    def encode_fields(self, buffer:list):
        buffer.append(f'"_class":"Animal",')
        buffer.append(f'"count":{json.dumps(self.count)},')
        buffer.append(f'"kind":{json.dumps(self.kind)}')

models.A = Animal
models.SHORT_CLASS_NAMES["Animal"] = "A"

class TestModel(unittest.TestCase):

    def setUp(self) -> None:
        self.model1 = Animal(count=2, kind="dog")
        self.encoding = models.encode(self.model1)
        self.model2 = models.decode(self.encoding, globals())

    def test_class1(self):
        self.assertEquals(self.model1.__class__, Animal)

    def test_class2(self):
        self.assertEquals(self.model2.__class__, Animal)

    def test_count(self):
        self.assertEquals(self.model2.count, 2)

    def test_kind(self):
        self.assertEquals(self.model2.kind, "dog")

    def test_equal(self):
        self.assertEquals(self.model1, self.model2)


class TestCell(unittest.TestCase):

    def setUp(self) -> None:
        self.cell1 = models.Cell()
        self.cell1.column = 1
        self.cell1.row = 12
        self.cell1.key = "A12"
        self.cell1.value = 32

        self.encoding = models.encode(self.cell1)
        self.cell2 = models.decode(self.encoding)

        self.cell3 = models.Cell(column=1, row=12, key="A12", value=32)

    def test_class1(self):
        self.assertEquals(self.cell1.__class__, models.Cell)

    def test_class2(self):
        self.assertEquals(self.cell2.__class__, models.Cell)

    def test_class3(self):
        self.assertEquals(self.cell1.key, "A12")
        self.assertEquals(self.cell3.key, "A12")

    def test_column(self):
        self.assertEquals(self.cell2.column, 1)

    def test_row(self):
        self.assertEquals(self.cell2.row, 12)

    def test_key(self):
        self.assertEquals(self.cell2.key, "A12")

    def test_value(self):
        self.assertEquals(self.cell2.value, '32')

    def test_listener(self):
        cell = models.Cell(column=1, row=12, key="A12", value=32)
        self.assertEquals(cell.value, 32)
        self.assertEquals(cell.row, 12)

        callback = unittest.mock.Mock()
        cell.listen(callback)

        cell.value = 42
        self.assertEquals(cell.value, 42)
        callback.assert_called_once()

        cell.row = 2
        self.assertEquals(cell.row, 2)
        callback.assert_called()
        self.assertEqual(callback.call_count, 2)



class TestSheet(unittest.TestCase):

    def setUp(self) -> None:
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

    def test_class1(self):
        self.assertEquals(self.sheet1.__class__, models.Sheet)

    def test_class2(self):
        self.assertEquals(self.sheet2.__class__, models.Sheet)

    def test_uid(self):
        self.assertEquals(self.sheet2.uid, "abc123")

    def test_cells(self):
        self.maxDiff = None
        for key, cell in self.sheet1.cells.items():
            self.assertIn(key, self.sheet2.cells)

    def test_cell(self):
        cell = self.sheet1.cells["C4"]
        self.assertEquals(cell.column, 3)
        self.assertEquals(cell.row, 4)
        self.assertEquals(cell.key, "C4")
        self.assertEquals(cell.value, 4)
        self.assertEquals(cell, models.Cell(column=3, row=4, key="C4", value=4))

    def test_equal(self):
        self.assertEquals(self.sheet1, self.sheet2)


class TestEdits(unittest.TestCase):

    def test_selection_changed(self):
        sheet = models.Sheet()
        change = models.SelectionChanged(key="A1")
        change.apply(sheet)
        self.assertEquals(sheet.selected, "A1")

    def test_script_changed(self):
        sheet = models.Sheet()
        change = models.CellScriptChanged("A1", "Hello", "World")
        change.apply(sheet)
        self.assertIn("A1", sheet.cells)
        cell = sheet.cells["A1"]
        self.assertEquals(cell.script, "World")

    def test_script_undo(self):
        sheet = models.Sheet()
        change1 = models.CellScriptChanged("A1", "Hello", "World")
        change1.apply(sheet)
        a1 = sheet.cells["A1"]
        self.assertEquals(a1.script, "World")
        change2 = models.CellScriptChanged("A1", "World", "!")
        change2.apply(sheet)
        self.assertEquals(a1.script, "!")
        change2.undo(sheet)
        self.assertEquals(a1.script, "World")
        change1.undo(sheet)
        self.assertEquals(a1.script, "Hello")

    def test_history(self):
        sheet = models.Sheet()
        change1 = models.CellScriptChanged("A1", "Hello", "World")
        change1.apply(sheet)
        a1 = sheet.cells["A1"]
        self.assertEquals(a1.script, "World")
        history.add(change1)

        change2 = models.CellScriptChanged("A1", "World", "!")
        change2.apply(sheet)
        self.assertEquals(a1.script, "!")
        history.add(change2)

        history.undo(sheet)
        self.assertEquals(a1.script, "World")
        history.undo(sheet)
        self.assertEquals(a1.script, "Hello")

    def test_notification(self):
        model = models.Cell(key="A1", script="1")
        sheet = pysheets.SpreadsheetView(models.Sheet())
        view = pysheets.CellView(sheet, "A1", model)
        view.setup_listener()
        self.assertIn(view.model_changed, model._listeners)

        view.model_changed = unittest.mock.Mock()
        model._listeners = [ view.model_changed]
        model.script = "2"
        view.model_changed.assert_called()
        for call_args in view.model_changed.call_args_list:
            cell, info = call_args[0]
            self.assertIn(info["name"], ["value", "script"])
            self.assertEquals(cell, model)
