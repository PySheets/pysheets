from firebase_admin import credentials
from firebase_admin import initialize_app
from firebase_admin import firestore

import hashlib
import json
import openai
import os
import random
import re
import requests
import subprocess
import time
import uuid


openai.api_key = json.loads(open("openai.json").read())["api_key"]
sourcegraph = json.loads(open("sourcegraph.json").read())

import static.constants as constants

logger = None
def set_logger(app_logger):
    global logger
    logger = app_logger


cred = credentials.Certificate('firestore.json')
initialize_app(cred, { 'storageBucket': 'pysheets-399411.appspot.com' })
db = firestore.client()

# User Management
email_to_info = db.collection('email_to_info')
token_to_email = db.collection('token_to_email')
registration = db.collection('registration')
reset = db.collection('reset')

# Document Storage
email_to_files = db.collection('email_to_files')
docid_to_doc = db.collection('docid_to_doc')
docid_to_edits = db.collection('docid_to_edits')

# AI Completion
email_to_completion_budget = db.collection('email_to_completion_budget')
prompt_to_completion = db.collection('prompt_to_completion')

# Observability
docid_to_logs = db.collection('docid_to_logs')


EXPIRATION_MINUTE_SECONDS = 60
EXPIRATION_HOUR_SECONDS = 60 * EXPIRATION_MINUTE_SECONDS
EXPIRATION_DAY_SECONDS = 24 * EXPIRATION_HOUR_SECONDS
EXPIRATION_WEEK_SECONDS = 7 * EXPIRATION_DAY_SECONDS

TUTORIAL_UIDS = [
    "u2b23OTLgKn91dOKi8UC", # Tutorial 1️⃣ - Welcome 👋
    "hFxE6WVMpX5A7kb2CjVL", # Tutorial 2️⃣ - Pandas 🐼
    "0Ych1f6Qfq76eNajGbrz", # Tutorial 3️⃣ - Charts 📊
    "gOmzk2oWGBlcOK4U4M8m", # Tutorial 4️⃣ - Services 🔧
    "8TzCv0pjrwZU1jj4XE0c", # Tutorial 5️⃣ - Advanced 🤓
    "1uTQ3m88BlUNwXFpXRmm", # Tutorial 6️⃣ - AI Completions ⭐
    "iKyXEDL2ZgaqoAVKEbqL", # Tutorial 7️⃣ - JavaScript 🚀
]

admins = [
    "laffra@gmail.com",
]
password_iterations = 100000
password_key_length = 64
password_hash_name = 'sha256'
password_salt = f"{cred.project_id}".encode("utf8")


def hash_password(password):
    password = password.encode("utf-8")

    return hashlib.pbkdf2_hmac(
        hash_name=password_hash_name,
        password=password,
        salt=password_salt,
        iterations=password_iterations,
        dklen=password_key_length
    )


class CompletionBudgetException(Exception): pass


def get_completion_budget(email):
    budget = email_to_completion_budget.document(email).get().to_dict()
    if not budget:
        budget = {
            "total": 0,
            "last": 0,
        }
        email_to_completion_budget.document(email).set(budget)
    return budget

    
def check_completion_budget(email):
    budget = get_completion_budget(email)
    if budget["total"] > 100:
        raise CompletionBudgetException("You reached the lifetime maximum of 100 free completions.")
    seconds = time.time() - budget["last"]
    if seconds < 60:
        raise CompletionBudgetException(f"Slow down. You can ask for completions again in {60 - seconds}s.")
    return budget


def increment_budget(email, budget):
    budget["total"] += 1
    budget["last"] = time.time()
    email_to_completion_budget.document(email).set(budget)


def openai_complete(prompt):
    return openai.Completion.create(
        model="gpt-3.5-turbo-instruct",
        prompt=prompt,
        temperature=0,
        max_tokens=1000,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        stop=["\"\"\""]
    )["choices"][0]

class SourceGraphError(TypeError): pass

def sourcegraph_complete(prompt):
    os.putenv("SRC_ENDPOINT", "https://sourcegraph.com")
    os.putenv("SRC_ACCESS_TOKEN", sourcegraph["token"])
    command = [
        "node_modules/.bin/cody-agent",
        "experimental-cli",
        "chat",
        "-m",
        prompt,
    ]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = process.communicate()
    text = f'{out.decode("utf-8")}{err.decode("utf-8")}'
    if not "```" in text:
        raise SourceGraphError(text)
    text = re.sub(".*```", "", text)
    text = re.sub("```.*", "", text)
    return {
        "text": text
    }


def complete(prompt, token):
    email = get_email(token)
    if not email:
        raise ValueError("login")
    budget = check_completion_budget(email)
    completion = prompt_to_completion.document(prompt).get().to_dict()
    if not completion:
        try:
            completion = sourcegraph_complete(prompt)
        except:
            completion = openai_complete(prompt)
        prompt_to_completion.document(prompt).set(completion)
        increment_budget(email, budget)
    print("###### COMPLETION #########")
    print(type(completion))
    print(completion)
    completion["budget"] = budget
    return completion
    

def get_email(token):
    return token_to_email.document(token).get().to_dict()[constants.DATA_KEY_EMAIL] if token else None


def login(email, password, reset=False):
    if not email:
        logger.info(f"Login email not provided.")
        return ""
    if not email:
        logger.info(f"Login email not provided.")
        return ""
    info = email_to_info.document(email).get()
    if not info.exists:
        logger.info(f"Login email not registered: {email}")
        return ""
    password_hash = info.to_dict().get(constants.DATA_KEY_PASSWORD)
    if not reset and not hash_password(password) == password_hash:
        logger.info(f"Login password hash different. Password length: {len(password)}")
        return ""
    token = str(uuid.uuid1())
    email_to_info.document(email).set({
        constants.DATA_KEY_PASSWORD: hash_password(password),
        constants.DATA_KEY_TOKEN: token,
        constants.DATA_KEY_EXPIRATION: time.time() + EXPIRATION_MINUTE_SECONDS
    })
    token_to_email.document(token).set({
        constants.DATA_KEY_EMAIL: email
    })
    logger.info(f"Login succes: {email}/{len(password)} => {token}")
    return token


def get_code():
    def digit():
        return random.choice(range(1,10))
    return f"{digit()}{digit()}{digit()}{digit()}{digit()}{digit()}"


def register(email, password):
    if not re.match(r"^\S+@\S+\.\S+$", email):
        logger.info("[Storage] Register %s - Error - invalid email pattern", email)
        return "error"
    if email_to_info.document(email).get().exists:
        logger.info("[Storage] Register %s - Error - email exists", email)
        return "error"
    code = get_code()
    logger.info("[Storage] Register %s with %s", email, code)
    registration.document(code).set({
        constants.DATA_KEY_EMAIL: email,
        constants.DATA_KEY_PASSWORD: hash_password(password),
    })
    send_confirmation(
        email,
        f"{code} - PySheets - Confirm your registration",
        f"Your PySheets registration code is {code}",
    )
    return "Please check your email"


def reset_password(email):
    if not email_to_info.document(email).get().exists:
        logger.info("[Storage] Reset %s - Error - email does not exist", email)
        return "error"
    code = get_code()
    logger.info("[Storage] Reset %s with %s", email, code)
    reset.document(code).set({
        constants.DATA_KEY_EMAIL: email,
    })
    send_confirmation(
        email,
        f"{code} - PySheets - Confirm your password reset",
        f"Your PySheets password reset code is {code}",
    )
    return "Please check your email"


def reset_password_with_code(email, password, code):
    if not email_to_info.document(email).get().exists:
        logger.info("[Storage] Reset with code %s - Error - email does not exist", email)
        return "error"
    if not reset.document(code).get().exists:
        logger.error("[Storage] Reset with code %s %s - Error - code does not exist", email, code)
        return "error"
    logger.info("[Storage] Reset %s with %s", email, code)
    if email != reset.document(code).get().to_dict()[constants.DATA_KEY_EMAIL]:
        logger.error("[Storage] Reset with code %s %s - Error - email does not match", email, code)
        return "error"
    return login(email, password, reset=True)


def confirm(email, password, code):
    details = registration.document(code).get().to_dict()
    logger.info("[Storage] Confirm %s with %s", email, code)
    if details[constants.DATA_KEY_EMAIL] == email:
        email_to_info.document(email).set({
            constants.DATA_KEY_EMAIL: email,
            constants.DATA_KEY_PASSWORD: details[constants.DATA_KEY_PASSWORD]
        })
        copy_tutorial(email)
        return login(email, password, reset=True)

    
def copy_tutorial(email):
    files = email_to_files.document(email).collection("files")
    for tutorial_uid in TUTORIAL_UIDS:
        uid = docid_to_doc.document().id
        logger.info("[Storage] Copy tutorial %s to %s for %s", tutorial_uid, uid, email)
        data = get_file_with_uid(tutorial_uid)
        data[ constants.DATA_KEY_UID ] = uid
        docid_to_doc.document(uid).set(data)
        files.document(uid).set({ constants.DATA_KEY_UID: uid})
    logger.info("[Storage] Copied tutorial for %s", email)


def get_user_files(token):
    return email_to_files.document(get_email(token)).collection('files')


def list_files(token):
    if not token:
        return []
    def extract(doc):
        document = docid_to_doc.document(doc.id).get().to_dict()
        if document:
            return (
                doc.id,
                document.get(constants.DATA_KEY_NAME, ''),
                document.get(constants.DATA_KEY_SCREENSHOT, ''),
                document.get(constants.DATA_KEY_RUNTIME, "micropython"),
                document.get(constants.DATA_KEY_PACKAGES, '') or []
            )
    return list(filter(None, [ extract(doc) for doc in get_user_files(token).stream() ]))


def send_confirmation(email, subject, body):
    send_mail("laffra@gmail.com", "New PySheets User", f"A new user, {email} just registered for PySheets")
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
        "b": body
    } 
    return post(url, data) == "OK"


def new(token):
    new_uid = docid_to_doc.document().id
    get_user_files(token).document(new_uid).set({ constants.DATA_KEY_UID: new_uid })
    return new_uid


def save(token, uid, data):
    docid_to_doc.document(uid).set(data)
    return get_user_files(token).document(uid).set({ constants.DATA_KEY_UID: uid })


def delete(token, uid):
    get_user_files(token).document(uid).delete()
    docid_to_doc.document(uid).delete()


def forget(token):
    email = get_email(token)
    count = 0
    for doc in email_to_files.document(email).collection('files').list_documents():
        doc.delete()
        count += 1
    email_to_info.document(email).delete()
    token_to_email.document(token).delete()
    return count


def get_file(token, uid):
    if get_user_files(token).document(uid).get().exists:
        return get_file_with_uid(uid)


def get_file_with_uid(uid):
    file = docid_to_doc.document(uid).get() 
    return file.to_dict() if file.exists else {}


def get_edits(token, uid, ts):
    if not uid:
        return f'{{ "{constants.DATA_KEY_ERROR}": "no uid" }}'
    if get_user_files(token).document(uid).get().exists:
        edits = docid_to_edits.document(uid).collection("edits").where(constants.DATA_KEY_TIMESTAMP, ">", float(ts)).get()
        return {
            constants.DATA_KEY_UID: uid,
            constants.DATA_KEY_TIMESTAMP: ts,
            constants.DATA_KEY_EDITS: [ edit.to_dict() for edit in edits ],
        }


def get_history(token, uid, before, after):
    if not uid:
        return f'{{ "{constants.DATA_KEY_ERROR}": "no uid" }}'
    if get_user_files(token).document(uid).get().exists:
        edits = docid_to_edits.document(uid).collection("edits") \
            .where(constants.DATA_KEY_TIMESTAMP, ">=", float(after)) \
            .where(constants.DATA_KEY_TIMESTAMP, "<=", float(before)) \
            .get()
        return {
            constants.DATA_KEY_UID: uid,
            constants.DATA_KEY_EDITS: [ edit.to_dict() for edit in edits ],
        }


def add_edit(email, uid, edit):
    edit[constants.DATA_KEY_EMAIL] = email
    edit[constants.DATA_KEY_TIMESTAMP] = int(time.time())
    docid_to_edits.document(uid).collection("edits").add(edit)
    return f'{{ "{constants.DATA_KEY_RESULT}":  "OK" }}'


def get_logs(token, uid, ts):
    check_admin(token)
    logs = docid_to_logs.document(uid).collection("logs").where(constants.DATA_KEY_TIMESTAMP, ">", float(ts)).get()
    return {
        constants.DATA_KEY_UID: uid,
        constants.DATA_KEY_TIMESTAMP: ts,
        constants.DATA_KEY_LOGS: [ log.to_dict() for log in logs ],
    }


def log(token, doc_uid, time, message):
    if doc_uid:
        docid_to_logs.document(doc_uid).collection("logs").add({
            constants.DATA_KEY_TOKEN: token,
            constants.DATA_KEY_TIMESTAMP: time,
            constants.DATA_KEY_MESSAGE: message,
        })


def check_owner(token, uid):
    try:
        get_user_files(token).document(uid).get().to_dict()[constants.DATA_KEY_UID]
    except:
        raise ValueError("owner")


def check_admin(token):
    user = token_to_email.document(token).get().to_dict()
    if user and user[constants.DATA_KEY_EMAIL] in admins:
        return
    raise ValueError(f"admin")


def share(token, sheet_id, email):
    check_owner(token, sheet_id)
    if not token_to_email.document(email).get().exists:
        token_to_email.document(email).set({ constants.DATA_KEY_EMAIL: email })
    email_to_files.document(email).collection("files").document(sheet_id).set({ constants.DATA_KEY_UID: sheet_id })
        
    
def get_users(token):
    check_admin(token)
    emails = set(list(filter(None, [
        doc.to_dict().get(constants.DATA_KEY_EMAIL, "")
        for doc in token_to_email.stream()
    ])))
    def get_files(email):
        return [
            doc.to_dict().get(constants.DATA_KEY_UID)
            for doc in email_to_files.document(email).collection('files').stream()
        ]
    return { "users": dict((email, get_files(email)) for email in emails)}