"""
CopyRight (c) 2024 - Chris Laffra - All Rights Reserved.

This module provides a worker for a PyScript-based application to run Python
code, find dependencies, and perform code completion.
"""

import json
import sys
import time
import re
import traceback

import requests

import api
import lsp
import constants
import ltk

import js # type: ignore    pylint: disable=import-error
import polyscript # type: ignore    pylint: disable=import-error
import pyodide # type: ignore    pylint: disable=import-error
import pyscript # type: ignore    pylint: disable=import-error

get = ltk.window.get
cache = { }
results = { }
OriginalSession = requests.Session
inputs_cache = {}


class PyScriptResponse():
    """
    Represents a response from a PyScript-based HTTP request.
    
    This class encapsulates the response data from a PyScript-based HTTP request,
    including the URL, status code, and response content.
    
    Attributes:
        url (str): The URL of the request.
        status (int): The HTTP status code of the response.
        content (str): The content of the response.
    
    Methods:
        json(): Parses the response content as JSON and returns the resulting object.
        text(): Returns the response content as a string.
    """
    def __init__(self, url, status, content):
        self.url = url
        self.status = status
        self.content = content

    def json(self):
        """
        Parses the response content as JSON and returns the resulting object.
        """
        return json.loads(self.content)

    def text(self):
        """
        Returns the response content as a string.
        """
        return self.content

    def __repr__(self):
        return f"Response[{self.url}, {self.status}, {self.content[32]}...]"


class PyScriptSession(OriginalSession):
    """
    Represents a custom session class that overrides the default `requests.Session`
    class to handle HTTP requests using PyScript's `window.XMLHttpRequest`.
    
    This class is used to make HTTP requests from within a PyScript-based worker environment,
    where the standard `requests` library may not be available or may not work as expected.
    
    The `request()` method of this class sends an HTTP request using the `window.XMLHttpRequest`
    object, with the URL modified to include the `constants.URL` parameter. The response
    is then wrapped in a `PyScriptResponse` object and returned.
    """

    def request( self, method, url, data=None, headers=None, **vargs):  #pylint: disable=arguments-differ,unused-argument
        xhr = ltk.window.XMLHttpRequest.new()
        xhr.open(method, f"load?{constants.URL}={url}", False)
        xhr.setRequestHeader("Authorization", (headers or self.headers).get("Authorization"))
        xhr.send(data)
        return PyScriptResponse(url, xhr.status, xhr.responseText)


requests.Session = PyScriptSession
requests.session = PyScriptSession



def setup():
    """
    Sets up the worker.
    """
    import builtins # pylint: disable=import-outside-toplevel
    if js.document is ltk.window.document:
        return
    js.document = ltk.window.document  # patch for matplotlib inside workers

    def worker_print(*args, file=None, end=""): # pylint: disable=unused-argument
        polyscript.xworker.sync.publish(
            "Worker",
            "Application",
            constants.TOPIC_WORKER_PRINT, f"[Worker] {' '.join(str(arg) for arg in args)}"
        )

    builtins.print = worker_print

completion_cache = {}

def get_image_data(figure):
    """
    Converts a Matplotlib figure to an HTML image representation.
    
    Args:
        figure (matplotlib.figure.Figure): The Matplotlib figure to convert.
    
    Returns:
        str: An HTML string representing the figure as an image.
    """
    from io import BytesIO # pylint: disable=import-outside-toplevel
    import base64 # pylint: disable=import-outside-toplevel

    #
    # Use the built-in agg backend.
    # This reduces rendering time for plots from ~6s to 70ms
    #
    matplotlib.use("agg")
    bytes_io = BytesIO()
    figure.set_edgecolor("#BBB")
    figure.savefig(bytes_io, bbox_inches="tight", format="png")
    bytes_io.seek(0)
    matplotlib.pyplot.close(figure)
    encoded = base64.b64encode(bytes_io.read())
    return f"""<img src="data:image/png;base64,{encoded.decode('utf-8')}">"""


def create_preview(result): # pylint: disable=too-many-return-statements
    """
    Creates a preview of the given result object.
    
    The preview can be in the form of an HTML representation, an image, or a
    string representation, depending on the type of the result object.
    
    Args:
        result: The result object to create a preview for.
    
    Returns:
        A string representation of the preview.
    """
    if str(result) == "DataFrame":
        return str(result)
    if "plotly" in str(type(result)):
        try:
            import plotly # pylint: disable=import-outside-toplevel
            html = plotly.io.to_html(result, default_width=500, default_height=500)
            return html
        except ImportError:
            pass
    try:
        return get_image_data(result)
    except Exception: # pylint: disable=broad-except
        pass  # print(traceback.format_exc())
    try:
        return get_image_data(result.get_figure())
    except Exception: # pylint: disable=broad-except
        pass  # print(traceback.format_exc())
    try:
        return result._repr_html_() # pylint: disable=protected-access
    except Exception: # pylint: disable=broad-except
        pass  # print(traceback.format_exc())
    try:
        return api.get_dict_table(result)
    except Exception: # pylint: disable=broad-except
        pass  # print(traceback.format_exc())
    return str(result)


def get_visualization_prompt(key, columns):
    """
    Generates a prompt for visualizing a dataframe as a matplotlib figure.
    
    Args:
        key (str): The key used to store the dataframe in the cache.
        columns (list[str]): The column names of the dataframe.
    
    Returns:
        str: A prompt that can be used to generate a visualization of the dataframe.
    """
    return f"""
Visualize a dataframe as a matplotlib figure in the code and call it "figure".
I already have it stored in a variable called "{key}".
Here are the column names for the dataframe:
{columns}
    """.strip()


def generate_completion(key, prompt):
    """
    Generates a completion for a given prompt using an external API.
    
    Args:
        key (str): A unique key to identify the completion request.
        prompt (str): The prompt to generate the completion for.
    
    Returns:
        None. The completion result is published to a message queue for further processing.
    """
    data = {constants.PROMPT: prompt}
    start = time.time()
    url = "complete"

    def success(response, status, xhr): # pylint: disable=unused-argument
        data = json.loads(ltk.window.JSON.stringify(response))
        if data.get(constants.STATUS, "ok") == "error":
            text = data[constants.ERROR]
        else:
            text = data["text"].replace("plt.show()", "figure")
            completion_cache[prompt] = data
        polyscript.xworker.sync.publish(
            "Worker",
            "Application",
            constants.TOPIC_WORKER_COMPLETION,
            json.dumps(
                {
                    "key": key,
                    "prompt": prompt,
                    "text": text,
                    "duration": time.time() - start,
                }
            ),
        )

    def error(data, status, xhr): # pylint: disable=unused-argument
        polyscript.xworker.sync.publish(
            "Worker",
            "Application",
            constants.TOPIC_WORKER_COMPLETION,
            json.dumps(
                {
                    "key": key,
                    "prompt": prompt,
                    "text": data,
                    "duration": time.time() - start,
                }
            ),
        )

    ltk.window.ltk_post(
        url,
        data,
        ltk.proxy(success),
        None,
        ltk.proxy(error),
    )


def run_in_worker(script):
    """
    Executes a Python script in the worker context, with access to the global
    cache and results dictionaries, as well as the pyodide, pyscript, and pysheets modules.
    
    The script is first intercepted to ensure the last expression is returned
    as the result. The script is then executed in the _globals environment,
    which includes the cache and results dictionaries, as well as the pyodide,
    pyscript, and pysheets modules. The result of the script execution is returned.
    """

    _globals = {}
    _globals.update(cache)
    _globals.update(results)
    _globals["pyodide"] = pyodide
    _globals["pyscript"] = pyscript
    _globals["pysheets"] = sys.modules["pysheets"] = api.PySheets(None, cache)
    _locals = _globals
    script = api.intercept_last_expression(script)
    # print("Executing script:", script)
    exec(script, _globals, _locals) # pylint: disable=exec-used
    return _locals["_"]


def handle_run(data): # pylint: disable=too-many-locals
    """
    Executes a Python script in the worker context, with access to the global
    cache and results dictionaries, as well as the pyodide, pyscript, and pysheets modules.
    """
    start = time.time()
    key, script, inputs = data
    cache.update(inputs)
    try:
        result = run_in_worker(script)
    except Exception:  # pylint: disable=broad-except
        tb = traceback.format_exc()
        try:
            lines = tb.strip().split("\n")
            line = [line for line in lines if "<module>" in line][0]
            lineno = int(re.sub("[^0-9]", "", line))
            error = f"Line {lineno}: {lines[-1]} - {tb}"
        except Exception as formatting_error: # pylint: disable=broad-except
            error = str(formatting_error)
            lineno = 1

        ltk.window.console.orig_log("error", lineno, error, tb)

        polyscript.xworker.sync.publish(
            "Worker",
            "Application",
            ltk.pubsub.TOPIC_WORKER_RESULT,
            json.dumps(
                {
                    "key": key,
                    "value": None,
                    "preview": "",
                    "duration": time.time() - start,
                    "lineno": lineno,
                    "error": error,
                    "traceback": tb,
                }
            ),
        )
        return

    try:
        kind = result.__class__.__name__
        cache[key] = results[key] = result
    except Exception:  # pylint: disable=broad-exception-caught
        polyscript.xworker.sync.publish(
            "Worker",
            "Application",
            ltk.pubsub.TOPIC_WORKER_RESULT,
            json.dumps(
                {
                    "key": key,
                    "script": script,
                    "value": None,
                    "preview": "",
                    "duration": time.time() - start,
                    "error": f"Worker result error: {type(error)}:{error}",
                    "traceback": traceback.format_exc(),
                }
            ),
        )
        return

    prompt = (
        get_visualization_prompt(key, results[key].columns.values)
        if kind == "DataFrame"
        else ""
    )

    try:
        preview = create_preview(result)
        base_kind = kind in ["int", "str", "float"]
        polyscript.xworker.sync.publish(
            "Worker",
            "Application",
            ltk.pubsub.TOPIC_WORKER_RESULT,
            json.dumps(
                {
                    "key": key,
                    "duration": time.time() - start,
                    "script": script,
                    "value": preview if base_kind else kind,
                    "preview": "" if base_kind else preview,
                    "prompt": prompt,
                    "error": (
                        preview
                        if kind == "str" and preview.startswith("ERROR:")
                        else None
                    ),
                }
            ),
        )
    except Exception as e: # pylint: disable=broad-exception-caught
        polyscript.xworker.sync(
            "Worker",
            "Application",
            ltk.pubsub.TOPIC_WORKER_RESULT,
            json.dumps(
                {
                    "key": key,
                    "value": None,
                    "script": script,
                    "preview": "",
                    "duration": time.time() - start,
                    "error": f"Worker preview error: {type(e)}:{e}",
                    "traceback": traceback.format_exc(),
                }
            ),
        )


def handle_set_cells(cells):
    """
    Handle a request from the api to set a collection of cells
    """
    for key, value in cells.items():
        cache[key] = value


def handle_request(sender, topic, request): # pylint: disable=unused-argument
    """
    Handles various requests received by the worker process, including:
    - Generating code completions
    - Finding inputs for a given script
    - Running a script
    """

    try:
        data = json.loads(request)
        if topic == constants.TOPIC_WORKER_COMPLETE:
            generate_completion(data["key"], data["prompt"])
        elif topic == constants.TOPIC_WORKER_FIND_INPUTS:
            key, script = data["key"], data["script"]
            inputs = inputs_cache.get(script, None)
            try:
                if inputs is None:
                    inputs = api.find_inputs(script)
                inputs_cache[script] = inputs
                polyscript.xworker.sync.publish(
                    "Worker",
                    "Application",
                    constants.TOPIC_WORKER_INPUTS,
                    json.dumps(
                        {
                            "key": key,
                            "inputs": inputs,
                        }
                    ),
                )
            except Exception as e: # pylint: disable=broad-exception-caught
                polyscript.xworker.sync.publish(
                    "Worker",
                    "Application",
                    constants.TOPIC_WORKER_INPUTS,
                    json.dumps(
                        {
                            "key": key,
                            "error": str(e),
                            "inputs": [],
                        }
                    ),
                )
        elif topic == constants.TOPIC_WORKER_CODE_COMPLETE:
            try:
                text, line, ch = data
                completions = lsp.complete_python(text, line, ch, cache, results)
                polyscript.xworker.sync.publish(
                    "Worker",
                    "Application",
                    constants.TOPIC_WORKER_CODE_COMPLETION,
                    json.dumps(completions),
                )
            except Exception: # pylint: disable=broad-exception-caught
                pass
        elif topic == ltk.pubsub.TOPIC_WORKER_RUN:
            handle_run(data)
        elif topic == constants.TOPIC_API_SET_CELLS:
            handle_set_cells(data)
        else:
            print("Error: Unexpected topic request", topic)
    except Exception as e: # pylint: disable=broad-exception-caught
        print("Cannot handle request", request, e)


polyscript.xworker.sync.handler = handle_request

polyscript.xworker.sync.subscribe(
    "Worker", ltk.TOPIC_WORKER_RUN, "pyodide-worker"
)
polyscript.xworker.sync.subscribe(
    "Worker", constants.TOPIC_WORKER_COMPLETE, "pyodide-worker"
)
polyscript.xworker.sync.subscribe(
    "Worker", constants.TOPIC_WORKER_FIND_INPUTS, "pyodide-worker"
)
polyscript.xworker.sync.subscribe(
    "Worker", constants.TOPIC_WORKER_CODE_COMPLETE, "pyodide-worker"
)
polyscript.xworker.sync.subscribe(
    "Worker", constants.TOPIC_API_SET_CELLS, "pyodide-worker"
)
polyscript.xworker.sync.publish(
    "Worker", "Sheet", ltk.pubsub.TOPIC_WORKER_READY, repr(sys.version)
)

try:
    import pandas               # pylint: disable=unused-import,wrong-import-position,import-error
    import matplotlib           # pylint: disable=wrong-import-position,import-error
    import matplotlib.pyplot    # pylint: disable=wrong-import-position,import-error
except (TypeError, ModuleNotFoundError, ImportError):
    pass # ignore load error on Github Actions build

setup()
