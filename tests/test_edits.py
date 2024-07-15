import json
import unittest

import sys
sys.path.append("..")

from static.models import CellValueChanged
import static.history as history
import static.constants as constants


class TestCellValue(unittest.TestCase):

    def test_add(self):
        for n in range(105):
            history.add(CellValueChanged(f"A{n}", "before", "after"))
        self.assertEqual(len(history.edits), 105)

    def test_receive(self):
        handle_edits = unittest.mock.Mock()
        edit1 = CellValueChanged(f"A1", "before", "after")
        edit2 = CellValueChanged(f"A2", "before", "after")
        edit3 = CellValueChanged(f"A3", "before", "after")
        encoded_edits = json.dumps([edit1, edit2, edit3])
        history.handle_edits(handle_edits, {
            constants.DATA_KEY_EDITS: encoded_edits,
        })
        handle_edits.assert_called_with(encoded_edits)

    def test_sync(self):
        handle_edits = unittest.mock.Mock()
        history.edits = []
        edit1 = CellValueChanged(f"A1", "before", "after")
        history.add(edit1)
        edit4 = CellValueChanged(f"A4", "before", "after")
        edit5 = CellValueChanged(f"A5", "before", "after")
        history.handle_edits(handle_edits, {
            constants.DATA_KEY_EDITS: json.dumps([edit4, edit5]),
        })
        handle_edits.assert_called_with(json.dumps([edit4, edit5]))

