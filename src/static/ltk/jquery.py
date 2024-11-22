"""
LTK - Copyright 2024 - All Rights Reserved - chrislaffra.com - See LICENSE
"""

import json
import sys
import time

import pyscript # pylint: disable=import-error
from pyscript import window # pylint: disable=import-error
try:
    import pyodide # pylint: disable=import-error
except:
    pass


__all__ = [
    "parse_int", "parse_float", "local_storage", "find", "create", "find_list", "to_js",
    "to_py", "schedule", "repeat", "cancel", "get", "delete", "get_time", "post", "async_proxy",
    "observe", "proxy", "get_url_parameter", "set_url_parameter", "push_state", "inject_script",
    "inject_css", "callback",
]


PYODIDE = "Clang" in sys.version
MICROPYTHON = not PYODIDE


def _fix_time_on_micropython():
    if MICROPYTHON:
        class MonkeyPatchedTimeModuleForMicroPython:
            """ Monkey patches the time module on MicroPython. """
        clone = MonkeyPatchedTimeModuleForMicroPython()
        for key in dir(time):
            setattr(clone, key, getattr(time, key))
        setattr(clone, "time", lambda: window.Date.new().getTime() / 1000)
        sys.modules["time"] = clone


parse_int = window.parseInt
parse_float = window.parseFloat
local_storage = window.localStorage
timers = {}


def find(selector):
    """ Returns a jQuery object for the given selector. """
    is_html = isinstance(selector, str) and selector.strip().startswith("<")
    has_newline = isinstance(selector, str) and "\n" in selector
    if has_newline or is_html:
        try:
            warning = f"Unexpect jQuery selector '{selector}'"
            if is_html:
                warning += ". To generate HTML, use ltk.create(...)"
            print(f"Warning: {warning}")
            import traceback # pylint: disable=import-outside-toplevel
            traceback.print_stack()
        except: # pylint: disable=bare-except
            pass
    return window.jQuery(selector)


def create(html):
    """ Creates a jQuery object from the given HTML. """
    html = html.strip()
    if not html or html[0] != "<":
        try:
            warning = f"A jQuery html fragment should start with '<', not '{html}'"
            print(f"Warning: {warning}")
            import traceback # pylint: disable=import-outside-toplevel
            traceback.print_stack()
        except: # pylint: disable=bare-except
            pass
    return window.jQuery(html)


KB = 1024
MB = KB * KB
GB = MB * MB


def to_human(byte_count):
    """ Returns a human-readable string for the given byte count. """
    if byte_count > GB:
        return f"{round(byte_count / GB)}GB"
    if byte_count > MB:
        return f"{round(byte_count / MB)}MB"
    if byte_count > KB:
        return f"{round(byte_count / KB)}KB"
    return f"{byte_count}"


def callback(function):
    """ A decorator a function that wraps the given function. """
    def inner(*args, **argv):
        return function(*args, **argv)
    return proxy(inner)


def get_time():
    """ Returns the current time in seconds since the epoch. """
    return window.get_time() / 1000


def find_list(selector, parent=None):
    """ Returns a list of jQuery objects for the given selector. """
    elements = parent.find(selector) if parent else window.jQuery(selector)
    return [ elements.eq(n) for n in range(elements.length) ]


def dumps(data):
    """ Returns a JSON string for the given data. """
    try:
        def encode(obj):
            try:
                return obj.__class__.__name__
            except: # pylint: disable=bare-except
                return None
        return json.dumps(data, default=encode)
    except: # pylint: disable=bare-except
        return json.dumps(data)


def to_js(python_object):
    """ Returns a JavaScript object for the given Python object. """
    if python_object.__class__.__name__ == "jsobj":
        return python_object
    return window.to_js(dumps(python_object))


def to_py(jsobj):
    """ Returns a Python object for the given JavaScript object. """
    try:
        return jsobj.to_py()
    except: # pylint: disable=bare-except
        try:
            return json.loads(window.to_py(jsobj)) # Micropython has no built-in to_py
        except: # pylint: disable=bare-except
            return str(jsobj)


def schedule(python_function, key, timeout_seconds=0):
    """
    Schedules the given Python function to run after the given timeout.
    If a function with the same key is already scheduled, it will be cancelled
    and a new scheduling is performed.
    """
    if not python_function:
        raise ValueError(f"schedule: Expecting a function, not {python_function}")
    if not isinstance(key, str):
        raise ValueError(f"schedule: key should be a string, not {type(key)}")
    if key in timers:
        window.clearTimeout(timers[key])
        del timers[key]
    timers[key] = window.setTimeout(proxy(python_function), int(timeout_seconds * 1000))


def repeat(python_function, key, timeout_seconds=1):
    """
    Schedules the given Python function to run every given timeout in seconds.
    If a function with the same key is already scheduled, it will be cancelled
    and a new scheduling is performed.
    """
    if key in timers:
        window.clearInterval(timers[key])
        del timers[key]
    timers[key] = window.setInterval(proxy(python_function), int(timeout_seconds * 1000))


def cancel(key):
    """ Cancels the scheduled function with the given key. """
    if key in timers:
        try:
            window.clearTimeout(timers[key])
        except: # pylint: disable=bare-except
            window.clearInterval(timers[key])
        del timers[key]


def get(url, handler, kind="json"):
    """
    Performs an asynchronous GET request to the given URL.
    The handler function is called with the response data.
    """
    start = get_time()
    @callback
    def success(response, *rest): # pylint: disable=unused-argument
        data = response if isinstance(response, str) else to_py(response)
        size = len(response) if data is response else len(dumps(data))
        window.console.log("[Network] GET OK", f"{get_time() - start:.2f}", to_human(size), url)
        handler(data)
    @callback
    def error(request, text_status, error_thrown):
        window.console.error(
            "[Network] GET ERROR", get_time() - start, error_thrown,
            request.status, repr(text_status), url
        )
        return handler(f'{{"Network error for {url}": "{text_status}"}}')
    window.ltk_get(url, success, kind, error)


def delete(url, handler):
    """
    Performs an asynchronous DELETE request to the given URL.
    The handler function is called when the delete was successful.
    """
    @callback
    def success(data, *rest): # pylint: disable=unused-argument
        return handler(to_py(data))
    @callback
    def error(request, text_status, error_thrown):
        window.console.error(
            "[Network] DELETE ERROR", request.status, text_status,
            repr(error_thrown), url
        )
    return window.ltk_delete(url, success, error)


def post(url, payload, handler, kind="json"):
    """
    Performs an asynchronous POST request to the given URL, passing the given payload.
    The handler function is called with the response data.
    """
    start = get_time()
    payload = window.encodeURIComponent(dumps(payload))
    @callback
    def success(response, *rest): # pylint: disable=unused-argument
        data = response if isinstance(response, str) else to_py(response)
        response_size = len(response) if data is response else len(dumps(data))
        size = f"{to_human(len(payload))}/{to_human(response_size)}"
        window.console.log("[Network] POST OK", f"{get_time() - start:.2f}", size, url)
        return handler(data)
    @callback
    def error(request, text_status, error_thrown):
        window.console.error(
            "[Network] POST ERROR", f"{get_time() - start:.2f}",
            request.status, text_status, repr(error_thrown), url
        )
        return handler(f'{{"Error": "{error_thrown}"}}')
    window.ltk_post(url, payload, success, kind, error)


def async_proxy(function):
    """ Returns a proxy for the given async function. """
    async def call_function(*args):
        return await function(*args)
    return proxy(call_function)


def observe(element, handler):
    """ Observes the given element and calls the given handler when the element changes. """
    config = window.eval("_={ attributes: true, childList: true, subtree: true };")
    function = proxy(lambda *args: handler(element))
    observer = window.MutationObserver.new(function)
    observer.observe(element[0], config)


def error(message):
    """ Displays an error message in the browser console. """
    if PYODIDE:
        import traceback  # pylint: disable=import-outside-toplevel,import-error
        traceback.print_exc()
    print(message)


def proxy(function):
    """
    Returns a proxy for the given function.
    On PyOdide, this is an FFI proxy. 
    On MicroPython, this simply returns the function itself.
    """
    if not function:
        return None

    def function_called_from_javascript(*args):
        try:
            return function(*args)
        except Exception as e: # pylint: disable=broad-except
            error(f"Error calling function from JavaScript {function}: {e}")
            return None

    if PYODIDE:
        return pyodide.ffi.create_proxy(function_called_from_javascript)
    else:
        return function_called_from_javascript

window.proxy = proxy


def get_url_parameter(key):
    """ Returns the current document's URL parameter. """
    return window.URLSearchParams.new(window.document.location.search).get(key)


def set_url_parameter(key, value, reload=True):
    """  Sets the current document's URL parameter. """
    search = window.URLSearchParams.new(window.location.search)
    search.set(key, value)
    url = f"{window.location.href.split('?')[0]}?{search.toString()}"
    if reload:
        window.document.location = url
    else:
        push_state(url)


def push_state(url):
    """ Pushes the given URL to the browser history. """
    window.history.pushState(None, "", url)


def inject_script(file_or_url_or_text, script_type=None, worker=None, at_end=True):
    """ Injects the given script into the document. """
    try:
        with open(file_or_url_or_text, encoding="utf-8") as fp:
            script = create("<script>").text(fp.read())
    except: #  pylint: disable=bare-except
        if file_or_url_or_text.endswith(".js"):
            script = create("<script>").attr("src", file_or_url_or_text)
        else:
            script = create("<script>").text(file_or_url_or_text)
    if script_type:
        script.attr("type", script_type)
    if worker:
        script.attr("worker", "")
    if at_end:
        script.appendTo(window.document.head)
    else:
        script.prependTo(window.document.head)


def inject_css(file_or_url_or_text, at_end=True):
    """ Injects the given CSS file or text into the document. """
    try:
        with open(file_or_url_or_text, encoding="utf-8") as fp:
            node = create("<style>").text(fp.read())
    except: # pylint: disable=bare-except
        if "{" in file_or_url_or_text:
            node = create("<style>").text(file_or_url_or_text)
        else:
            node = create("<link>").attr("rel", "stylesheet").attr("href", file_or_url_or_text)
    if at_end:
        node.appendTo(window.document.head)
    else:
        node.prependTo(window.document.head)


_fix_time_on_micropython()

if not pyscript.RUNNING_IN_WORKER:
    inject_script("ltk/ltk.js", at_end=False)
    inject_css("ltk/ltk.css", at_end=False)
