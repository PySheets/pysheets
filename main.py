from flask import Flask
from flask import jsonify
from flask import render_template
from flask import request

import ai
import base64
import json
import logging
import requests
import time
import traceback

import static.constants as constants
import static.models as models


app = Flask(__name__)


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
        "error": f"{error.__class__.__name__}: {error}",
        "status": "error",
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
    "static/timeline.py" = "timeline.py"
    "static/editor.py" = "editor.py"
    "static/api.py" = "api.py"
    "static/lsp.py" = "lsp.py"
    "static/preview.py" = "preview.py"
    "static/inventory.py" = "inventory.py"
    "static/models.py" = "models.py"
    "static/selection.py" = "selection.py"
    "static/storage.py" = "storage.py"
    "static/history.py" = "history.py"
    "static/html_maker.py" = "html_maker.py"
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
    package_names = request.args.get(constants.PYTHON_PACKAGES, "").split()
    pyodide = request.args.get(constants.PYTHON_RUNTIME) == "pyodide"
    loading = "Loading..."
    files = FILES + FILES_LTK
    runtime = RUNTIME_PYODIDE if pyodide else RUNTIME_MICROPYTHON
    interpreter = '' if pyodide else 'interpreter = "1.23.0"'
    version_interpreter = 'latest' if pyodide else '1.23.0'
    vm = "" if runtime == RUNTIME_MICROPYTHON else f" {', '.join(['Pyodide'] + package_names)}"
    packages = f"packages=[{','.join(repr(package) for package in package_names)}]" if pyodide else ""
    package_list = request.args.get(constants.PYTHON_PACKAGES, "")
    editor_width = 350
    return render_template("index.html", **locals())


@app.route("/ltk/ltk.css")
def get_ltk_css():
    return ssl_get("https://raw.githubusercontent.com/pyscript/ltk/main/ltk/ltk.css")

@app.route("/ltk/ltk.js")
def get_ltk_js():
    
    return ssl_get("https://raw.githubusercontent.com/pyscript/ltk/main/ltk/ltk.js")

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


@app.route("/complete", methods=["POST"])
def complete():
    data = get_form_data()
    prompt = data[constants.PROMPT]
    return ai.complete(prompt)


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
    app.logger.info("Load, url=%s", request.args.get(constants.URL))
    url = request.args.get(constants.URL)
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


@app.route("/<path:path>")
def send(path):
    import os
    if not os.path.exists("static/"+path):
        raise ValueError(f"Cannot return requested file: /static/{path} is missing")
    return app.send_static_file(path)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8081, debug=True)
