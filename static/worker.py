print("Worker starting")

import builtins
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

from api import PySheets, edit_script

DATA_KEY_URL = "u"
DATA_KEY_TOKEN = "t"

window = pyscript.window
get = window.get
cache = {}

OriginalSession = requests.Session


class PyScriptResponse():
    def __init__(self, url, status, content):
        self.url = url
        self.status = status
        self.content = content

    def json(self):
        return json.loads(self.content)

    def text(self):
        return self.content

    def __repr__(self):
        return f"Response[{self.url}, {self.status}, {self.content[32]}...]"


class PyScriptSession(OriginalSession):
    def __init__(self):
        OriginalSession.__init__(self)

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
TOPIC_WORKER_PRINT = "worker.print"


sender = "Worker"
receiver = "Application"
subscribe = polyscript.xworker.sync.subscribe
publish = polyscript.xworker.sync.publish

orig_print = builtins.print
def worker_print(*args):
    publish(sender, receiver, TOPIC_WORKER_PRINT, f"[Worker] {' '.join(str(arg) for arg in args)}")
    orig_print(*args)
builtins.print = worker_print


js.document = pyscript.document  # patch for matplotlib inside workers

class Logger():
    def info(self, *args):
        publish(sender, receiver, TOPIC_INFO, json.dumps([ self.format(args)]))

    def error(self, *args):
        publish(sender, receiver, TOPIC_ERROR, json.dumps([ self.format(args)]))

    def format(self, *args):
        return f"Worker: {' '.join(str(arg) for arg in args)}"

logger = Logger()


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
    _globals = {}
    _globals.update(inputs)
    _globals["pyodide"] = pyodide
    _globals["pyscript"] = pyscript
    _globals["pysheets"] = PySheets(None, inputs)
    _locals = _globals
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
        pass # print(traceback.format_exc())
    try:
        return get_image_data(result.get_figure())
    except:
        pass # print(traceback.format_exc())
    try:
        return result._repr_html_()
    except:
        pass # print(traceback.format_exc())
    try:
        return get_dict_table(result)
    except:
        pass # print(traceback.format_exc())
    return str(result)



def run(data):
    job = json.loads(data)
    start = time.time()
    try:
        key, script, inputs = job
        inputs.update(cache)
        result = run_script(script, inputs)
    except:
        publish(sender, receiver, TOPIC_WORKER_RESULT, json.dumps({
            "key": key, 
            "value": None,
            "preview": "",
            "duration": time.time() - start,
            "error": traceback.format_exc(),
        }))
        return

    try:
        kind = result.__class__.__name__
        cache[key] = result
    except:
        publish(sender, receiver, TOPIC_WORKER_RESULT, json.dumps({
            "key": key, 
            "value": None,
            "preview": "",
            "duration": time.time() - start,
            "error": traceback.format_exc(),
        }))
        return

    try:
        preview = create_preview(result)
        base_kind = kind in ["int","str","float"]
        publish(sender, receiver, TOPIC_WORKER_RESULT, json.dumps({
            "key": key, 
            "duration": time.time() - start,
            "value": preview if base_kind else kind,
            "preview": "" if base_kind else preview,
            "error": None,
        }))
    except:
        publish(sender, receiver, TOPIC_WORKER_RESULT, json.dumps({
            "key": key, 
            "value": None,
            "preview": "",
            "duration": time.time() - start,
            "error": traceback.format_exc(),
        }))

polyscript.xworker.sync.handler = lambda sender, topic, data: run(data)

subscribe("Worker", TOPIC_WORKER_RUN, "pyodide-worker")

publish("Worker", "Sheet", TOPIC_WORKER_READY, repr(sys.version))