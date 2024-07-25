import ltk
import logging
import state
from pyscript import window # type: ignore
import constants

logger = logging.getLogger('root')


def landing(event):
    window.open("https://pysheets.app")


def feedback(event):
    window.open("https://docs.google.com/forms/d/e/1FAIpQLScmeDuDr5fxKYhe04Jo-pNS73P4VF2m-i8X8EC9rfKl-jT84A/viewform")


def discord(event):
    window.open("https://discord.gg/4wy23872th")


def create_menu(sheet):
    file_menu = ltk.Menu("File",
        ltk.MenuItem("➕", "New", "", lambda item: new_sheet()),
        ltk.MenuItem("📂", "Open", "Cmd+O", lambda item: go_home()),
        ltk.MenuItem("🗑", "Delete", "", lambda item: delete_sheet()),
    )
    view_menu = ltk.Menu("View",
        ltk.MenuItem("◱", "Full Screen", "", lambda event: ltk.document.body.requestFullscreen()),
    )
    help_menu = ltk.Menu("Help",
        ltk.MenuItem("🅿️", "About", "", ltk.proxy(landing)),
        ltk.MenuItem("👏", "Feedback", "", ltk.proxy(feedback)),
        ltk.MenuItem("💬", "Discord", "", ltk.proxy(discord)),
    )
    return ltk.MenuBar([
        file_menu, 
        view_menu, 
        help_menu
    ]).css("opacity", 0).animate(ltk.to_js({ "opacity": 1 }), constants.ANIMATION_DURATION)


def delete_sheet():
    if window.confirm("This will permanently delete the current sheet."):
        import storage
        storage.delete(
            state.uid,
            lambda result: ltk.find("#main").animate({
                "opacity": 0,
            },
            constants.ANIMATION_DURATION_VERY_SLOW,
            ltk.proxy(lambda: go_home()))
        )


IMPORT_MESSAGE = """
PySheets supports importing of Excel, Google Sheets, and CSV.
<br><br>
To import a sheet, simply enter a URL into any of the cells in the sheet.
The AI will then propose the next step.
<br><br>
A message will appear in the console for the next step.
"""


def import_sheet():
    ltk.Div(IMPORT_MESSAGE) \
        .attr("title", "Importing a Sheet into PySheets") \
        .dialog(ltk.to_js({ "width": 350 }))


def go_home():
    window.document.location = "/"


def load_doc(uid):
    window.document.location = f"?{constants.SHEET_ID}={uid}"


def new_sheet():
    import models
    import storage
    uid = window.crypto.randomUUID()
    sheet = models.Sheet(uid=window.crypto.randomUUID())
    storage.save(sheet)
    load_doc(uid)


ltk.find(".logo").on("click", ltk.proxy(lambda event: go_home()))
