from flask import Flask
from flask import jsonify
from flask import render_template
from flask import request
from flask import send_file

import base64
import json
import logging
import ai
import storage
import time
import traceback
import requests

from templates import html
import static.constants as constants
import static.models as models


app = Flask(__name__)
storage.set_logger(app.logger)
app.logger.setLevel(logging.INFO)


@app.after_request
def set_response_headers(response):
    response.headers['Cross-Origin-Embedder-Policy'] = 'require-corp'
    response.headers['X-Custom-Header'] = 'value'
    response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
    response.headers['Cross-Origin-Resource-Policy'] = 'cross-origin'
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response


@app.errorhandler(Exception) 
def handle_error(error):
    app.logger.error(error)
    traceback.print_exc()
    response = { 
        constants.DATA_KEY_ERROR: f"{error.__class__.__name__}: {error}",
        constants.DATA_KEY_STATUS: "error",
    }
    return response


@app.errorhandler(404) 
def handle_error(error):
    app.logger.error("404: %s", request.path)
    return "Nothing here"


RUNTIME_PYODIDE = "py"
import os
PATH = os.path.join(os.path.dirname(__file__), "static")
RUNTIME_MICROPYTHON = "mpy"
FILES = """
    "static/constants.py" = "constants.py"
    "static/menu.py" = "menu.py"
    "static/state.py" = "state.py"
    "static/pysheets.py" = "pysheets.py"
    "static/timeline.py" = "timeline.py"
    "static/editor.py" = "editor.py"
    "static/api.py" = "api.py"
    "static/lsp.py" = "lsp.py"
    "static/preview.py" = "preview.py"
    "static/inventory.py" = "inventory.py"
    "static/login.py" = "login.py"
    "static/models.py" = "models.py"
    "static/selection.py" = "selection.py"
    "static/history.py" = "history.py"
"""
FILES_LTK = """
    "https://raw.githubusercontent.com/pyscript/ltk/main/ltk/jquery.py" = "ltk/jquery.py"
    "https://raw.githubusercontent.com/pyscript/ltk/main/ltk/widgets.py" = "ltk/widgets.py"
    "https://raw.githubusercontent.com/pyscript/ltk/main/ltk/pubsub.py" = "ltk/pubsub.py"
    "https://raw.githubusercontent.com/pyscript/ltk/main/ltk/__init__.py" = "ltk/__init__.py"
    "https://raw.githubusercontent.com/pyscript/ltk/main/ltk/logger.py" = "ltk/logger.py"
    "https://raw.githubusercontent.com/pyscript/ltk/main/ltk/ltk.js" = "ltk/ltk.js"
    "https://raw.githubusercontent.com/pyscript/ltk/main/ltk/ltk.css" = "ltk/ltk.css"
"""


@app.route("/")
def root():
    if request.args:
        return go()
    return render_template("landing.html")


@app.route("/go")
def go():
    token = request.cookies.get(constants.DATA_KEY_TOKEN)
    uid = request.args.get(constants.DATA_KEY_UID, "")
    package_names = request.args.get(constants.DATA_KEY_PACKAGES, "").split()
    pyodide = package_names or request.args.get(constants.DATA_KEY_RUNTIME) == "pyodide"
    loading = "Loading..."
    files = FILES + FILES_LTK
    runtime = RUNTIME_PYODIDE if pyodide else RUNTIME_MICROPYTHON
    interpreter = '' if pyodide else 'interpreter = "1.23.0"'
    version_interpreter = 'latest' if pyodide else '1.23.0'
    version_storage = storage.version
    auto = 'experimental_create_proxy = "auto"' if pyodide else ''
    vm = "" if runtime == RUNTIME_MICROPYTHON else f" {', '.join(['Pyodide'] + package_names)}"
    packages = f"packages=[{','.join(repr(package) for package in package_names)}]" if pyodide else ""
    previews = []
    path = PATH
    token = "none" if storage.version == "Sqlite" else ""
    if uid:
        sheet = storage.get_sheet(token, uid)
        name = sheet.name
        timestamp = sheet.updated_timestamp
        selected = sheet.selected
        package_list = request.args.get(constants.DATA_KEY_PACKAGES, "")
        editor_width = request.args.get(constants.DATA_KEY_EDITOR_WIDTH, "350")
        sheet_html = html.make_html(sheet)
        css = html.make_css(sheet)
        encoded_sheet = models.encode(sheet)
    else:
        package_list = editor_width = name = selected = timestamp = sheet = ""
        cells = []
    return render_template("index.html", **locals())


@app.route("/list")
def list_files():
    files = storage.list_files(request.cookies.get(constants.DATA_KEY_TOKEN))
    return jsonify({ constants.DATA_KEY_IDS: files })


@app.route("/new")
def new_file():
    token = request.cookies.get(constants.DATA_KEY_TOKEN)
    return jsonify({constants.DATA_KEY_UID: storage.new(token)})


@app.route("/delete", methods=["DELETE"])
def delete_file():
    token = request.cookies.get(constants.DATA_KEY_TOKEN)
    uid = request.args.get(constants.DATA_KEY_UID)
    storage.delete(token, uid)
    return jsonify({constants.DATA_KEY_STATUS: "OK"})


def get_form_data():
    form = request.form.to_dict()
    try:
        json_data = list(form.keys())[0]
        data = json.loads(json_data)
    except:
        data = form
    if isinstance(data, list):
        data = data[0]
    return data

@app.route("/login", methods=["POST"])
def login():
    data = get_form_data()
    token = storage.login(data[constants.DATA_KEY_EMAIL], data[constants.DATA_KEY_PASSWORD])
    return {
        constants.DATA_KEY_TOKEN: token,
        constants.DATA_KEY_STATUS: "OK" if token else "error",
    }


@app.route("/register", methods=["POST"])
def register():
    data = get_form_data()
    return { constants.DATA_KEY_STATUS: storage.register(data[constants.DATA_KEY_EMAIL], data[constants.DATA_KEY_PASSWORD]) }


@app.route("/reset", methods=["POST"])
def reset():
    data = get_form_data()
    return { constants.DATA_KEY_STATUS: storage.reset_password(data[constants.DATA_KEY_EMAIL]) }


@app.route("/reset_code", methods=["POST"])
def reset_code():
    data = get_form_data()
    token = storage.reset_password_with_code(data[constants.DATA_KEY_EMAIL], data[constants.DATA_KEY_PASSWORD], data[constants.DATA_KEY_CODE])
    return {
        constants.DATA_KEY_TOKEN: token,
        constants.DATA_KEY_STATUS: "OK" if token else "error",
    }


@app.route("/confirm", methods=["POST"])
def confirm():
    data = get_form_data()
    token = storage.confirm(data[constants.DATA_KEY_EMAIL], data[constants.DATA_KEY_PASSWORD], data[constants.DATA_KEY_CODE])
    return {
        constants.DATA_KEY_TOKEN: token,
        constants.DATA_KEY_STATUS: "OK" if token else "error",
    }


@app.route("/share", methods=["GET"])
def share():
    uid = request.args.get(constants.DATA_KEY_UID)
    email = request.args.get(constants.DATA_KEY_EMAIL)
    token = request.cookies.get(constants.DATA_KEY_TOKEN)
    storage.share(token, uid, email)
    return jsonify({ constants.DATA_KEY_STATUS: "OK" })


@app.route("/complete", methods=["POST"])
def complete():
    data = get_form_data()
    token = request.cookies.get(constants.DATA_KEY_TOKEN)
    prompt = data[constants.DATA_KEY_PROMPT]
    return ai.complete(prompt, token)


@app.route("/users", methods=["GET"])
def users():
    return storage.get_users(request.cookies.get(constants.DATA_KEY_TOKEN))


@app.route("/edits", methods=["GET", "POST"])
def edits():
    token = request.cookies.get(constants.DATA_KEY_TOKEN)
    start = float(request.args.get(constants.DATA_KEY_START, 0))
    timestamp = float(request.args.get(constants.DATA_KEY_TIMESTAMP))
    uid = request.args.get(constants.DATA_KEY_UID)

    # save edits
    edits = get_form_data()
    storage.save_edits(token, uid, start, edits)
    sheet = storage.get_sheet(token, uid)
    for edit_dict in eval(edits[constants.DATA_KEY_EDITS]):
        models.convert(edit_dict).apply(sheet)
    sheet.updated_timestamp = timestamp
    storage.save(token, uid, sheet)

    # get new edits
    return {
        constants.DATA_KEY_EDITS: storage.get_edits(token, uid, start, timestamp)
    }


@app.route("/emails", methods=["GET"])
def emails():
    response = {
        "emails": storage.get_all_emails(request.cookies.get(constants.DATA_KEY_TOKEN))
    }
    return base64.b64encode(json.dumps(response).encode('utf-8')) # send base64 encoded bytes


@app.route("/embed", methods=["GET"])
def embed():
    key = request.args.get(constants.DATA_KEY_CELL)
    uid = request.args.get(constants.DATA_KEY_UID)
    sheet = storage.get_sheet_with_uid(uid)
    if key in sheet.cells:
        cell = sheet.cells[key]
        if cell.embed:
            return cell.preview
    return f'<html>[Chart is missing]</html>'


@app.route("/forget", methods=["GET"])
def forget():
    return { 
        "status": "OK",
        "removed": storage.forget(request.args[constants.DATA_KEY_TOKEN]),
    }


@app.route("/logs", methods=["GET"])
def logs():
    response = storage.get_logs(
        request.cookies.get(constants.DATA_KEY_TOKEN),
        request.args.get(constants.DATA_KEY_UID),
        request.args.get(constants.DATA_KEY_TIMESTAMP),
    )
    return base64.b64encode(json.dumps(response).encode('utf-8')) # send base64 encoded bytes


@app.route("/log", methods=["POST"])
def log():
    data = get_form_data()
    doc_uid = data[constants.DATA_KEY_UID]
    token = request.cookies.get(constants.DATA_KEY_TOKEN)
    for time, message in data[constants.DATA_KEY_ENTRIES]:
        storage.log(token, doc_uid, time, message)
    return f'{{ "{constants.DATA_KEY_RESULT}":  "OK" }}'


def ssl_get(url, headers=None):
    try:
        return requests.get(url, verify=True, headers=headers or {}).content
    except Exception as e:
        app.logger.error("ssl_get: error %s: %s", url, e)
        pass
    try:
        return requests.get(url, verify=False, headers=headers or {}).content
    except Exception as e:
        app.logger.error("ssl_get: error %s: %s", url, e)
        return f"error: {e}"


def ssl_post(url, data, headers=None):
    try:
        return requests.post(url, data, verify=True, headers=headers or {}).content
    except:
        pass
    try:
        return requests.post(url, data, verify=False, headers=headers or {}).content
    except Exception as e:
        return f"error: {e}"

load_cache = {}

@app.route("/load", methods=["GET", "POST"])
def load():
    app.logger.info("Load, url=%s token=%s", request.args.get(constants.DATA_KEY_URL), request.cookies.get(constants.DATA_KEY_TOKEN))
    if storage.get_email(request.cookies.get(constants.DATA_KEY_TOKEN)):
        url = request.args.get(constants.DATA_KEY_URL)
        if url in load_cache:
            when, response = load_cache[url]
            if time.time() - when < 60:
                app.logger.info("/load: network cache hit: %s", url)
                return response
        headers = {
            "Authorization": request.headers.get("Authorization")
        }
        if request.method == "GET":
            response = ssl_get(url, headers=headers)
        elif request.method == "POST":
            data = get_form_data()
            response = ssl_post(url, data, headers=headers)
        else:
            raise ValueError(f"Bad method {request.method}")
        try:
            response = base64.b64encode(response) # send base64 encoded bytes
        except:
            pass
        load_cache[url] = time.time(), response
        app.logger.info("/load: network cache miss: %s, %s bytes", url, len(response))
        return response # send regular string

    raise ValueError("Not logged in")


@app.route("/<path:path>")
def send(path):
    import os
    if not os.path.exists("static/"+path):
        raise ValueError(f"Cannot return requested file: /static/{path} is missing")
    return app.send_static_file(path)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8081, debug=True)
