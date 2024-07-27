"""
CopyRight (c) 2024 - Chris Laffra - All Rights Reserved.

Mock for PyScript's polyscript module
"""

from unittest.mock import MagicMock

def __getattr__(name):  # pylint: disable=unused-argument
    return MagicMock()
