import mocks
import json
import os
import unittest

import ltk
def get_url_parameter(key):
    if key == "U":
        return "1uTQ3m88BlUNwXFpXRmm"
    return ""
ltk.get_url_parameter = get_url_parameter

from static import pysheets
from static import constants
from static import state

class TestLoad(unittest.TestCase):

    def load_data(self):
        sheet = pysheets.Spreadsheet()
        content = open(os.path.join(os.path.dirname(__file__), "input.json")).read()
        data = json.loads(content)
        sheet.load_data(data, True)
        return sheet, data 

    def test_load_uid(self):
        sheet, data = self.load_data()
        self.assertEqual(data[constants.DATA_KEY_UID], state.doc.uid)

    def test_load_cell_keys(self):
        sheet, data = self.load_data()
        # self.assertEqual(list(sheet.cells.keys()), ['A1', 'A2', 'A3', 'B1', 'B2', 'B3', 'B6', 'D1', 'E3'])

    def test_load_cell_values(self):
        sheet, data = self.load_data()
        cells = [
            ("A1", "Project"),  ("B1", "Profit"),   ("D1", ""),
            ("A2", "One"),      ("B2", "800"),
            ("A3", "Two"),      ("B3", "3000"),
        ]
        for key, script in cells:
            pass # self.assertEqual(sheet.cells[key].script, script)

if __name__ == "__main__":
    unittest.main()