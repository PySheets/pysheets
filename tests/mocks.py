"""
CopyRight (c) 2024 - Chris Laffra - All Rights Reserved.

This module provides a set of mocks and utility functions for testing purposes.
"""

import sys
import time
import os

sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "static"))

import ltk      # pylint: disable=wrong-import-position
import state    # pylint: disable=wrong-import-position



def schedule(function, key, duration=None): # pylint: disable=unused-argument
    """
    Replaces ltk.schedule with a mock implementation that calls the specified function immediately.
    """
    try:
        function()
    except Exception:  # pylint: disable=broad-except
        pass


def mock_functions_for_testing():
    """
    Replaces various functions and modules with mock implementations for testing purposes.
    """
    ltk.get_time = time.time
    ltk.schedule = schedule
    ltk.post = lambda url, data, done: "OK"
    state.mobile = lambda: True
    state.show_worker_status = lambda: True
    state.console.write = lambda *args, action=None: True


mock_functions_for_testing()
