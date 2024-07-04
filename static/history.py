import constants
import ltk
import models
import state

from pyscript import window # type: ignore


edits = []
history = []


def add(edit):
    # error = f"edit must be a models.Edit object, instead got {edit.__class__.__name__}"
    # assert isinstance(edit, models.Edit), error
    edits.append(edit)
    history.append(edit)


def undo(sheet):
    while history:
        edit = history.pop()
        if edit.undo(sheet):
            return


def handle_edits(handler, response):
    state.doc.last_edit = window.time()
    new_edits = response[constants.DATA_KEY_EDITS]
    if state.mode == constants.MODE_DEVELOPMENT:
        for n in range(10):
            state.console.clear(f"edit-up-{n}")
            state.console.clear(f"edit-down-{n}")
        for n,edit in enumerate(edits[:10]):
            state.console.write(f"edit-up-{n}", "[Edits] ⬆", n, edit)
        for n,edit in enumerate(new_edits[:10]):
            state.console.write(f"edit-down-{n}", "[Edits] ️️️⬇", n, edit)
    if edits or new_edits:
        state.console.write("edits", f"[Edits] Document saved. (⬆️{len(edits)} ⬇️{len(new_edits)} )")
    edits.clear()
    if handler:
        handler(new_edits)


def sync_edits(handler=None):
    for chunk in range(0, len(edits), 100):
        send_edits(handler, edits[chunk:chunk+10])


def send_edits(handler, edits):
    ltk.post(
        f"/edits?{constants.DATA_KEY_UID}={state.doc.uid}&{constants.DATA_KEY_START}={window.start}&{constants.DATA_KEY_TIMESTAMP}={state.doc.last_edit}",
        {
            constants.DATA_KEY_TIMESTAMP: window.time(),
            constants.DATA_KEY_EDITS: str(edits),
        },
        ltk.proxy(handler)
    )


# ltk.find(ltk.window).on("beforeunload", ltk.proxy(lambda: sync_edits()))