"""
CopyRight (c) 2024 - Chris Laffra - All Rights Reserved.

This Flask application serves as the main entry point for the PySheets application.
It sets up the Flask app, defines error handlers, and provides various routes for handling different functionality.
"""

import base64
import json
import os
import subprocess
import sys
import threading
import time
import traceback
import webbrowser

import requests

from flask import Flask
from flask import render_template
from flask import request

import ai

from static import constants

try:
    command = ["pip", "show", "pysheets-app"]
    lines = subprocess.check_output(command).decode("utf-8").split("\n")
    version_lines = [line for line in lines if line.startswith("Version:")]
    VERSION = version_lines[0].split(" ")[1]
except Exception as e:   # pylint: disable=broad-except
    VERSION = str(e)

static_folder = os.path.join(os.path.dirname(__file__), "static")
app = Flask(__name__, static_folder=static_folder)


@app.after_request
def set_response_headers(response):
    """
    Sets the response headers to enable cross-origin resource sharing (CORS) and other security-related headers.
    """
    response.headers['Cross-Origin-Embedder-Policy'] = 'require-corp'
    response.headers['X-Custom-Header'] = 'value'
    response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
    response.headers['Cross-Origin-Resource-Policy'] = 'cross-origin'
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response


@app.errorhandler(Exception)
def handle_error(error):
    """
    Handles an exception that occurs in the Flask application.
    
    Args:
        error (Exception): The exception that occurred.
    
    Returns:
        A JSON response containing the error message and status.
    """
    app.logger.error(error) # pylint: disable=no-member
    traceback.print_exc()
    return {
        "error": f"{error.__class__.__name__}: {error}",
        "status": "error",
    }


@app.errorhandler(404)
def handle_404(error): # pylint: disable=unused-argument
    """
    Handles when the requested URL was not found. 
    """
    app.logger.error("404: %s", request.path) # pylint: disable=no-member
    return "Nothing here"


PATH = os.path.join(os.path.dirname(__file__), "static")
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
    "static/views/spreadsheet.py" = "views/spreadsheet.py"
    "static/views/cell.py" = "views/cell.py"
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
    """
    Renders the main index page of the application.
    """
    package_names = request.args.get(constants.PYTHON_PACKAGES, "").split()
    pyodide = request.args.get(constants.PYTHON_RUNTIME) == "py"
    runtime = RUNTIME_PYODIDE if pyodide else RUNTIME_MICROPYTHON
    return render_template("index.html", **{
        "loading": "Loading...",
        "files": FILES + FILES_LTK,
        "version": VERSION,
        "runtime": runtime,
        "vm": "" if runtime == RUNTIME_MICROPYTHON else f" {', '.join(['Pyodide'] + package_names)}",
        "packages": f"packages=[{','.join(repr(package) for package in package_names)}]" if pyodide else "",
        "package_list": request.args.get(constants.PYTHON_PACKAGES, ""),
        "editor_width": 350,
        "path": PATH,
    })


@app.route("/ltk/ltk.css")
def get_ltk_css():
    """
    Retrieves the latest contents of the LTK CSS file from the GitHub repository.
    """
    return ssl_get("https://raw.githubusercontent.com/pyscript/ltk/main/ltk/ltk.css")


@app.route("/ltk/ltk.js")
def get_ltk_js():
    """
    Retrieves the latest contents of the LTK JavaScript file from the GitHub repository.
    """
    return ssl_get("https://raw.githubusercontent.com/pyscript/ltk/main/ltk/ltk.js")


def get_form_data():
    """
    Retrieves the form data from the current request.
    
    Returns:
        dict: The form data from the current request.
    """
    form = request.form.to_dict()
    try:
        json_data = list(form.keys())[0]
        data = json.loads(json_data)
    except Exception: # pylint: disable=broad-except
        data = form
    if isinstance(data, list):
        data = data[0]
    return data


@app.route("/complete", methods=["POST"])
def complete():
    """
    Completes a prompt by calling the AI model's completion function.
    
    Args:
        data (dict): The form data containing the prompt to complete.
    
    Returns:
        The result of the AI model's completion for the given prompt.
    """
    data = get_form_data()
    prompt = data[constants.PROMPT]
    return ai.complete(prompt)


def ssl_get(url, headers=None):
    """
    Retrieves the contents of the specified URL using an SSL connection.
    
    Args:
        url (str): The URL to retrieve.
        headers (dict, optional): Any additional headers to include in the request.
    
    Returns:
        bytes: The content of the URL, or an error message if the request fails.
    """
    try:
        return requests.get(url, verify=True, headers=headers or {}, timeout=2000).content
    except Exception as e: # pylint: disable=broad-except
        app.logger.error("ssl_get: error %s: %s", url, e)  # pylint: disable=no-member
    try:
        return requests.get(url, verify=False, headers=headers or {}, timeout=2000).content
    except Exception as e: # pylint: disable=broad-except
        app.logger.error("ssl_get: error %s: %s", url, e)  # pylint: disable=no-member
        return f"error: {e}"


def ssl_post(url, data, headers=None):
    """
    Sends an HTTP POST request to the specified URL using an SSL connection.
    
    Args:
        url (str): The URL to send the POST request to.
        data (dict): The data to include in the POST request body.
        headers (dict, optional): Any additional headers to include in the request.
    
    Returns:
        bytes: The content of the URL response, or an error message if the request fails.
    """
    try:
        return requests.post(url, data, verify=True, headers=headers or {}, timeout=2000).content
    except Exception: # pylint: disable=broad-except
        pass
    try:
        return requests.post(url, data, verify=False, headers=headers or {}, timeout=2000).content
    except Exception as e: # pylint: disable=broad-except
        return f"error: {e}"


load_cache = {}


@app.route("/load", methods=["GET", "POST"])
def load():
    """
    Retrieves the contents of a URL using an SSL connection, caching the response for up to 60 seconds.
    
    Args:
        url (str): The URL to retrieve.
    
    Returns:
        bytes: The content of the URL, or an error message if the request fails.
    """
    app.logger.info("Load, url=%s", request.args.get(constants.URL)) # pylint: disable=no-member
    url = request.args.get(constants.URL)
    if url in load_cache:
        when, response = load_cache[url]
        if time.time() - when < 60:
            print("/load: network cache hit: %s", url)
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
    print(response)
    try:
        response = base64.b64encode(response) # send base64 encoded bytes
    except Exception: # pylint: disable=broad-except
        pass
    load_cache[url] = time.time(), response
    print("/load: network cache miss", url, len(response))
    return response # send regular string


@app.route("/<path:path>")
def send(path):
    """
    Sends a file from the "static" directory.
    
    Args:
        path (str): The path to the static file to send.
    
    Raises:
        ValueError: If the requested file does not exist in the "static" directory.
    
    Returns:
        The contents of the requested static file.
    """
    return app.send_static_file(path)


def open_browser():
    """
    Opens the default web browser to the local server URL.
    
    This function is called after a short delay to automatically open the application
    in the user's default web browser when the server starts up. This provides a
    convenient way for the developer to access the running application without
    having to manually open a browser window.
    """
    webbrowser.open('http://127.0.0.1:8081')

def run_app():
    """
    Runs the PySheets application after `pip install pyscript-app` and calling `pysheets`.
    """
    if "--nolaunch" not in sys.argv:
        threading.Timer(1.5, open_browser).start()
    app.run(host='127.0.0.1', port=8081, debug=True)

if __name__ == '__main__':
    run_app()