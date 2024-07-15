import sqlite3
import uuid
import time
import json
import random
import threading

import static.constants as constants
import static.models as models

from storage.settings import admins
from storage.settings import EXPIRATION_MINUTE_SECONDS
from storage.tutorials import TUTORIAL_UIDS
from storage.identity import hash_prompt
from storage.identity import hash_password

logger = None
def set_logger(app_logger):
    global logger
    logger = app_logger


# Thread-local storage for SQLite connections
local_data = threading.local()

def connect():
    if not hasattr(local_data, "connection"):
        local_data.connection = sqlite3.connect("pysheets.db")
    connection = local_data.connection
    return connection, connection.cursor()


# Perform SQLite operations using the cursor 'c'

def setup():
    connection, cursor = connect()
    # Create tables
    cursor.execute('''CREATE TABLE IF NOT EXISTS users
                (email TEXT PRIMARY KEY, password TEXT, token TEXT, expiration REAL)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS sheets
                (uid TEXT PRIMARY KEY, name TEXT, data TEXT, screenshot TEXT, timestamp REAL)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS edits
                (sheet_id TEXT, user TEXT, timestamp REAL, edits TEXT, PRIMARY KEY (sheet_id, user, timestamp))''')
    connection.commit()


def get_email(token):
    return "no-email@pysheets.app"

def login(email, password, reset=False):
    pass

def new(token):
    connection, cursor = connect()
    new_uid = str(uuid.uuid4())
    email = get_email(token)
    if email:
        cursor.execute("INSERT INTO sheets (uid, name) VALUES (?, 'Untitled Sheet')", (new_uid,))
        connection.commit()
    return new_uid

def save(token, uid, sheet):
    connection, cursor = connect()
    email = get_email(token)
    if email:
        data = models.encode(sheet)
        cursor.execute("UPDATE sheets SET data = ?, name = ?, screenshot = ?, timestamp = ? WHERE uid = ?",
                  (data, sheet.name, sheet.screenshot, time.time(), uid))
        connection.commit()
    return uid

def get_sheet(token, uid):
    connection, cursor = connect()
    email = get_email(token)
    if email:
        cursor.execute("SELECT data FROM sheets WHERE uid = ?", (uid,))
        result = cursor.fetchone()
        if result:
            return models.decode(result[0] or json.dumps(models.Sheet()))

def get_sheet_with_uid(uid):
    connection, cursor = connect()
    cursor.execute("SELECT data FROM sheets WHERE uid = ?", (uid,))
    result = cursor.fetchone()
    if result:
        return models.decode(result[0])
    else:
        return models.Sheet()

def list_files(token):
    connection, cursor = connect()
    email = get_email(token)
    print("list files", email)
    if email:
        cursor.execute("SELECT uid, name, screenshot FROM sheets")
        results = cursor.fetchall()
        return [(uid, name, screenshot, "micropython", []) for uid, name, screenshot in results]
    return []

def delete(token, uid):
    connection, cursor = connect()
    email = get_email(token)
    if email:
        cursor.execute("DELETE FROM sheets WHERE uid = ?", (uid,))
        connection.commit()

def save_edits(token, sheet_id, start, edits):
    connection, cursor = connect()
    if not edits:
        return
    user = f"{token}-{start}"
    timestamp = time.time()
    cursor.execute("INSERT INTO edits (sheet_id, user, timestamp, edits) VALUES (?, ?, ?, ?)",
              (sheet_id, user, timestamp, str(edits)))
    connection.commit()

def get_edits(token, sheet_id, start, timestamp):
    connection, cursor = connect()
    user = f"{token}-{start}"
    cursor.execute("SELECT edits FROM edits WHERE sheet_id = ? AND user != ? AND timestamp > ?",
              (sheet_id, user, timestamp))
    results = cursor.fetchall()
    return [eval(edits[0]) for edits in results]

# Implement other functions as needed...

def get_code():
    connection, cursor = connect()
    def digit():
        return random.choice(range(1, 10))

    return f"{digit()}{digit()}{digit()}{digit()}{digit()}{digit()}"

def register(email, password):
    pass

def reset_password(email):
    pass

def reset_password_with_code(email, password, code):
    pass

def confirm(email, password, code):
    pass

def copy_tutorial(email):
    pass

def forget(token):
    pass

def send_confirmation(email, subject, body):
    pass

def share(token, sheet_id, email):
    pass

def get_completion_budget(email):
    import sys
    return {
        "total": -1,
        "last": -1,
    }

def set_completion_budget(email, budget):
    pass

def get_completion(prompt):
    return None

def set_completion(prompt, completion):
    pass

def increment_budget(email, budget):
    pass

def get_cached_completion(prompt):
    pass

def set_cached_completion(prompt, completion):
    pass
