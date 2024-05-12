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
    "static/profiler.py" = "profiler.py"
    "static/editor.py" = "editor.py"
    "static/api.py" = "api.py"
    "static/lsp.py" = "lsp.py"
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
    token = request.cookies.get(DATA_KEY_TOKEN)
    package_names = request.args.get(DATA_KEY_PACKAGES, "").split()
    pyodide = True or request.args.get(DATA_KEY_RUNTIME, "") == "pyodide"
    files = FILES + FILES_LTK
    runtime = RUNTIME_PYODIDE if pyodide else RUNTIME_MICROPYTHON
    interpreter = '' if pyodide else 'interpreter = "1.22.0-272"'
    version_interpreter = 'latest' if pyodide else '1.22.0-272'
    version_storage = storage.version
    auto = 'experimental_create_proxy = "auto"' if pyodide else ''
    packages = f"packages=[{','.join(repr(package) for package in package_names)}]" if pyodide else ""
    vm = "" if runtime == RUNTIME_MICROPYTHON else f" {', '.join(['Pyodide'] + package_names)}"
    uid = request.args.get(DATA_KEY_UID, "")
    if uid:
        data = storage.get_file(token, uid)
        name = data[DATA_KEY_NAME]
        timestamp = data[DATA_KEY_TIMESTAMP]
        current = data[DATA_KEY_CURRENT]
        package_list = request.args.get(DATA_KEY_PACKAGES, "")
        previews = json.dumps([
            (key, value)
            for key, value in data.get(DATA_KEY_PREVIEWS, "{}").items()
        ])
        editor_width = request.args.get(DATA_KEY_EDITOR_WIDTH, "350")
        sheet = make_sheet(data)
        scripts = make_scripts(data)
    else:
        package_list = editor_width = name = current = timestamp = sheet = ""
    return render_template("index.html", **locals())


def make_column_label(col, data):
    label = f"{chr(ord('A') + col - 1)}"
    width = max(25, data[DATA_KEY_COLUMNS].get(str(col), {}).get(DATA_KEY_WIDTH, 72))
    return f'<div class="column-label col-{col}" id="col-{col}" col="{col}" style="width: {width}px">{label}</div>'


def make_column_header(data):
    return "".join((
        [ 
            '<div id="column-header" class="column-header">',
            *[ make_column_label(col, data) for col in range(1, DEFAULT_COLUMN_COUNT + 1) ],
            '</div>'
        ]
    ))


def make_cell(col, row, data):
    width = max(25, data[DATA_KEY_COLUMNS].get(str(col), {}).get(DATA_KEY_WIDTH, 72))
    height = max(20, data[DATA_KEY_ROWS].get(str(row), {}).get(DATA_KEY_HEIGHT, 20))
    styles = [
        f"width: {width}px;",
        f"height: {height}px;",
    ]
    preview = ""
    key = f"{chr(ord('A') + col - 1)}{row}"
    value = data[DATA_KEY_CELLS].get(key, "")
    if isinstance(value, dict):
        if DATA_KEY_VALUE_PREVIEW in value[DATA_KEY_VALUE]:
            preview = f'preview="{value[DATA_KEY_VALUE][DATA_KEY_VALUE_PREVIEW]}"'
            print("########", key, preview)
        if DATA_KEY_VALUE_FONT_FAMILY in value:
            styles.append(f"font-family: {value[DATA_KEY_VALUE_FONT_FAMILY]}")
        if DATA_KEY_VALUE_FONT_SIZE in value:
            styles.append(f"font-size: {value[DATA_KEY_VALUE_FONT_SIZE]}")
        if DATA_KEY_VALUE_FONT_STYLE in value:
            styles.append(f"font-style: {value[DATA_KEY_VALUE_FONT_STYLE]}")
        if DATA_KEY_VALUE_FONT_WEIGHT in value:
            styles.append(f"font-weight: {value[DATA_KEY_VALUE_FONT_WEIGHT]}")
        if DATA_KEY_VALUE_VERTICAL_ALIGN in value:
            styles.append(f"vertical-align: {value[DATA_KEY_VALUE_VERTICAL_ALIGN]}")
        if DATA_KEY_VALUE_TEXT_ALIGN in value:
            styles.append(f"text-align: {value[DATA_KEY_VALUE_TEXT_ALIGN]}")
        if DATA_KEY_VALUE_COLOR in value:
            styles.append(f"color: {value[DATA_KEY_VALUE_COLOR]}")
        if DATA_KEY_VALUE_FILL in value:
            styles.append(f"background-color: {value[DATA_KEY_VALUE_FILL]}")
        value = value[DATA_KEY_VALUE][DATA_KEY_VALUE_KIND].replace("<", "&lt;").replace(">", "&gt;")
    style = ";".join(styles)
    return f'<div id="{key}" class="cell row-{row} col-{col}" col="{col}" row="{row}" style="{style}" {preview}>{value}</div>'


def make_row_label(row, data):
    height = max(18, data[DATA_KEY_ROWS].get(str(row), {}).get(DATA_KEY_HEIGHT, 18))
    return f'<div class="row-label row-{row}" style="height:{height}px;" row="{row}">{row}</div>\n'


def make_row_header(data):
    return "".join(
        [
            f'\n<div id="row-header" class="row-header">',
                *[ make_row_label(row, data) for row in range(1, DEFAULT_ROW_COUNT + 1) ],
            '</div>\n',
        ]
    )


def make_row(row, data):
    height = max(18, data[DATA_KEY_ROWS].get(str(row), {}).get(DATA_KEY_HEIGHT, 18)) + 4
    return "\n".join(
        [
            f'\n<div id="row-{row}" class="cell-row">',
                *[ make_cell(col, row, data) for col in range(1, DEFAULT_COLUMN_COUNT + 1) ],
            '</div>\n',
        ]
    )


def make_sheet(data):
    return "".join(
        [
            "<div class='sheet' id='sheet' style='display: none;'>",
                make_column_header(data),
                make_row_header(data),
                "<div class='sheet-grid' id='sheet-grid'>",
                    "\n\n".join([ make_row(row, data) for row in range(1, DEFAULT_ROW_COUNT + 1) ]),
                "</div>",
                "<div class='blank'>",
            "</div>",
        ]
    )


def make_scripts(data):
    scripts = dict([
        (key, value[DATA_KEY_VALUE][DATA_KEY_VALUE_FORMULA].replace('`', '\\`'))
        for key, value in data[DATA_KEY_CELLS].items()
        if isinstance(value, dict)
    ])
    return "\n".join([
        "window.scripts = [",
        "\n".join(f"\t\t[`{key}`, `{script}`]," for key,script in scripts.items()),
        "\t];\n",
    ])


@app.route("/list")
def list_files():
    files = storage.list_files(request.args.get(DATA_KEY_TOKEN))
    return jsonify({ DATA_KEY_IDS: files })


def get_file(token):
    if not token:
        return "{}"
    uid = request.args.get(DATA_KEY_UID)
    if not uid:
        return jsonify({
            DATA_KEY_UID: storage.new(token),
            DATA_KEY_NAME: "Untitled Sheet",
        })
    else:
        timestamp = float(request.args.get(DATA_KEY_TIMESTAMP, "0"))
        data = storage.get_file(token, uid) or {
            DATA_KEY_NAME: "Untitled Sheet",
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
    return ai.complete(prompt, token)


@app.route("/users", methods=["GET"])
def users():
    return storage.get_users(request.args.get(DATA_KEY_TOKEN))


@app.route("/file", methods=["GET", "POST", "DELETE"])
def file():
    return FILE_ACTIONS[request.method](request.args.get(DATA_KEY_TOKEN))


@app.route("/emails", methods=["GET"])
def emails():
    response = {
        "emails": storage.get_all_emails(request.args.get(DATA_KEY_TOKEN))
    }
    return base64.b64encode(json.dumps(response).encode('utf-8')) # send base64 encoded bytes


@app.route("/embed", methods=["GET"])
def embed():
    key = request.args.get(DATA_KEY_CELL)
    uid = request.args.get(DATA_KEY_UID)
    file = storage.get_file_with_uid(uid)
    cells = file[DATA_KEY_CELLS]
    if key in cells:
        cell = cells[key]
        if cell.get(DATA_KEY_VALUE_EMBED):
            return cell[DATA_KEY_VALUE].get(DATA_KEY_VALUE_PREVIEW, "")
    return f'<html>[Chart is missing]</html>'


@app.route("/forget", methods=["GET"])
def forget():
    return { 
        "status": "OK",
        "removed": storage.forget(request.args[DATA_KEY_TOKEN]),
    }


@app.route("/logs", methods=["GET"])
def logs():
    response = storage.get_logs(
        request.args.get(DATA_KEY_TOKEN),
        request.args.get(DATA_KEY_UID),
        request.args.get(DATA_KEY_TIMESTAMP),
    )
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
