import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))


import unittest
import unittest.mock
import mocks
from static import api
from static import constants
import ltk


class TestInputs(unittest.TestCase):
    def check(self, script, expected):
        actual = sorted(api.find_inputs(script))
        self.assertEquals(actual, expected)

    def test_syntax_error(self):
        self.check("this causes a syntax error", [])

    def test_add(self):
        self.check("C1+C2", ["C1", "C2"])

    def test_function_call(self):
        self.check("print(C1, 'Hello', C2, 'World')", ["C1", "C2"])

    def test_reference(self):
        self.check("x = C2", ["C2"])

    def test_ignore_string(self):
        self.check("x, y = 'C1', C2", ["C2"])

    def test_statements_1(self):
        self.check("x = 10\ny = C2", ["C2"])

    def test_statements_2(self):
        self.check("y = C2; x = 10", ["C2"])

    def test_assignment(self):
        self.check("C1 = 0\nx = C2\nC3 = 1", ["C2"])

    def test_function_range(self):
        self.check("print('C1:C2')", ["C1", "C2"])

    def mock_worker(self):
        from static import worker
        import json

        # mock polyscript subscribe
        def handle_worker_request(data):
            worker.handle_request("Worker", constants.TOPIC_WORKER_FIND_INPUTS, json.dumps(data))
        ltk.subscribe("Worker", constants.TOPIC_WORKER_FIND_INPUTS, handle_worker_request)

        # mock polyscript publish
        worker.publish = ltk.publish

    def check_worker(self, key, script, expected):
        self.mock_worker()
        handle_inputs = unittest.mock.Mock()
        ltk.subscribe(
            "Test",
            constants.TOPIC_WORKER_INPUTS,
            handle_inputs
        )
        ltk.publish(
            "Test",
            "Worker",
            constants.TOPIC_WORKER_FIND_INPUTS,
            {
                "key": key,
                "script": script,
            },
        )
        data = json.loads(handle_inputs.call_args[0][0])
        self.assertEquals(data["key"], key)
        self.assertEquals(sorted(data["inputs"]), sorted(expected))
        
    def test_worker_simple(self):
        self.check_worker("A1", "C1+C2", ["C1", "C2"])
        
    def test_worker_range(self):
        self.check_worker("A1", "print('AA1:AB4')", ["AB3", "AB1", "AA4", "AA3", "AA1", "AA2", "AB2", "AB4"])

