from pymongo import MongoClient

import json
import random
import re
import requests
import sys
import time
import uuid

sys.path.append(".")

import static.constants as constants

from storage.settings import admins
from storage.settings import EXPIRATION_MINUTE_SECONDS
from storage.tutorials import TUTORIAL_UIDS
from storage.identity import hash_prompt
from storage.identity import hash_password

__all__ = [
    # ai
    "get_completion_budget", "get_cached_completion", "set_cached_completion", "increment_budget",
    # files
    "new", "save", "get_file", "get_file_with_uid", "list_files", "delete",
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

MONGO_HOST = "localhost"
MONGO_PORT = 27017

mongo_config = {
    "host": MONGO_HOST,
    "port": MONGO_PORT,
    "username": "pysheets-admin",
    "password": "bmlyXWlRYX15",
}
client = MongoClient(**mongo_config)
db = client["pysheets"]

# User Management
email_to_info = db["email_to_info"]
token_to_email = db["token_to_email"]
registration = db["registration"]
reset = db["reset"]

# Document Storage
email_to_files = db["email_to_files"]
docid_to_doc = db["docid_to_doc"]

# AI Completion
email_to_completion_budget = db["email_to_completion_budget"]
prompt_to_completion = db["prompt_to_completion"]

# Observability
docid_to_logs = db["docid_to_logs"]

logger = None


def set_logger(app_logger):
    global logger
    logger = app_logger


def get_completion_budget(email):
    budget = email_to_completion_budget.find_one({"_id": email})
    if not budget:
        budget = {
            "_id": email,
            "total": 0,
            "last": 0,
        }
        email_to_completion_budget.insert_one(budget)
    return budget


def increment_budget(email, budget):
    budget["total"] += 1
    budget["last"] = time.time()
    email_to_completion_budget.update_one({"_id": email}, {"$set": budget})


def get_cached_completion(prompt):
    return prompt_to_completion.find_one({"_id": hash_prompt(prompt)})


def set_cached_completion(prompt, completion):
    prompt_to_completion.update_one(
        {"_id": hash_prompt(prompt)}, {"$set": completion}, upsert=True
    )


def get_email(token):
    user = token_to_email.find_one({"_id": token})
    return user[constants.DATA_KEY_EMAIL] if user else None


def login(email, password, reset=False):
    if not email:
        logger.info(f"Login email not provided.")
        return ""
    info = email_to_info.find_one({"_id": email})
    if not info:
        logger.info(f"Login email not registered: {email}")
        return ""
    password_hash = info.get(constants.DATA_KEY_PASSWORD)
    if not reset and not hash_password(password) == password_hash:
        logger.info(f"Login password hash different. Password length: {len(password)}")
        return ""
    token = str(uuid.uuid1())
    email_to_info.update_one(
        {"_id": email},
        {
            "$set": {
                constants.DATA_KEY_PASSWORD: hash_password(password),
                constants.DATA_KEY_TOKEN: token,
                constants.DATA_KEY_EXPIRATION: time.time() + EXPIRATION_MINUTE_SECONDS,
            }
        },
    )
    token_to_email.update_one(
        {"_id": token}, {"$set": {constants.DATA_KEY_EMAIL: email}}, upsert=True
    )
    logger.info(f"Login succes: {email}/{len(password)} => {token}")
    return token


def get_code():
    def digit():
        return random.choice(range(1, 10))

    return f"{digit()}{digit()}{digit()}{digit()}{digit()}{digit()}"


def register(email, password):
    if not re.match(r"^\S+@\S+\.\S+$", email):
        logger.info("[Storage] Register %s - Error - invalid email pattern", email)
        return "error"
    if email_to_info.find_one({"_id": email}):
        logger.info("[Storage] Register %s - Error - email exists", email)
        return "error"
    code = get_code()
    logger.info("[Storage] Register %s with %s", email, code)
    registration.insert_one(
        {
            "_id": code,
            constants.DATA_KEY_EMAIL: email,
            constants.DATA_KEY_TIMESTAMP: int(time.time()),
            constants.DATA_KEY_PASSWORD: hash_password(password),
        }
    )
    send_confirmation(
        email,
        f"{code} - PySheets - Confirm your registration",
        f"Your PySheets registration code is {code}",
    )
    return "Please check your email"


def reset_password(email):
    if not email_to_info.find_one({"_id": email}):
        logger.info("[Storage] Reset %s - Error - email does not exist", email)
        return "error"
    code = get_code()
    logger.info("[Storage] Reset %s with %s", email, code)
    reset.insert_one(
        {
            "_id": code,
            constants.DATA_KEY_EMAIL: email,
        }
    )
    send_confirmation(
        email,
        f"{code} - PySheets - Confirm your password reset",
        f"Your PySheets password reset code is {code}",
    )
    return "Please check your email"


def reset_password_with_code(email, password, code):
    if not email_to_info.find_one({"_id": email}):
        logger.info(
            "[Storage] Reset with code %s - Error - email does not exist", email
        )
        return "error"
    reset_doc = reset.find_one({"_id": code})
    if not reset_doc:
        logger.error(
            "[Storage] Reset with code %s %s - Error - code does not exist", email, code
        )
        return "error"
    logger.info("[Storage] Reset %s with %s", email, code)
    if email != reset_doc[constants.DATA_KEY_EMAIL]:
        logger.error(
            "[Storage] Reset with code %s %s - Error - email does not match",
            email,
            code,
        )
        return "error"
    return login(email, password, reset=True)


def confirm(email, password, code):
    details = registration.find_one({"_id": code})
    logger.info("[Storage] Confirm %s with %s", email, code)
    if details[constants.DATA_KEY_EMAIL] == email:
        email_to_info.update_one(
            {"_id": email},
            {
                "$set": {
                    constants.DATA_KEY_EMAIL: email,
                    constants.DATA_KEY_PASSWORD: details[constants.DATA_KEY_PASSWORD],
                }
            },
            upsert=True,
        )
        copy_tutorial(email)
        return login(email, password, reset=True)


def copy_tutorial(email):
    files = email_to_files.find_one({"_id": email}, {"_id": 0, "files": 1})
    if not files:
        files = {"files": []}
        email_to_files.insert_one({"_id": email, "files": []})
    for tutorial_uid in TUTORIAL_UIDS:
        uid = str(uuid.uuid4())
        logger.info("[Storage] Copy tutorial %s to %s for %s", tutorial_uid, uid, email)
        data = get_file_with_uid(tutorial_uid)
        data[constants.DATA_KEY_UID] = uid
        docid_to_doc.insert_one(data)
        files["files"].append(uid)
    email_to_files.update_one({"_id": email}, {"$set": {"files": files["files"]}})
    logger.info("[Storage] Copied tutorial for %s", email)


def get_user_files(token):
    email = get_email(token)
    if email:
        files = email_to_files.find_one({"_id": email}, {"_id": 0, "files": 1})
        return files["files"] if files else []
    return []


def list_files(token):
    if not token:
        return []
    files = []
    for uid in get_user_files(token):
        document = docid_to_doc.find_one({"_id": uid})
        if document:
            files.append(
                (
                    uid,
                    document.get(constants.DATA_KEY_NAME, ""),
                    document.get(constants.DATA_KEY_SCREENSHOT, ""),
                    document.get(constants.DATA_KEY_RUNTIME, "micropython"),
                    document.get(constants.DATA_KEY_PACKAGES, "") or [],
                )
            )
    return files


def send_confirmation(email, subject, body):
    send_mail(
        "laffra@gmail.com",
        "New PySheets User",
        f"A new user, {email} just registered for PySheets",
    )
    response = send_mail(email, subject, body)
    logger.info("[Storage] Sent confirmation email to %s: %s", email, response)
    return response


def post(url, data):
    try:
        return requests.post(url, data, verify=True).content
    except:
        pass
    try:
        return requests.post(url, data, verify=False).content
    except Exception as e:
        return f"error: {e}"


def send_mail(email, subject, body):
    url = "https://chrislaffra.com/mail.php"
    data = {
        "c": "Z9qhy2XaT4g",
        "f": "no-reply@pysheets.app",
        "e": email,
        "s": subject,
        "b": body,
    }
    return post(url, data) == "OK"


def new(token):
    new_uid = str(uuid.uuid4())
    email = get_email(token)
    if email:
        files = email_to_files.find_one({"_id": email}, {"_id": 0, "files": 1})
        if not files:
            files = {"files": []}
            email_to_files.insert_one({"_id": email, "files": []})
        files["files"].append(new_uid)
        email_to_files.update_one({"_id": email}, {"$set": {"files": files["files"]}})
    return new_uid


def save(token, uid, data):
    data["_id"] = uid
    docid_to_doc.update_one({"_id": uid}, {"$set": data}, upsert=True)
    email = get_email(token)
    if email:
        files = email_to_files.find_one({"_id": email}, {"_id": 0, "files": 1})
        if not files:
            files = {"files": []}
            email_to_files.insert_one({"_id": email, "files": []})
        if uid not in files["files"]:
            files["files"].append(uid)
            email_to_files.update_one(
                {"_id": email}, {"$set": {"files": files["files"]}}
            )
    return uid


def delete(token, uid):
    email = get_email(token)
    if email:
        files = email_to_files.find_one({"_id": email}, {"_id": 0, "files": 1})
        if files and uid in files["files"]:
            files["files"].remove(uid)
            email_to_files.update_one(
                {"_id": email}, {"$set": {"files": files["files"]}}
            )
    docid_to_doc.delete_one({"_id": uid})


def forget(token):
    email = get_email(token)
    if email:
        files = email_to_files.find_one({"_id": email}, {"_id": 0, "files": 1})
        if files:
            for uid in files["files"]:
                docid_to_doc.delete_one({"_id": uid})
        email_to_files.delete_one({"_id": email})
        email_to_info.delete_one({"_id": email})
        token_to_email.delete_one({"_id": token})
    return len(files["files"]) if files else 0


def get_file(token, uid):
    if uid in get_user_files(token):
        return get_file_with_uid(uid)


def get_file_with_uid(uid):
    data = docid_to_doc.find_one({"_id": uid}) or {
        constants.DATA_KEY_NAME: "Untitled Sheet",
        constants.DATA_KEY_CURRENT: "A1",
        constants.DATA_KEY_TIMESTAMP: time.time(),
        constants.DATA_KEY_COLUMNS: {},
        constants.DATA_KEY_ROWS: {},
        constants.DATA_KEY_CELLS: {},
    }
    if constants.DATA_KEY_CELLS_ENCODED in data:
        data[constants.DATA_KEY_CELLS] = json.loads(data[constants.DATA_KEY_CELLS_ENCODED])
    return data


def get_logs(token, uid, ts):
    check_admin(token)
    logs = [
        log
        for log in docid_to_logs.find(
            {"_id": uid, constants.DATA_KEY_TIMESTAMP: {"$gt": float(ts)}}, {"_id": 0}
        )
    ]
    return {
        constants.DATA_KEY_UID: uid,
        constants.DATA_KEY_TIMESTAMP: ts,
        constants.DATA_KEY_LOGS: logs,
    }


def log(token, doc_uid, time, message):
    if not doc_uid:
        return 
    entry = {
        constants.DATA_KEY_TOKEN: token,
        constants.DATA_KEY_TIMESTAMP: time,
        constants.DATA_KEY_MESSAGE: message,
    }
    docid_to_logs.update_one(
        {"_id": doc_uid},
        {"$addToSet": {"logs": entry}},
        upsert=True
    )


def check_owner(token, uid):
    email = get_email(token)
    if email:
        files = email_to_files.find_one({"_id": email}, {"_id": 0, "files": 1})
        if files and uid in files["files"]:
            return
    raise ValueError("owner")


def check_admin(token):
    email = get_email(token)
    if email and email in admins:
        return
    raise ValueError(f"{email} is not an admin")


def share(token, sheet_id, email):
    check_owner(token, sheet_id)
    if not token_to_email.find_one({"_id": email}):
        token_to_email.insert_one(
            {
                "_id": email,
                constants.DATA_KEY_EMAIL: email,
            }
        )
    email_to_files.update_one(
        {"_id": email}, {"$addToSet": {"files": sheet_id}}, upsert=True
    )


def get_all_emails(token):
    check_admin(token)
    return list(
        set(
            filter(
                None,
                [
                    doc[constants.DATA_KEY_EMAIL]
                    for doc in token_to_email.find(
                        {}, {constants.DATA_KEY_EMAIL: 1, "_id": 0}
                    )
                ],
            )
        )
    )


def get_files(email):
    files = email_to_files.find_one({"_id": email}, {"_id": 0, "files": 1})
    return (
        [docid_to_doc.find_one({"_id": uid}) for uid in files["files"]] if files else []
    )


def get_file_ids(email):
    files = email_to_files.find_one({"_id": email}, {"_id": 0, "files": 1})
    try:
        return [file[constants.DATA_KEY_UID] for file in files["files"] or []]
    except:
        return [file for file in files["files"] or []]


def get_users(token):
    check_admin(token)
    users = {}
    for email in get_all_emails(token):
        users[email] = get_file_ids(email)
    return {"users": users}


if __name__ == "__main__":
    from storage.firestore import dump, get_all_emails, get_files

    def migrate_mapping(name):
        n = 0
        for n, (token, obj) in enumerate(dump(name)):
            obj["_id"] = token
            if constants.DATA_KEY_VALUE in obj:
                value = obj[constants.DATA_KEY_VALUE]
                for key, value in value.items():
                    obj[key] = value
            try:
                db[name].insert_one(obj)
            except:
                pass # already loaded this object

    token = "faa58bae-f1ac-11ee-a84e-8ec652b6ed36"
    emails = get_all_emails(token)
    doc_uids = set()

    def migrate_files():
        for email in emails:
            files = email_to_files.find_one({"_id": email})
            if not files:
                files = {"files": []}
                email_to_files.insert_one({"_id": email, "files": []})
            files["files"] = get_file_ids(email)
            doc_uids.update(files["files"])
            email_to_files.update_one(
                {"_id": email}, {"$set": {"files": files["files"]}}
            )

    migrate_files()
    migrate_mapping("token_to_email")
    migrate_mapping("email_to_info")
    migrate_mapping("registration")
    migrate_mapping("reset")
    migrate_mapping("docid_to_doc")

