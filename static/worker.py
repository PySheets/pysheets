import builtins
import json
import sys
import time
import traceback
import re
import requests

import js # type: ignore
import polyscript # type: ignore
import pyodide # type: ignore
import pyscript # type: ignore

try:
    from api import edit_script, PySheets, get_dict_table
except:
    pass

DATA_KEY_URL = "u"
DATA_KEY_TOKEN = "t"
DATA_KEY_PROMPT = "v"
DATA_KEY_COMPLETION = "w"

window = pyscript.window
get = window.get
cache = {}
token = window.localStorage.getItem(DATA_KEY_TOKEN)

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
TOPIC_WORKER_COMPLETION = "worker.completion"


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

completions = {}

class Logger():
    def info(self, *args):
        publish(sender, receiver, TOPIC_INFO, json.dumps([ self.format(args)]))

    def error(self, *args):
        publish(sender, receiver, TOPIC_ERROR, json.dumps([ self.format(args)]))

    def format(self, *args):
        return f"Worker: {' '.join(str(arg) for arg in args)}"

logger = Logger()



def run_in_worker(script, inputs):
    _globals = {}
    _globals.update(inputs)
    _globals["pyodide"] = pyodide
    _globals["pyscript"] = pyscript
    _globals["pysheets"] = PySheets(None, inputs)
    _locals = _globals
    exec(script, _globals, _locals)
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


def normalize_dataframe(dataframe):
    return re.sub("[0-9][0-9.]+", "1", dataframe)


def complete(key, kind):
    if kind != "DataFrame":
        return
    dataframe = normalize_dataframe(str(cache[key]))
    if dataframe in completions:
        return completions[dataframe]
    generate_completion(key, kind, dataframe)


def generate_completion(key, kind, dataframe):
    data = {
        DATA_KEY_PROMPT: f"""
            Given the following dataframe, show the Python code to visualize.
            Include an explanation at the start, formatted as a Python comment.
            Assume I have the dataframe stored already in a variable called "{key}".
            Create a matplotlib figure in the code and call it "figure".

            {dataframe}
        """
    }
    start = time.time()
    url = f"complete?{DATA_KEY_TOKEN}={window.getToken()}"
    def success(data, status, xhr):
        completion = json.loads(window.JSON.stringify(data))
        text = completion["text"].replace("plt.show()", "figure")
        completions[dataframe] = completion
        publish(sender, receiver, TOPIC_WORKER_COMPLETION, json.dumps({
            "key": key, 
            "text": text,
            "duration": time.time() - start,
        }))
    window.ltk_post(url, json.dumps(data), pyodide.ffi.create_proxy(success), "json")


def run(data):
    job = json.loads(data)
    start = time.time()
    try:
        key, script, inputs = job
        inputs.update(cache)
        result = run_in_worker(script, inputs)
    except Exception as e:
        import re
        tb = traceback.format_exc()
        try:
            lines = re.sub('Traceback.*<string>"," line ', "", tb).split("\n")
            line = int(lines[3].split(" ")[-1])
            stack = "\n".join(lines[4:])
            error = f"{lines[-2]}: At line {line + 1} {stack}"
        except Exception as e:
            print("oops", e)
            error = tb
        publish(sender, receiver, TOPIC_WORKER_RESULT, json.dumps({
            "key": key, 
            "value": None,
            "preview": "",
            "duration": time.time() - start,
            "error": error,
        }))
        return

    try:
        kind = result.__class__.__name__
        cache[key] = result
    except:
        publish(sender, receiver, TOPIC_WORKER_RESULT, json.dumps({
            "key": key, 
            "script": script,
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
            "script": script,
            "value": preview if base_kind else kind,
            "preview": "" if base_kind else preview,
            "error": None,
        }))
        complete(key, kind)
    except:
        publish(sender, receiver, TOPIC_WORKER_RESULT, json.dumps({
            "key": key, 
            "value": None,
            "script": script,
            "preview": "",
            "duration": time.time() - start,
            "error": traceback.format_exc(),
        }))

polyscript.xworker.sync.handler = lambda sender, topic, data: run(data)

subscribe("Worker", TOPIC_WORKER_RUN, "pyodide-worker")

publish("Worker", "Sheet", TOPIC_WORKER_READY, repr(sys.version))