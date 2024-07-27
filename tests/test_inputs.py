"""
CopyRight (c) 2024 - Chris Laffra - All Rights Reserved.

This module contains unit tests for the `api.find_inputs()` function, which is
used to extract input variables from a given script.
"""

import json
import sys
import unittest
import unittest.mock

import ltk

sys.path.append("..")

from tests import mocks # pylint: disable=wrong-import-position,unused-import
from static import api # pylint: disable=wrong-import-position
from static import constants # pylint: disable=wrong-import-position
from static import worker # pylint: disable=wrong-import-position


class TestInputs(unittest.TestCase):
    """
    This class contains unit tests for the `api.find_inputs()` function, which is used
    to extract input variables from a given script. The tests cover various scenarios,
    including syntax errors, arithmetic operations, function calls, variable references,
    string handling, and multiple statements. The class also includes tests for the worker
    functionality, which mocks the polyscript subscribe and publish operations.
    """

    def check(self, script, expected):
        """
        Helper function for testing the `api.find_inputs()` function.
        """
        actual = sorted(api.find_inputs(script))
        self.assertEqual(set(actual), set(expected))

    def test_reference(self):
        """
        Simple expression containing a cell reference.
        """
        self.check("C2", ["C2"])

    def test_assignment(self):
        """
        Simple assignment with a cell reference as the right-hand side.
        """
        self.check("x = C2", ["C2"])

    def test_syntax_error(self):
        """
        Syntactically incorrect scripts have no inputs.
        """
        self.check("this causes a syntax error", [])

    def test_add(self):
        """
        Expression with an arithmetic operation containing two cell references.
        """
        self.check("C1+C2", ["C1", "C2"])

    def test_function_call(self):
        """
        Function call with a cell reference as an argument.
        """
        self.check("print(C1, 'Hello', C2, 'World')", ["C1", "C2"])

    def test_ignore_string(self):
        """
        Ignore cell references inside of strings.
        """
        self.check("x, y = 'C1', C2", ["C2"])

    def test_statements_1(self):
        """
        Multiple statements with a cell references in the first statement.
        """
        self.check("y = C2; x = 10", ["C2"])

    def test_statements_2(self):
        """
        Multiple statements with a cell references in the second statement.
        """
        self.check("x = 10\ny = C2", ["C2"])

    def test_assignment_to_cell_reference(self):
        """
        Ignore assignment to a cell reference.
        """
        self.check("C1 = 0\nx = C2\nC3 = 1", ["C2"])

    def test_function_range(self):
        """
        Detect cell reference ranges.
        """
        self.check("print('C1:C2')", ["C1", "C2"])

    def test_function_range_aa(self):
        """
        Detect cell reference ranges in the AA column.
        """
        self.check("print('AA1:AB4')", ["AB3", "AB1", "AA4", "AA3", "AA1", "AA2", "AB2", "AB4"])

    def mock_worker(self):
        """
        Mocks the worker functionality by subscribing to the 'Worker' topic for the
        'TOPIC_WORKER_FIND_INPUTS' event, and publishing to the 'Worker' topic when
        a request is received. This allows testing the worker functionality without
        actually running the worker as a web worker.
        """

        # mock polyscript subscribe
        def handle_worker_request(data):
            worker.handle_request("Worker", constants.TOPIC_WORKER_FIND_INPUTS, json.dumps(data))
        ltk.subscribe("Worker", constants.TOPIC_WORKER_FIND_INPUTS, handle_worker_request)

        # mock polyscript publish
        worker.publish = ltk.publish

    def check_worker(self, key, script, expected):
        """
        Checks the worker functionality by mocking the worker's behavior and verifying
        that the expected cell references are detected in the provided script.
        """
        self.mock_worker()
        handle_inputs = unittest.mock.Mock()

        # receive responses from the worker
        ltk.subscribe(
            "Worker",
            constants.TOPIC_WORKER_INPUTS,
            handle_inputs
        )

        # send a request to the worker
        ltk.publish(
            "Test",
            "Worker",
            constants.TOPIC_WORKER_FIND_INPUTS,
            {
                "key": key,
                "script": script,
            },
        )

        # verify the result
        handle_inputs.assert_called_once()
        data = json.loads(handle_inputs.call_args[0][0])
        self.assertEqual(data["key"], key)
        self.assertEqual(sorted(data["inputs"]), sorted(expected))

    @unittest.skip("Skipping worker tests as pubsub has changed")
    def test_worker_simple(self):
        """
        Checks the worker functionality by mocking the worker's behavior and verifying
        that the expected cell references are detected in the provided script.
        """
        self.check_worker("A1", "C1+C2", ["C1", "C2"])

    @unittest.skip("Skipping worker tests as pubsub has changed")
    def test_worker_range(self):
        """
        Checks the worker functionality by mocking the worker's behavior and verifying
        that the expected cell references are detected in the provided script.
        """
        self.check_worker("A1", "print('AA1:AB4')", ["AB3", "AB1", "AA4", "AA3", "AA1", "AA2", "AB2", "AB4"])
