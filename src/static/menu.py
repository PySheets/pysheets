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
    def go_home():
        ltk.window.document.location = "/"

    ltk.find(".logo").on("click", ltk.proxy(lambda event: go_home()))

    return ltk.MenuBar([
        create_file_menu(),
        create_view_menu(),
        create_help_menu()
    ]).css("opacity", 0).animate(ltk.to_js({ "opacity": 1 }), constants.ANIMATION_DURATION)


def handle_import_preview(data):
    """
    Handle a message from the worker with a preview of a CSV or Excel
    """
    ltk.find("#import-data-preview").html(data["preview"])
    ltk.find(".import-final-button").attr("disabled", False)


def handle_import_done(data): # pylint: disable=unused-argument
    """
    Handle a request from the UI to import a CSV or Excel from the web
    """
    ltk.find("#import-dialog").remove()


ltk.subscribe("Importer", constants.TOPIC_WORKER_PREVIEW_IMPORTED_WEB, handle_import_preview)
ltk.subscribe("Importer", constants.TOPIC_WORKER_IMPORTED_WEB, handle_import_done)


def import_sheet():
    """
    Show a dialog to let the user import a sheet.
    """

    if state.UI.editor.get():
        return ltk.window.alert("Please select an empty cell and press 'import' again.")

    def load_from_web(event): # pylint: disable=unused-argument
        state.UI.set_random_color()
        ltk.publish(
            "Importer",
            "Worker",
            constants.TOPIC_WORKER_PREVIEW_IMPORT_WEB,
            {
                "url": ltk.find("#import-web-url").val()
            },
        )
        # result will arrive in handle_import

    def import_into_sheet(event): # pylint: disable=unused-argument
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

    def load_dataframe(event): # pylint: disable=unused-argument
        url = ltk.find("#import-web-url").val()
        state.UI.set_random_color()
        state.UI.current.set(f"""=
pysheets.load_sheet("{url}")
        """)
        ltk.find("#import-dialog").remove()

    def load_polars(event): # pylint: disable=unused-argument
        url = ltk.find("#import-web-url").val()
        state.UI.set_random_color()
        state.UI.current.set(f"""=
import io
import urllib.request
import polars

url = "{url}"
csv_bytes = io.BytesIO(urllib.request.urlopen(url).read())
polars.read_csv(csv_bytes)
        """)
        ltk.find("#import-dialog").remove()

    def load_duckdb(event): # pylint: disable=unused-argument
        packages = set(["duckdb", "fsspec"] + ltk.find("#packages").val().split())
        ltk.find("#packages").val(" ".join(list(packages)))
        ltk.find("#reload-button").click()
        url = ltk.find("#import-web-url").val()
        state.UI.set_random_color()
        state.UI.current.set(f"""=
import io
import urllib.request
import duckdb

url = "{url}"
csv_bytes = io.BytesIO(urllib.request.urlopen(url).read())
csv_sql = duckdb.read_csv(csv_bytes)
select = '''SELECT * FROM csv_sql'''
where = ''''''
duckdb.sql(f"{{select}} {{where}}").df()
        """)
        ltk.find("#import-dialog").remove()

    dialog = (
        ltk.Div(
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
                    ltk.Button("Pandas", load_dataframe)
                        .addClass("import-load-dataframe-button")
                        .addClass("import-final-button")
                        .attr("disabled", True),
                    ltk.Button("Polars", load_polars)
                        .addClass("import-load-dataframe-button")
                        .addClass("import-final-button")
                        .attr("disabled", True),
                    ltk.Button("DuckDB", load_duckdb)
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
        .dialog()
    )
    dialog.dialog("option", "modal", True)
    dialog.dialog("option", "width", 800)
    dialog.dialog("option", "height", "auto")



def create_file_menu():
    """
    Create a file menu.
    """
    def go_home(event): # pylint: disable=unused-argument
        ltk.window.document.location = "/"

    def download(event): # pylint: disable=unused-argument
        import models # pylint: disable=import-outside-toplevel
        state.SHEET.screenshot = ""
        json_data = models.encode(state.SHEET)
        json_data = ltk.window.JSON.stringify(ltk.window.JSON.parse(json_data), None, 4)
        url = f"data:text/json;charset=utf-8,{ltk.window.encodeURIComponent(json_data)}"
        name = state.SHEET.name.replace(" ", "_").lower()
        dialog = ltk.VBox(
            ltk.Text("""
                After you download this sheet as a JSON file, you can commit it to github
                or upload it to Google Drive, Dropbox, or any other cloud storage.
            """),
            ltk.Break(),
            ltk.Text("""
                After your uploaded file is reachable as a url, you can load it into
                PySheets as https://pysheets.app/?open=your_url.
            """),
            ltk.Break(),
            ltk.HBox(
                ltk.Link(url, "Download Now")
                    .attr("download", name + ".json")
                    .addClass("download-link")
                    .css("color", "white")
                    .on("click", ltk.proxy(lambda event: dialog.remove())),
            ),
            ltk.Break(),
        ).dialog({
            "title": "Download Sheet",
            "modal": True,
            "width": 500,
            "height": "auto",
        })


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
        ltk.MenuItem("💾", "Download", "", ltk.proxy(download)),
    ] + ([
        ltk.MenuItem("📥", "Import ...", "", ltk.proxy(lambda event: import_sheet())),
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
        ltk.window.open("https://discord.gg/m6mkZ5me")

    def show_tutorial(event): # pylint: disable=unused-argument
        ltk.window.open("https://github.com/PySheets/pysheets?tab=readme-ov-file#tutorials")

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
    load_doc(sheet.uid, new=True)


def load_doc(uid, new=False):
    """
    Loads a document with the given unique identifier (uid).
    
    Args:
        uid (str): The unique identifier of the document to load.
        new (bool): Indicates whether the document is new or not.
    
    Returns:
        None
    """
    ltk.window.document.location = f"?{constants.SHEET_ID}={uid}&{constants.NEW_SHEET}={new}"
