"""
Copyright (c) 2024 laffra - All Rights Reserved. 

Manages the history of edits made to a sheet, including adding new edits, flushing changes to storage,
and undoing the most recent edit.
"""


import ltk

import state
import storage
import models
import timeline

history = []


class SingleEdit:
    """
    A context manager for edits that should be considered as one for undo.
    """
    def __init__(self, description):
        self.description = description

    def __enter__(self):
        add(models.EditGroup(self.description))
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        add(models.EmptyEdit())
        flush()  # Flush changes when exiting the context




def add(edit):
    """
    Adds an edit to the history and schedules a flush of the changes to storage.
    """
    if isinstance(edit, models.EmptyEdit):
        return
    if history and isinstance(history[-1], models.EditGroup):
        history[-1].add(edit)
    else:
        history.append(edit)
        timeline.add_edit(edit)

    schedule_flush()


def schedule_flush():
    """
    Schedules a flush of the changes to storage.
    """
    ltk.schedule( flush, "flush events", 0)


def flush():
    """
    Flushes the changes to the storage and schedules a status update to be displayed after a short delay.
    """
    storage.save(state.SHEET)
    ltk.schedule(show_status, "show status", 0.3)


def show_status():
    """
    Displays a message in the console indicating that all changes have been saved.
    """
    if state.console.contains("Sheet"):
        state.console.write("Sheet", "[History] All changes have been saved.")


def undo(sheet):
    """
    Undoes the most recent edit in the history and schedules a flush of the changes to storage.

    Args:
        sheet (models.Sheet): The sheet object to undo the edit on.

    Returns:
        None
    """
    while history:
        edit = history.pop()
        timeline.remove(edit)
        if edit.undo(sheet):
            schedule_flush()
            return
