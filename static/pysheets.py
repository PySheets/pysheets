"""
CopyRight (c) 2024 - Chris Laffra - All Rights Reserved.

Initializes the PySheets application and sets up the necessary components.
"""

import sys

import ltk
import constants
import inventory
import storage
import state

from views.spreadsheet import SpreadsheetView



state.console.write("pysheets", f"[Main] Pysheets starting {constants.ICON_HOUR_GLASS}")


def load_ui():
    """
    Loads the user interface for the PySheets application.
    """

    state.clear()

    def load_inventory():
        inventory.list_sheets()

    def load_sheet_with_model(model):
        state.SHEET = model
        SpreadsheetView(model)

    if state.UID:
        storage.load_sheet(state.UID, load_sheet_with_model)
    else:
        load_inventory()


def write_startup_message():
    """
    Writes a startup message to the application console.
    """
    vm_type = state.vm_type(sys.version)
    vm_version = sys.version.split()[0].replace(";", "")
    message = f"[UI] Running {vm_type}; Python {vm_version}; UI startup took {ltk.get_time():.3f}s."
    state.console.write("pysheets", message)


def main():
    """
    The main entry point for the PySheets application. 
    """
    write_startup_message()
    state.start_worker()
    ltk.subscribe(constants.PUBSUB_SHEET_ID, constants.TOPIC_WORKER_PRINT, print)
    ltk.subscribe(constants.PUBSUB_SHEET_ID, ltk.TOPIC_INFO, print)
    ltk.subscribe(constants.PUBSUB_SHEET_ID, ltk.TOPIC_ERROR, print)
    storage.setup(load_ui)
