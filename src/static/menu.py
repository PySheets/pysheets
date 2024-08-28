"""
Copyright (c) 2024 laffra - All Rights Reserved. 

This module provides functions for creating and managing the application menu.

"""

import logging

import ltk
import state
import constants

logger = logging.getLogger('root')


def create_menu():
    """
    Creates the application menu with the following options:
    
    - File menu:
        - New: Creates a new sheet
        - Open: Goes to the home page
        - Delete: Deletes the current sheet
    
    - View menu:
        - Full Screen: Toggles full screen mode
    
    - Help menu:
        - About: Opens the PySheets website
        - Feedback: Opens a feedback form
        - Discord: Opens the PySheets Discord server
    
    The menu is animated to fade in when it is created.
    """
    def about(event): # pylint: disable=unused-argument
        ltk.window.open("/about")

    def feedback(event): # pylint: disable=unused-argument
        ltk.window.open("https://docs.google.com/forms/d/e/1FAIpQLScmeDuDr5fxKYhe04Jo"
                    "-pNS73P4VF2m-i8X8EC9rfKl-jT84A/viewform")

    def discord(event): # pylint: disable=unused-argument
        ltk.window.open("https://discord.gg/4wy23872th")

    def go_home():
        ltk.window.document.location = "/"

    def delete_sheet():
        if ltk.window.confirm("This will permanently delete the current sheet."):
            import storage # pylint: disable=import-outside-toplevel
            storage.delete(
                state.UID,
                ltk.proxy(lambda result: go_home()),
                ltk.window.alert
            )

    file_menu = ltk.Menu("File",
        ltk.MenuItem("➕", "New", "", lambda item: new_sheet()),
        ltk.MenuItem("📂", "Open", "Cmd+O", lambda item: go_home()),
    )
    if state.UID:
        file_menu.popup.append(
            ltk.MenuItem("🗑", "Delete", "", lambda item: delete_sheet()),
        )
    view_menu = ltk.Menu("View",
        ltk.MenuItem("⌞⌝", "Full Screen", "", lambda event: ltk.document.body.requestFullscreen()),
    )
    help_menu = ltk.Menu("Help",
        ltk.MenuItem("🅿️", "About", "", ltk.proxy(about)),
        ltk.MenuItem("👏", "Feedback", "", ltk.proxy(feedback)),
        ltk.MenuItem("💬", "Discord", "", ltk.proxy(discord)),
    )
    ltk.find(".logo").on("click", ltk.proxy(lambda event: go_home()))
    return ltk.MenuBar([
        file_menu,
        view_menu,
        help_menu
    ]).css("opacity", 0).animate(ltk.to_js({ "opacity": 1 }), constants.ANIMATION_DURATION)


def new_sheet():
    """
    Creates a new sheet and saves it to storage, then loads the new sheet.
    """
    import models # pylint: disable=import-outside-toplevel
    import storage # pylint: disable=import-outside-toplevel
    uid = ltk.window.crypto.randomUUID()
    sheet = models.Sheet(uid=ltk.window.crypto.randomUUID())
    storage.save(sheet)
    load_doc(uid)


def load_doc(uid):
    """
    Loads a document with the given unique identifier (uid).
    
    Args:
        uid (str): The unique identifier of the document to load.
    
    Returns:
        None
    """
    ltk.window.document.location = f"?{constants.SHEET_ID}={uid}"
