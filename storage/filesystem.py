import os
import json
import uuid
import time
from pathlib import Path

import static.constants as constants
import static.models as models

__all__ = [
    # files
    "new", "save", "get_sheet", "list_files", "delete", "save_edits", "get_edits",
    # sharing
    "share",
    # identity
    "get_email", "forget", "login", "register", "reset_password", "reset_password_with_code", "confirm",
    # monitoring
    "log", "set_logger", "get_all_emails", "get_logs", "get_users",
]

logger = None
def set_logger(app_logger):
    global logger
    logger = app_logger

DATA_DIR = "data"
USERS_DIR = os.path.join(DATA_DIR, "users")
SHEETS_DIR = os.path.join(DATA_DIR, "sheets")
LOGS_DIR = os.path.join(DATA_DIR, "logs")

# Create directories if they don't exist
Path(USERS_DIR).mkdir(parents=True, exist_ok=True)
Path(SHEETS_DIR).mkdir(parents=True, exist_ok=True)
Path(LOGS_DIR).mkdir(parents=True, exist_ok=True)

# User Management
def get_user_dir(email):
    return os.path.join(USERS_DIR, email)

def get_sheet_path(uid):
    return os.path.join(SHEETS_DIR, f"{uid}.json")

def get_log_path(uid):
    return os.path.join(LOGS_DIR, f"{uid}.log")

# Document Storage
def new(token):
    new_uid = str(uuid.uuid4())
    email = get_email(token)
    if email:
        user_dir = get_user_dir(email)
        Path(user_dir).mkdir(parents=True, exist_ok=True)
        with open(os.path.join(user_dir, "sheets.txt"), "a") as f:
            f.write(f"{new_uid}\n")
    return new_uid

def save(token, uid, sheet):
    doc = {constants.SHEET: models.encode(sheet)}
    with open(get_sheet_path(uid), "w") as f:
        json.dump(doc, f)
    email = get_email(token)
    if email:
        user_dir = get_user_dir(email)
        Path(user_dir).mkdir(parents=True, exist_ok=True)
        with open(os.path.join(user_dir, "sheets.txt"), "a") as f:
            f.write(f"{uid}\n")
    return uid

def delete(token, uid):
    email = get_email(token)
    if email:
        user_dir = get_user_dir(email)
        with open(os.path.join(user_dir, "sheets.txt"), "r") as f:
            sheets = f.readlines()
        with open(os.path.join(user_dir, "sheets.txt"), "w") as f:
            for sheet in sheets:
                if sheet.strip() != uid:
                    f.write(sheet)
    os.remove(get_sheet_path(uid))

def get_sheet(token, uid):
    if uid in get_user_files(token):
        return get_sheet_with_uid(uid)

def get_sheet_with_uid(uid):
    with open(get_sheet_path(uid), "r") as f:
        doc = json.load(f)
    return models.decode(doc[constants.SHEET])

def get_user_files(token):
    email = get_email(token)
    if email:
        user_dir = get_user_dir(email)
        if os.path.exists(os.path.join(user_dir, "sheets.txt")):
            with open(os.path.join(user_dir, "sheets.txt"), "r") as f:
                sheets = f.readlines()
            return [sheet.strip() for sheet in sheets]
    return []

def list_files(token):
    if not token:
        return []
    files = []
    for uid in get_user_files(token):
        try:
            sheet = get_sheet_with_uid(uid)
            if sheet:
                files.append(
                    (
                        uid,
                        sheet.name,
                        sheet.screenshot,
                        "micropython",
                        [], # sheet.packages,
                    )
                )
        except:
            pass
    return files

# Sharing
def share(token, sheet_id, email):
    check_owner(token, sheet_id)
    user_dir = get_user_dir(email)
    Path(user_dir).mkdir(parents=True, exist_ok=True)
    with open(os.path.join(user_dir, "sheets.txt"), "a") as f:
        f.write(f"{sheet_id}\n")

# Identity
# ... (implement identity functions here)

# Monitoring
def log(token, doc_uid, time, message):
    if not doc_uid:
        return
    log_path = get_log_path(doc_uid)
    with open(log_path, "a") as f:
        f.write(f"{time} - {token} - {message}\n")

def get_logs(token, uid, ts):
    check_admin(token)
    logs = []
    log_path = get_log_path(uid)
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            for line in f:
                timestamp, _, message = line.split(" - ", 2)
                if float(timestamp) > float(ts):
                    logs.append(message.strip())
    return {
        constants.DATA_KEY_UID: uid,
        constants.DATA_KEY_TIMESTAMP: ts,
        constants.DATA_KEY_LOGS: logs,
    }

# ... (implement other functions here)