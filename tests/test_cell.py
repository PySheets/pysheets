import mocks
import unittest
from unittest.mock import MagicMock

import sys
sys.path.append("..")

from static.pysheets import SpreadsheetView
from static.models import Sheet, Cell


class TestCellValue(unittest.TestCase):

    def test_cell(self):
        model = Sheet(uid="abc123")
        sheet = SpreadsheetView(model)
        cell = sheet.get_cell("B2")
        self.assertEqual(cell.tag, "div")
        self.assertEqual(cell.classes, [])
        self.assertEqual(cell.model.column, 2)
        self.assertEqual(cell.running, False)
        self.assertEqual(cell.sheet, sheet)
        self.assertEqual(cell.model.row, 2)
        self.assertEqual(cell.model.key, "B2")
        cell.set("=10*10")
        self.assertEqual(cell.inputs, set())
        self.assertEqual(cell.model.script, "=10*10")

    def test_cell_update(self):
        sheet = SpreadsheetView(Sheet())
        cell = sheet.get_cell("B2")
        cell.set("=20 + 30")
        cell.evaluate_locally("_=60")

    def test_cell_evaluate(self):
        sheet = SpreadsheetView(Sheet())
        cell = sheet.get_cell("B2")
        cell.set("=20 + 30")
        cell.evaluate()
        self.assertEqual(cell.model.script, "=20 + 30")

    def test_cell_set(self):
        sheet = SpreadsheetView(Sheet())
        cell = sheet.get_cell("B2")
        cell.set("")
        cell.set("=100 / 5")

    def test_cell_text(self):
        sheet = SpreadsheetView(Sheet())
        cell = sheet.get_cell("B2")
        cell.set("")
        cell.text = MagicMock()
        cell.set("=10*100")
        cell.text.assert_called_with("1000")

Sheet(
    uid="",
    name="Pandas-13",
    columns={1: 35, 2: 35, 3: 107},
    rows={},
    cells={
        "A1": Cell(
            key="A1",
            column=1,
            row=1,
            value="1",
            script="1",
            embed=False,
            style={"background-color": "#faebeb", "text-align": "center"},
        ),
        "A2": Cell(
            key="A2",
            column=1,
            row=2,
            value="2",
            script="2",
            embed=False,
            style={"background-color": "#faebeb", "text-align": "center"},
        ),
        "A3": Cell(
            key="A3",
            column=1,
            row=3,
            value="3",
            script="3",
            embed=False,
            style={"background-color": "#faebeb", "text-align": "center"},
        ),
        "B1": Cell(
            key="B1",
            column=2,
            row=1,
            value="4",
            script="4",
            embed=False,
            style={"background-color": "#faebeb", "text-align": "center"},
        ),
        "B2": Cell(
            key="B2",
            column=2,
            row=2,
            value="11",
            script="11",
            embed=False,
            style={"background-color": "#faebeb", "text-align": "center"},
        ),
        "B3": Cell(
            key="B3",
            column=2,
            row=3,
            value="6",
            script="6",
            embed=False,
            style={"background-color": "#faebeb", "text-align": "center"},
        ),
        "D3": Cell(
            key="D3",
            column=4,
            row=3,
            value="DataFrame",
            script="=\nimport pandas as pd\nimport numpy as np\n\ndf = pd.DataFrame(\n    np.array(([A1, A2, A3], [B1, B2, B3])),\n    index=['mouse', 'rabbit'],\n    columns=['one', 'two', 'three']\n)\ndf",
            embed="",
            style={"background-color": "#d1e3ff"},
        ),
        "F3": Cell(
            key="F3",
            column=6,
            row=3,
            value="",
            script="",
            embed=False,
            style={"background-color": "#e0ffea"},
        ),
        "C12": Cell(
            key="C12",
            column=3,
            row=12,
            value="Figure",
            script="=\n\nprompt = \"\"\"\nVisualize a dataframe as a matplotlib figure in the code and call it \"figure\".\nI already have it stored in a variable called \"D3\".\nHere are the column names for the dataframe:\n['one' 'two' 'three']\n\"\"\"\n\n# The following code is entirely AI-generated. Please check it for errors.\n\nimport matplotlib.pyplot as plt\n\n# Create figure and axes\nfigure = plt.figure()\nax = figure.add_subplot(111)\n\n# Plot dataframe columns as lines\nax.plot(D3['one'], label='one')\nax.plot(D3['two'], label='two')\nax.plot(D3['three'], label='three')\n\n# Add legend and labels\nax.legend()\nax.set_xlabel('x-axis')\nax.set_ylabel('y-axis')\nax.set_title('Dataframe Visualization')\n\n# Show figure\nfigure",
            embed=False,
            style={},
        ),
    },
    selected="K4",
    screenshot="/screenshot.png",
    created_timestamp=0,
    updated_timestamp=1719179840.684,
    column_count=26,
    row_count=50,
)
