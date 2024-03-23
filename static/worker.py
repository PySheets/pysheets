import base64
import io
import json
import sys
import time
import traceback

import js # type: ignore
import polyscript # type: ignore
import pyodide # type: ignore
import pyscript # type: ignore
import json
import pyscript # type: ignore
import requests


from constants import *

window = pyscript.window
get = window.get
cache = {}

OriginalSession = requests.Session


class PyScriptResponse():
    def __init__(self, url, status, content):
        self.url = url
        self.status = status
        self.content = content
        print(self)

    def json(self):
        return json.loads(self.content)

    def text(self):
        return self.content

    def __repr__(self):
        return f"Response[{self.url}, {self.status}, {self.content[32]}...]"


class PyScriptSession(OriginalSession):
    def __init__(self):
        OriginalSession.__init__(self)
        print("NEW Session", self)

    def request(self,
        method,
        url,
        params=None,
        data=None,
        headers=None,
        cookies=None,
        files=None,
        auth=None,
        timeout=None,
        allow_redirects=True,
        proxies=None,
        hooks=None,
        stream=None,
        verify=None,
        cert=None,
        json=None,
    ):
        xhr = window.XMLHttpRequest.new()
        xhr.open(method, f"load?{DATA_KEY_TOKEN}={window.getToken()}&{DATA_KEY_URL}={url}", False)
        xhr.setRequestHeader("Authorization", (headers or self.headers).get("Authorization"))
        xhr.send(data)
        return PyScriptResponse(url, xhr.status, xhr.responseText)


requests.Session = PyScriptSession
requests.session = lambda: PyScriptSession()

import urllib.request

def load_with_trampoline(url):
    def get(url):
        xhr = window.XMLHttpRequest.new()
        xhr.open("GET", url, False)
        xhr.send(None)
        if xhr.status != 200:
            raise IOError(f"HTTP Error: {xhr.status} for {url}")
        return xhr.responseText

    if url and url[0] == "/":
        url = f"https://{window.location.host}{url}"
    elif not url.startswith("https://"):
        url = f"{window.location.href}{url}"
    bytes_or_string = get(window.addToken(f"/load?u={window.encodeURIComponent(url)}"))
    print("load =>", type(bytes_or_string), bytes_or_string[:32])
    try:
        response = base64.b64decode(bytes_or_string)
    except:
        response = bytes_or_string
    try:
        return json.loads(response)
    except:
        return response


def urlopen(url, data=None, timeout=3, *, cafile=None, capath=None, cadefault=False, context=None):
    try:
        content = load_with_trampoline(url)
        print("urlopen", url, "=>", type(content), len(content))
        try:
            return io.BytesIO(content)
        except:
            return io.StringIO(content)
    except Exception as e:
        print("urlopen", "error", e)

urllib.request.urlopen = urlopen


TOPIC_INFO = "log.info"
TOPIC_DEBUG = "log.debug"
TOPIC_ERROR = "log.error"
TOPIC_WARNING = "log.warning"
TOPIC_CRITICAL = "log.critical"

TOPIC_REQUEST = "app.request"
TOPIC_RESPONSE = "app.response"
TOPIC_WORKER_READY = "worker.ready"
TOPIC_WORKER_RUN = "worker.run"
TOPIC_WORKER_RESULT = "worker.result"


sender = "Worker"
receiver = "Application"
subscribe = polyscript.xworker.sync.subscribe
publish = polyscript.xworker.sync.publish


js.document = pyscript.document  # patch for matplotlib inside workers

class Logger():
    def info(self, *args):
        publish(sender, receiver, TOPIC_INFO, json.dumps([ self.format(args)]))

    def error(self, *args):
        publish(sender, receiver, TOPIC_ERROR, json.dumps([ self.format(args)]))

    def format(self, *args):
        return f"Worker: {' '.join(str(arg) for arg in args)}"

logger = Logger()

def get_col_row(key):
    for index, c in enumerate(key):
        if c.isdigit():
            row = int(key[index:])
            column = ord(key[index - 1]) - ord('A') + 1
            return (column, row)


def get_dict_table(result):
    return "".join([
        "<table border='1' class='dataframe'>",
            "<thead>",
                "<tr><th>key</th><th>value</th></tr>",
            "</thead>",
            "<tbody>",
                "".join(f"<tr><td>{key}</td><td>{str(value)}</td></tr>" for key, value in result.items()),
            "</thead>",
        "</table>",
    ])



def run_script(script, inputs):

    def edit_script(script): # TODO: use ast to parse script
        lines = script.strip().split("\n")
        lines[-1] = f"_={lines[-1]}"
        return "\n".join(lines)

    class PySheets():

        @classmethod
        def sheet(cls, selection, headers=True):
            import pandas
            start, end = selection.split(":")
            start_col, start_row = get_col_row(start)
            end_col, end_row = get_col_row(end)
            data = {}
            for col in range(start_col, end_col + 1):
                keys = [
                    f"{chr(ord('A') + col - 1)}{row}"
                    for row in range(start_row, end_row + 1)
                ]
                values = [ inputs[ key ] for key in keys ]
                header = values.pop(0) if headers else f"col-{col}"
                data[header] = values
            return pandas.DataFrame.from_dict(data)

        @classmethod
        def load(cls, url):
            return load_with_trampoline(url)

    _globals = {}
    _globals.update(inputs)
    _globals["pyodide"] = pyodide
    _globals["pyscript"] = pyscript
    _globals["pysheets"] = PySheets()
    _locals = {}
    exec(edit_script(script), _globals, _locals)
    return _locals["_"]


def get_image_data(figure):
    from io import BytesIO
    import base64
    import matplotlib

    #
    # Use the built-in agg backend.
    # This reduces rendering time for plots from ~6s to 70ms 
    #
    matplotlib.use('agg')
    bytes = BytesIO()
    figure.set_size_inches(4, 3)
    figure.set_edgecolor("#BBB")
    figure.savefig(bytes, bbox_inches="tight", format='png')
    bytes.seek(0)
    matplotlib.pyplot.close(figure)
    bytes = base64.b64encode(bytes.read())
    return f"""<img src="data:image/png;base64,{bytes.decode('utf-8')}">"""


def create_preview(result):
    if str(result) == "DataFrame":
        return str(result)
    try:
        return get_image_data(result)
    except:
        pass
    try:
        return get_image_data(result.get_figure())
    except:
        pass
    try:
        return result._repr_html_()
    except:
        pass
    try:
        return get_dict_table(result)
    except:
        pass
    return str(result)



def run(job):
    start = time.time()
    try:
        key, script, inputs = job
        inputs.update(cache)
        result = run_script(script, inputs)
    except Exception as e:
        publish(sender, receiver, TOPIC_WORKER_RESULT, json.dumps([key, time.time() - start, str(e), traceback.format_exc()]))
        return

    try:
        kind = result.__class__.__name__
        cache[key] = result
    except Exception as e:
        publish(sender, receiver, TOPIC_WORKER_RESULT, json.dumps([key, time.time() - start, str(e), traceback.format_exc()]))
        return

    try:
        preview = create_preview(result)
        publish(sender, receiver, TOPIC_WORKER_RESULT, json.dumps([key, time.time() - start, kind, preview]))
    except Exception as e:
        publish(sender, receiver, TOPIC_WORKER_RESULT, json.dumps([key, time.time() - start, str(e), traceback.format_exc()]))


 
polyscript.xworker.sync.handler = lambda sender, topic, data: run(json.loads(data))

subscribe("Worker", TOPIC_WORKER_RUN, "pyodide-worker")
publish("Worker", "DAG", TOPIC_WORKER_READY, repr(sys.version))