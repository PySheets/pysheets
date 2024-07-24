import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))


import unittest
import unittest.mock
import mocks
from static import api

class TestLastExpression(unittest.TestCase):

    def test_intercept_empty(self):
        script = ''
        actual = api.intercept_last_expression(script)
        expected = ''
        self.assertEquals(actual, expected)

    def test_intercept_multiline_dict(self):
        script = "x = {\n    'y':\n     4,\n }"
        actual = api.intercept_last_expression(script)
        expected = "_ = " + script
        self.assertEquals(actual, expected)

    def test_intercept_multiline_call(self):
        script = "print(\n1,\n2,\n3\n)\nprint(\n4,\n3,\n4\n)"
        actual = api.intercept_last_expression(script)
        expected = "print(\n1,\n2,\n3\n)\n_ = print(\n4,\n3,\n4\n)"
        self.assertEquals(actual, expected)

    def test_intercept_multiline(self):
        script = "x = 1\ny = 2\nz = 3"
        actual = api.intercept_last_expression(script)
        expected = "x = 1\ny = 2\n_ = z = 3"
        self.assertEquals(actual, expected)
