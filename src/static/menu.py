"""
Copyright (c) 2024 laffra - All Rights Reserved. 

This module provides functions for creating and managing the application menu.

"""

import logging

import ltk
import state
import constants
import tutorial

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
    def go_home():
        ltk.window.document.location = "/"

    ltk.find(".logo").on("click", ltk.proxy(lambda event: go_home()))

    return ltk.MenuBar([
        create_file_menu(),
        create_view_menu(),
        create_help_menu()
    ]).css("opacity", 0).animate(ltk.to_js({ "opacity": 1 }), constants.ANIMATION_DURATION)


def handle_import_preview(data):
    ltk.find("#import-data-preview").html(data["preview"])
    ltk.find(".import-final-button").attr("disabled", False)


def handle_import_done(data):
    ltk.find("#import-dialog").remove()


ltk.subscribe("Importer", constants.TOPIC_WORKER_PREVIEW_IMPORTED_WEB, handle_import_preview)
ltk.subscribe("Importer", constants.TOPIC_WORKER_IMPORTED_WEB, handle_import_done)


def share_sheet():
    """
    Create a dialog to let the user share a sheet.
    """
    sheet = state.SHEET

    def handle_url(data):
        url = data["url"]
        ltk.find("#share-url").text(url, data).attr("href", url)

    url = "https://pysheets.app/share"
    ltk.post(
        url,
        {
            "sheet": {
                "cells": dict(
                    (cell.key, {
                        "value": cell.value,
                        "script": cell.script,
                        "prompt": cell.prompt,
                        "style": dict([
                            (property, value)
                            for property, value in cell.style.items()
                            if value
                        ])
                    })
                    for cell in sheet.cells.values()
                ),
                "columns": sheet.columns,
                "rows": sheet.rows,
                "packages": sheet.packages,
                "name": f"Copy of {sheet.name}",
                "selected": sheet.selected,
            }
        },
        ltk.proxy(handle_url)
    )

    (ltk.Div(
        ltk.VBox(
            ltk.Strong("Here is a link to a copy of your sheet:")
                .css("font-size", 20),
            ltk.Break(),
            ltk.HBox(
                ltk.Link("#", "Loading...")
                    .attr("id", "share-url"),
                ltk.Button("🔗", click=lambda event: ltk.window.navigator.clipboard.writeText(ltk.find("#share-url").text()))
                    .addClass("copy-button")
            ),
        )
    )
    .addClass("share-dialog")
    .attr("id", "share-dialog")
    .attr("title", "Share Your Sheet")
    .dialog({
        "modal": True,
        "width": 530,
        "height": "auto"
    })
    .find("button").focus())


def import_sheet():
    """
    Show a dialog to let the user import a sheet.
    """

    if state.UI.editor.get():
        return ltk.window.alert("Please select an empty cell and press 'import' again.")

    def load_from_web(event):
        ltk.publish(
            "Importer",
            "Worker",
            constants.TOPIC_WORKER_PREVIEW_IMPORT_WEB,
            {
                "url": ltk.find("#import-web-url").val()
            },
        )
        # result will arrive in handle_import

    def web_url_changed(event):
        ltk.find("#import-web-url-load-button").attr("disabled", False)

    def import_into_sheet(event):
        ltk.publish(
            "Application",
            "Worker",
            constants.TOPIC_WORKER_IMPORT_WEB,
            {
                "url": ltk.find("#import-web-url").val(),
                "start_key": state.UI.current.model.key,
            },
        )
        # result will arrive in handle_import_done

    def load_dataframe(event):
        url = ltk.find("#import-web-url").val()
        state.UI.current.set(f"""=
pysheets.load_sheet("{url}")
        """)
        ltk.find("#import-dialog").remove()

    def upload_file(event):
        ltk.publish(
            "Application",
            "Worker",
            constants.TOPIC_WORKER_UPLOAD,
            {
                "id": "import-file",
            },
        )

    (ltk.Div(
        ltk.VBox(
            ltk.HBox(
                ltk.Input("")
                    .addClass("import-web-url-input")
                    .attr("id", "import-web-url")
                    .on("input", ltk.proxy(load_from_web))
                    .attr("placeholder", "Enter a web url..."),
            ),
            ltk.HBox(
                ltk.Div()
                    .addClass("import-data-preview")
                    .attr("id", "import-data-preview")
            ),
            ltk.HBox(
                ltk.Button("Import into Sheet", import_into_sheet)
                    .addClass("import-into-sheet-button")
                    .addClass("import-final-button")
                    .attr("disabled", True),
                ltk.Button("Load as Dataframe", load_dataframe)
                    .addClass("import-load-dataframe-button")
                    .addClass("import-final-button")
                    .attr("disabled", True),
                ltk.Button("Cancel", handle_import_done)
                    .addClass("import-cancel-button")
                    .addClass("import-final-button")
            )
        )
    )
    .addClass("import-dialog")
    .attr("id", "import-dialog")
    .attr("title", "Import Data")
    .dialog({
        "modal": True,
        "width": 530,
        "height": "auto"
    }))


def create_file_menu():
    """
    Create a file menu.
    """
    def go_home(event): # pylint: disable=unused-argument
        ltk.window.document.location = "/"

    def delete_sheet(event): # pylint: disable=unused-argument
        if ltk.window.confirm("This will permanently delete the current sheet."):
            import storage # pylint: disable=import-outside-toplevel
            storage.delete(
                state.UID,
                ltk.proxy(go_home),
                ltk.window.alert
            )

    items = [
        ltk.MenuItem("➕", "New", "", ltk.proxy(lambda event: new_sheet())),
        ltk.MenuItem("📂", "Open", "Cmd+O", ltk.proxy(go_home)),
    ] + ([
        ltk.MenuItem("📥", "Import ...", "", ltk.proxy(lambda event: import_sheet())),
        ltk.MenuItem("📥", "Share a copy ...", "", ltk.proxy(lambda event: share_sheet())),
        ltk.MenuItem("🗑️", "Delete", "", ltk.proxy(delete_sheet)),
    ] if state.UID else [])
    return ltk.Menu("File", items)


def create_view_menu():
    """
    Create a view menu.
    """
    return ltk.Menu("View",
        ltk.MenuItem("⌞⌝", "Full Screen", "", lambda event: ltk.document.body.requestFullscreen()),
    )


def create_help_menu():
    """
    Create a help menu.
    """
    def about(event): # pylint: disable=unused-argument
        ltk.window.open("/about")

    def feedback(event): # pylint: disable=unused-argument
        ltk.window.open("https://docs.google.com/forms/d/e/1FAIpQLScmeDuDr5fxKYhe04Jo"
                    "-pNS73P4VF2m-i8X8EC9rfKl-jT84A/viewform")

    def discord(event): # pylint: disable=unused-argument
        ltk.window.open("https://discord.gg/4wy23872th")

    def show_tutorial(event): # pylint: disable=unused-argument
        tutorial.show()

    return ltk.Menu("Help",
        ltk.MenuItem("🅿️", "About", "", ltk.proxy(about)),
        ltk.MenuItem("🎓️", "Tutorial", "", ltk.proxy(show_tutorial)),
        ltk.MenuItem("👏", "Feedback", "", ltk.proxy(feedback)),
        ltk.MenuItem("💬", "Discord", "", ltk.proxy(discord)),
    )


def new_sheet():
    """
    Creates a new sheet and saves it to storage, then loads the new sheet.
    """
    import models # pylint: disable=import-outside-toplevel
    import storage # pylint: disable=import-outside-toplevel
    sheet = models.Sheet(uid=ltk.window.crypto.randomUUID())
    storage.save(sheet)
    load_doc(sheet.uid)


def load_doc(uid):
    """
    Loads a document with the given unique identifier (uid).
    
    Args:
        uid (str): The unique identifier of the document to load.
    
    Returns:
        None
    """
    ltk.window.document.location = f"?{constants.SHEET_ID}={uid}"
