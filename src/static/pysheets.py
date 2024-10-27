"""
CopyRight (c) 2024 - Chris Laffra - All Rights Reserved.

Initializes the PySheets application and sets up the necessary components.
"""

import sys

import ltk
import constants
import inventory
import models
import state

from views.spreadsheet import SpreadsheetView

import storage


state.console.write("pysheets", f"[Main] Pysheets starting {constants.ICON_HOUR_GLASS}")
state.console.write(
    "sponsor1",
    "[License] Sponsor PySheets and support the PySheets team 🌷.",
    action=ltk.Link("https://buy.stripe.com/00g1684SS2BZ9Es7st",
        ltk.Button("Buy", click=lambda event: None)
            .addClass("buy-button")
            .css("min-width", 45)
    )
)
state.console.write(
    "help",
    "[Help] Learn more about PySheets with our tutorials 🎓.",
    action=ltk.Button(
        "Learn", 
        lambda event: ltk.window.open(
            "https://github.com/PySheets/pysheets?tab=readme-ov-file#tutorials"
        )
    )
    .addClass("learn-button")
    .css("min-width", 45)
)


def load_ui():
    """
    Loads the user interface for the PySheets application.
    """

    state.clear()

    def load_inventory():
        inventory.list_sheets()

    def load_sheet_with_model(model):
        if model.new and not state.NEW:
            ltk.window.alert("This sheet is not available on this browser.")
        state.UID = model.uid
        state.SHEET = model
        state.UI = SpreadsheetView(model)
        state.start_worker()

    def load(data):
        if "sheet" in data:
            data = data["sheet"]
        if not "uid" in data:
            data["uid"] = state.UID
        sheet = models.Sheet(**data)
        storage.save(sheet)
        load_sheet_with_model(sheet)
        ltk.window.history.pushState(ltk.to_js({}), "", f"?id={state.UID}")

    def load_sheet_from_url():
        state.UID = ltk.window.crypto.randomUUID()
        url = f"/load?{constants.URL}={state.OPEN_URL}"
        ltk.get(url, ltk.proxy(load))

    if state.UID:
        storage.load_sheet(state.UID, load_sheet_with_model)
    elif state.OPEN_URL:
        load_sheet_from_url()
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


def check_version():
    """
    Checks the latest version of the PySheets application.
    """
    def report_version(latest, *rest): # pylint: disable=unused-argument
        latest = latest.strip()
        message = f"You are using the latest version of PySheets: {latest} 👍."
        if latest != ltk.window.version:
            message = f"Upgrade to v{latest} with 'pip install pysheets-app --upgrade' ⛔."
        state.console.write("version", f"[Version] {message}")

    def report_error(xhr, status, error): # pylint: disable=unused-argument
        state.console.write(
            "version", 
            f"[Main] Error getting the latest version of PySheets: {error}."
        )

    if ltk.window.location.host != "pysheets.app":
        ltk.window.ltk_get("https://pysheets.app/version", report_version, "text", report_error)


def handle_buffered_dom_operations(data):
    """
    Handles the DOM operations buffered by the worker to play in the main UI thread.
    
    Args:
        data (str): A dict with a list containing DOM operations
    """
    for operation in data["operations"]:
        selector, function = operation[:2]
        args = operation[2:]
        widget = ltk.find(selector)
        getattr(widget, function)(*args)


def main():
    """
    The main entry point for the PySheets application. 
    """
    check_version()
    write_startup_message()
    ltk.subscribe(constants.PUBSUB_SHEET_ID, constants.TOPIC_WORKER_WIDGET_PROXY, handle_buffered_dom_operations)
    ltk.subscribe(constants.PUBSUB_SHEET_ID, constants.TOPIC_WORKER_PRINT, print)
    ltk.subscribe(constants.PUBSUB_SHEET_ID, ltk.TOPIC_INFO, print)
    ltk.subscribe(constants.PUBSUB_SHEET_ID, ltk.TOPIC_ERROR, print)
    storage.setup(load_ui)
