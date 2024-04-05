from flask import Flask
from flask import jsonify
from flask import render_template
from flask import request
from flask import send_file

import base64
import json
import logging
import storage
import time
import traceback
import requests

from static.constants import *


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
        DATA_KEY_ERROR: f"{error.__class__.__name__}: {error}",
        DATA_KEY_STATUS: "error",
    }
    return response


@app.errorhandler(404) 
def handle_error(error):
    app.logger.error("404: %s", request.path)
    return "Nothing here"


RUNTIME_PYODIDE = "py"
RUNTIME_MICROPYTHON = "mpy"
FILES = """
    "static/constants.py" = "constants.py"
    "static/menu.py" = "menu.py"
    "static/state.py" = "state.py"
    "static/pysheets.py" = "pysheets.py"
    "static/editor.py" = "editor.py"
    "static/api.py" = "api.py"
"""
FILES_LTK = """
    "https://raw.githubusercontent.com/laffra/ltk/main/ltk/jquery.py" = "ltk/jquery.py"
    "https://raw.githubusercontent.com/laffra/ltk/main/ltk/widgets.py" = "ltk/widgets.py"
    "https://raw.githubusercontent.com/laffra/ltk/main/ltk/pubsub.py" = "ltk/pubsub.py"
    "https://raw.githubusercontent.com/laffra/ltk/main/ltk/__init__.py" = "ltk/__init__.py"
    "https://raw.githubusercontent.com/laffra/ltk/main/ltk/logger.py" = "ltk/logger.py"
    "https://raw.githubusercontent.com/laffra/ltk/main/ltk/ltk.js" = "ltk/ltk.js"
    "https://raw.githubusercontent.com/laffra/ltk/main/ltk/ltk.css" = "ltk/ltk.css"
"""


@app.route("/")
def root():
    package_names = request.args.get(DATA_KEY_PACKAGES, "").split()
    pyodide = request.args.get(DATA_KEY_RUNTIME, "") == "pyodide"
    files = FILES + FILES_LTK
    runtime = RUNTIME_PYODIDE if pyodide else RUNTIME_MICROPYTHON
    interpreter = '' if pyodide else 'interpreter = "1.22.0-272"'
    version_interpreter = 'latest' if pyodide else '1.22.0-272'
    auto = 'experimental_create_proxy = "auto"' if pyodide else ''
    packages = f"packages=[{','.join(repr(package) for package in package_names)}]" if pyodide else ""
    vm = "" if runtime == RUNTIME_MICROPYTHON else f" {', '.join(['Pyodide'] + package_names)}"
    return render_template("index.html", **locals())


@app.route("/list")
def list_files():
    files = storage.list_files(request.args.get(DATA_KEY_TOKEN))
    return jsonify({ DATA_KEY_IDS: files })


def get_file(token):
    if not token:
        return "{}"
    uid = request.args.get(DATA_KEY_UID)
    if not uid:
        return jsonify({ DATA_KEY_UID: storage.new(token) })
    else:
        timestamp = float(request.args.get(DATA_KEY_TIMESTAMP, "0"))
        data = storage.get_file(token, uid) or {
            DATA_KEY_NAME: "",
            DATA_KEY_CELLS: {},
            DATA_KEY_UID: uid,
            DATA_KEY_SCREENSHOT: None
        }
        if timestamp and timestamp == data[DATA_KEY_TIMESTAMP]:
            return jsonify({
                DATA_KEY_STATUS: "Unchanged",
                DATA_KEY_UID: uid,
            })
        data[DATA_KEY_STATUS] = "Changed" if timestamp else "Fetched"
        if DATA_KEY_SCREENSHOT in data:
            del data[DATA_KEY_SCREENSHOT]
        return jsonify(data)


def post_file(token):
    data = get_form_data()
    uid = data[DATA_KEY_UID]
    app.logger.info("POST %s %s %s", token, uid, len(body))
    storage.save(token, uid, data)
    return jsonify({DATA_KEY_STATUS: "OK"})


def delete_file(token):
    uid = request.args.get(DATA_KEY_UID)
    storage.delete(token, uid)
    return jsonify({DATA_KEY_STATUS: "OK"})


FILE_ACTIONS = {
    "GET": get_file,
    "POST": post_file,
    "DELETE": delete_file,
}

def get_form_data():
    form = request.form.to_dict()
    return json.loads(list(form.keys())[0])

@app.route("/login", methods=["POST"])
def login():
    data = get_form_data()
    token = storage.login(data[DATA_KEY_EMAIL], data[DATA_KEY_PASSWORD])
    return {
        DATA_KEY_TOKEN: token,
        DATA_KEY_STATUS: "OK" if token else "error",
    }


@app.route("/register", methods=["POST"])
def register():
    data = get_form_data()
    return { DATA_KEY_STATUS: storage.register(data[DATA_KEY_EMAIL], data[DATA_KEY_PASSWORD]) }


@app.route("/reset", methods=["POST"])
def reset():
    data = get_form_data()
    return { DATA_KEY_STATUS: storage.reset_password(data[DATA_KEY_EMAIL]) }


@app.route("/reset_code", methods=["POST"])
def reset_code():
    data = get_form_data()
    token = storage.reset_password_with_code(data[DATA_KEY_EMAIL], data[DATA_KEY_PASSWORD], data[DATA_KEY_CODE])
    return {
        DATA_KEY_TOKEN: token,
        DATA_KEY_STATUS: "OK" if token else "error",
    }


@app.route("/confirm", methods=["POST"])
def confirm():
    data = get_form_data()
    token = storage.confirm(data[DATA_KEY_EMAIL], data[DATA_KEY_PASSWORD], data[DATA_KEY_CODE])
    return {
        DATA_KEY_TOKEN: token,
        DATA_KEY_STATUS: "OK" if token else "error",
    }


@app.route("/share", methods=["GET"])
def share():
    uid = request.args.get(DATA_KEY_UID)
    email = request.args.get(DATA_KEY_EMAIL)
    token = request.args.get(DATA_KEY_TOKEN)
    storage.share(token, uid, email)
    return jsonify({ DATA_KEY_STATUS: "OK" })


@app.route("/complete", methods=["POST"])
def complete():
    data = get_form_data()
    token = request.args.get(DATA_KEY_TOKEN)
    prompt = data[DATA_KEY_PROMPT]
    return storage.complete(prompt, token)


@app.route("/users", methods=["GET"])
def users():
    response = storage.get_users(request.args.get(DATA_KEY_TOKEN))
    return base64.b64encode(json.dumps(response).encode('utf-8')) # send base64 encoded bytes


@app.route("/file", methods=["GET", "POST", "DELETE"])
def file():
    return FILE_ACTIONS[request.method](request.args.get(DATA_KEY_TOKEN))


@app.route("/edits", methods=["GET"])
def edits():
    return storage.get_edits(
        request.args.get(DATA_KEY_TOKEN),
        request.args.get(DATA_KEY_UID),
        request.args.get(DATA_KEY_TIMESTAMP)
    )


@app.route("/history", methods=["GET"])
def history():
    return storage.get_history(
        request.args.get(DATA_KEY_TOKEN),
        request.args.get(DATA_KEY_UID),
        request.args.get(DATA_KEY_BEFORE),
        request.args.get(DATA_KEY_AFTER)
    )


@app.route("/forget", methods=["GET"])
def forget():
    return { 
        "status": "OK",
        "removed": storage.forget(request.args[DATA_KEY_TOKEN]),
    }


@app.route("/edit", methods=["POST"])
def edit():
    data = get_form_data()
    email = storage.get_email(request.args.get(DATA_KEY_TOKEN))
    return storage.add_edit(
        email,
        data[DATA_KEY_UID],
        data[DATA_KEY_EDIT],
    )


@app.route("/logs", methods=["GET"])
def logs():
    response = storage.get_logs(
        request.args.get(DATA_KEY_TOKEN),
        request.args.get(DATA_KEY_UID),
        request.args.get(DATA_KEY_TIMESTAMP),
    )
    print("Logs", request.args.get(DATA_KEY_UID), "=>", response)
    return base64.b64encode(json.dumps(response).encode('utf-8')) # send base64 encoded bytes


@app.route("/log", methods=["POST"])
def log():
    data = get_form_data()
    doc_uid = data[DATA_KEY_UID]
    token = request.args.get(DATA_KEY_TOKEN)
    for time, message in data[DATA_KEY_ENTRIES]:
        storage.log(token, doc_uid, time, message)
    return f'{{ "{DATA_KEY_RESULT}":  "OK" }}'


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
    app.logger.info("Load, url=%s token=%s", request.args.get(DATA_KEY_URL), request.args.get(DATA_KEY_TOKEN))
    if storage.get_email(request.args.get(DATA_KEY_TOKEN)):
        url = request.args.get(DATA_KEY_URL)
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
