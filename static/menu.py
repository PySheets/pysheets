import ltk
import logging
import state
from pyscript import window # type: ignore
import constants

logger = logging.getLogger('root')


def landing(event):
    window.open("/")


def feedback(event):
    window.open("https://docs.google.com/forms/d/e/1FAIpQLScmeDuDr5fxKYhe04Jo-pNS73P4VF2m-i8X8EC9rfKl-jT84A/viewform")


def discord(event):
    window.open("https://discord.com/invite/4jjFF6hj")


def create_menu(sheet):
    return ltk.MenuBar(
        ltk.Menu("File",
             ltk.MenuItem("➕", "New", "", lambda item: new_sheet()),
             ltk.MenuItem("📂", "Open", "Cmd+O", lambda item: go_go()),
             ltk.MenuItem("📂", "Import", "", lambda item: import_sheet()),
             ltk.MenuItem("🎁", "Share", "", lambda item: share_sheet()),
             ltk.MenuItem("🗑", "Delete", "", lambda item: delete_doc()),
             ltk.MenuItem("R", "Restore", "", lambda item: sheet.restore()),
        ),
        ltk.Menu("View",
             ltk.MenuItem("◱", "Full Screen", "", lambda event: ltk.document.body.requestFullscreen()),
        ),
        ltk.Menu("User",
            ltk.MenuItem("👋", "Sign out", "", ltk.proxy(state.logout)),
            ltk.MenuItem("💀", "Forget me", "", ltk.proxy(state.forget_me)),
        ),
        ltk.Menu("Help",
            ltk.MenuItem("🅿️", "About", "", ltk.proxy(landing)),
            ltk.MenuItem("👏", "Feedback", "", ltk.proxy(feedback)),
            ltk.MenuItem("💬", "Discord", "", ltk.proxy(discord)),
        )
    )
DELETE_PROMPT = """
This will permanently delete the current sheet.
You and anyone it has been shared with will lose access.
We cannot recover the contents.

Enter the name of the sheet to actually delete it:")
"""


def delete_doc():
    if window.prompt(DELETE_PROMPT) == state.doc.name:
        url = f"/file?{constants.DATA_KEY_UID}={state.doc.uid}"
        ltk.delete(state.add_token(url), lambda data: go_go())


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


def go_go():
    window.document.location = "/go"


def load_doc(uid):
    window.document.location = f"?{constants.DATA_KEY_UID}={uid}"


def share(uid, email):
    logger.info("share %s %s %s", uid, "with", email)
    def confirm(response):
        if response[constants.DATA_KEY_STATUS] == "error":
            logger.error(response[constants.DATA_KEY_STATUS])
            window.alert(response[constants.DATA_KEY_STATUS])
        logger.info(f"Sheet {state.doc.uid} was shared with {email}")

    url = f"/share?{constants.DATA_KEY_UID}={uid}&{constants.DATA_KEY_EMAIL}={email}"
    ltk.get(state.add_token(url), ltk.proxy(confirm))
    close_share_dialog()


def close_share_dialog():
    ltk.find(".share-popup").dialog('close')


def new_sheet():
    state.doc.name = "Untitled"
    ltk.get(state.add_token("/file"), ltk.proxy(lambda data: load_doc(data[constants.DATA_KEY_UID])))


def share_sheet():
    ltk.VBox(
        ltk.Text("Email name to share with:").addClass("share-label"),
        ltk.Input("").attr("id", "share-email").addClass("share-email"),
        ltk.HBox(
            ltk.Button("Cancel", lambda event: close_share_dialog()).addClass("cancel-button"),
            ltk.Button("Share", lambda event: share(state.doc.uid, ltk.find("#share-email").val())).addClass("share-button"),
        ).css("margin-left", "auto")
    ).dialog().addClass("share-popup").parent().width(350)


ltk.find(".logo").on("click", ltk.proxy(lambda event: go_go()))
