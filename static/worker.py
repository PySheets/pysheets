import constants
import json
import ltk
import sys
import time
import requests

import js # type: ignore
import polyscript # type: ignore
import pyodide # type: ignore
import pyscript # type: ignore

window = pyscript.window
get = window.get
cache = { }
results = { }
OriginalSession = requests.Session
inputs_cache = {}



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
        xhr.open(method, f"load?{constants.URL}={url}", False)
        xhr.setRequestHeader("Authorization", (headers or self.headers).get("Authorization"))
        xhr.send(data)
        return PyScriptResponse(url, xhr.status, xhr.responseText)


requests.Session = PyScriptSession
requests.session = lambda: PyScriptSession()

sender = "Worker"
receiver = "Application"
subscribe = polyscript.xworker.sync.subscribe
publish = polyscript.xworker.sync.publish

def setup():
    import builtins
    if js.document is pyscript.document:
        return
    js.document = pyscript.document  # patch for matplotlib inside workers
    def worker_print(*args, file=None, end=""):
        publish(sender, receiver, constants.TOPIC_WORKER_PRINT, f"[Worker] {' '.join(str(arg) for arg in args)}")
    builtins.print = worker_print

completion_cache = {}

class Logger():
    def info(self, *args):
        publish(sender, receiver, constants.TOPIC_INFO, json.dumps([ self.format(args)]))

    def error(self, *args):
        publish(sender, receiver, constants.TOPIC_ERROR, json.dumps([ self.format(args)]))

    def format(self, *args):
        return f"Worker: {' '.join(str(arg) for arg in args)}"

logger = Logger()




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
    figure.set_edgecolor("#BBB")
    figure.savefig(bytes, bbox_inches="tight", format='png')
    bytes.seek(0)
    matplotlib.pyplot.close(figure)
    bytes = base64.b64encode(bytes.read())
    return f"""<img src="data:image/png;base64,{bytes.decode('utf-8')}">"""


def create_preview(result):
    import api
    if str(result) == "DataFrame":
        return str(result)
    if "plotly" in str(type(result)):
        try:
            import plotly
            html = plotly.io.to_html(result, default_width=500, default_height=500)
            return html
        except:
            pass
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
        return api.get_dict_table(result)
    except:
        pass # print(traceback.format_exc())
    return str(result)


def get_visualization_prompt(key, columns):
    return f"""
Visualize a dataframe as a matplotlib figure in the code and call it "figure".
I already have it stored in a variable called "{key}".
Here are the column names for the dataframe:
{columns}
    """.strip()


def generate_completion(key, prompt):
    data = { constants.PROMPT: prompt }
    start = time.time()
    url = f"complete"

    def success(response, status, xhr):
        data = json.loads(window.JSON.stringify(response))
        if data.get(constants.STATUS, "ok") == "error":
            text = data[constants.ERROR]
        else:
            text = data["text"].replace("plt.show()", "figure")
            completion_cache[prompt] = data
        publish(sender, receiver, constants.TOPIC_WORKER_COMPLETION, json.dumps({
            "key": key, 
            "prompt": prompt,
            "text": text,
            "duration": time.time() - start,
        }))

    def error(data, status, xhr):
        publish(sender, receiver, constants.TOPIC_WORKER_COMPLETION, json.dumps({
            "key": key, 
            "prompt": prompt,
            "text": data,
            "duration": time.time() - start,
        }))

    window.ltk_post(
        url, 
        data, 
        pyodide.ffi.create_proxy(success), 
        None,
        pyodide.ffi.create_proxy(error)
    )


def run_in_worker(key, script):
    import api
    _globals = {}
    _globals.update(cache)
    _globals.update(results)
    _globals["pyodide"] = pyodide
    _globals["pyscript"] = pyscript
    _globals["pysheets"] = sys.modules["pysheets"] = api.PySheets(None, cache)
    _locals = _globals
    script = api.intercept_last_expression(script)
    # print("Executing script:", script)
    exec(script, _globals, _locals)
    return _locals["_"]


def run(data):
    start = time.time()
    try:
        key, script, inputs = data
        cache.update(inputs)
        result = run_in_worker(key, script)
    except Exception as e:
        import traceback
        import re
        tb = traceback.format_exc()
        try:
            lines = tb.strip().split("\n")
            line = [line for line in lines if "<string>" in line][0]
            lineno = int(re.sub("[^0-9]", "", line))
            error = f"At line {lineno + 1}: {lines[-1]} - {tb}"
        except Exception as e:
            error = str(e)
            lineno = 1
        publish(sender, receiver, ltk.pubsub.TOPIC_WORKER_RESULT, json.dumps({
            "key": key, 
            "value": None,
            "preview": "",
            "duration": time.time() - start,
            "lineno": lineno,
            "error": error,
            "traceback": tb,
        }))
        return

    try:
        kind = result.__class__.__name__
        cache[key] = results[key] = result
    except Exception as e:
        import traceback
        publish(sender, receiver, ltk.pubsub.TOPIC_WORKER_RESULT, json.dumps({
            "key": key, 
            "script": script,
            "value": None,
            "preview": "",
            "duration": time.time() - start,
            "error": f"Worker result error: {type(error)}:{error}",
            "traceback": traceback.format_exc()
        }))
        return

    prompt = get_visualization_prompt(key, results[key].columns.values) if kind == "DataFrame" else ""

    try:
        preview = create_preview(result)
        base_kind = kind in ["int","str","float"]
        publish(sender, receiver, ltk.pubsub.TOPIC_WORKER_RESULT, json.dumps({
            "key": key, 
            "duration": time.time() - start,
            "script": script,
            "value": preview if base_kind else kind,
            "preview": "" if base_kind else preview,
            "prompt": prompt,
            "error": preview if kind == "str" and preview.startswith("ERROR:") else None,
        }))
    except Exception as e:
        import traceback
        publish(sender, receiver, ltk.pubsub.TOPIC_WORKER_RESULT, json.dumps({
            "key": key, 
            "value": None,
            "script": script,
            "preview": "",
            "duration": time.time() - start,
            "error": f"Worker preview error: {type(e)}:{e}",
            "traceback": traceback.format_exc()
        }))

def handle_request(sender, topic, request):
    setup()
    import api
    import lsp
    try:
        data = json.loads(request)
        if topic == constants.TOPIC_WORKER_COMPLETE:
            generate_completion(data["key"], data["prompt"])
        elif topic == constants.TOPIC_WORKER_FIND_INPUTS:
            key, script = data["key"], data["script"]
            inputs = inputs_cache.get(script, None)
            if inputs is None:
                inputs = api.find_inputs(script)
            inputs_cache[script] = inputs
            publish(sender, receiver, constants.TOPIC_WORKER_INPUTS, json.dumps({
                "key": key,
                "inputs": inputs,
            }))
        elif topic == constants.TOPIC_WORKER_CODE_COMPLETE:
            text, line, ch = data
            completions = lsp.complete_python(text, line, ch, cache, results)
            publish(sender, receiver, constants.TOPIC_WORKER_CODE_COMPLETION, json.dumps(completions))
        elif topic == ltk.pubsub.TOPIC_WORKER_RUN:
            run(data)
        else:
            print("Error: Unexpected topic request", topic)
    except Exception as e:
        import traceback
        print("Error: Handling topic", topic)
        traceback.print_exc()

polyscript.xworker.sync.handler = handle_request

subscribe("Worker", ltk.TOPIC_WORKER_RUN, "pyodide-worker")
subscribe("Worker", constants.TOPIC_WORKER_COMPLETE, "pyodide-worker")
subscribe("Worker", constants.TOPIC_WORKER_FIND_INPUTS, "pyodide-worker")
subscribe("Worker", constants.TOPIC_WORKER_CODE_COMPLETE, "pyodide-worker")

publish("Worker", "Sheet", ltk.pubsub.TOPIC_WORKER_READY, repr(sys.version))

import pandas
import matplotlib.pyplot
