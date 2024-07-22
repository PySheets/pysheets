import ltk
import models
import storage
import state


history = []


def add(edit):
    history.append(edit)
    if isinstance(edit, models.USER_EDITS):
        state.console.write("Sheet", f"[History] Saving...")
    schedule_flush()

def schedule_flush():
    ltk.schedule(lambda: flush(), "flush events", 0)

def flush():
    storage.save(state.sheet)
    ltk.schedule(show_status, "show status", 0.3)
    
def show_status():
    if state.console.contains("Sheet"):
        state.console.write("Sheet", f"[History] All changes were saved.")

def undo(sheet):
    while history:
        edit = history.pop()
        if edit.undo(sheet):
            print("undo", edit)
            schedule_flush()
            return
