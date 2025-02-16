"""
CopyRight (c) 2024 - Chris Laffra - All Rights Reserved.

This module patches the PyOdide runtime to:
 - Make it work more like a standard Python runtime by handling requests better.
 - Buffering DOM access through LTK to improve performance.
"""

import builtins
import io
import json
import time
import urllib

import constants
import ltk
import requests

import js # type: ignore    pylint: disable=import-error
import polyscript # type: ignore    pylint: disable=import-error
import pyscript # type: ignore    pylint: disable=import-error


OriginalSession = requests.Session
network_cache = {}
network_calls = []


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
        self.code = status
        self.content = content
        self.msg = {}
        self.headers = {}
        self.cookies = ltk.window.document.cookie

    def info(self):
        """ Return the response headers. """
        return self.headers

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

    def read(self):
        """
        Returns the response content as a string.
        """
        return self.content.encode('utf-8')

    def __repr__(self):
        return f"Response[{self.url}, {self.status}, {self.content[32]}...]"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass



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
        content = xhr.responseText
        network_calls.append((
            method,
            url,
            xhr.status,
            len(content),
            f"{content[:64]}{'...' if len(content) > 64 else ''}"
        ))
        return PyScriptResponse(url, xhr.status, content)


def wrap_as_file(content):
    """
    Wraps the provided content as a file-like object.
    
    Args:
        content (bytes or str): The content to be wrapped as a file-like object.
    
    Returns:
        file-like object: A file-like object containing the provided content.
    """
    return io.StringIO(content) if isinstance(content, str) else io.BytesIO(content)


def _load_with_trampoline(url):
    """
    Loads the content from the provided URL using a trampoline mechanism to cache the response.
    
    Args:
        url (str): The URL to load the content from.
    
    Returns:
        bytes: The decoded content from the URL.
    
    This function first checks if the URL is already cached in the `network_cache` dictionary.
    If the cached content is less than 60 seconds old, it returns the cached value.
    Otherwise, it makes a GET request to the URL using `window.XMLHttpRequest` and caches
    the response text. If the HTTP status code is not 200, it raises an `IOError` with the status code.
    """
    def get(url):
        if url in network_cache:
            when, content = network_cache[url]
            if time.time() - when < 60:
                return content

        xhr = ltk.window.XMLHttpRequest.new()
        xhr.open("GET", url, False)
        xhr.send(None)
        if xhr.status != 200:
            raise IOError(f"HTTP Error: {xhr.status} for {url}")
        content = xhr.responseText
        network_cache[url] = time.time(), content
        network_calls.append((
            "GET", 
            url,
            xhr.status,
            len(content),
            f"{content[:64]}{'...' if len(content) > 64 else ''}"
        ))
        return content

    if isinstance(url, str) and url and url[0] != "/":
        url = f"/load?url={ltk.window.encodeURIComponent(url)}"

    return get(url)



class HTTPHandler(urllib.request.HTTPHandler):
    """ 
    A custom HTTP handler for urllib.request that uses the PyScript-based XMLHttpRequest
    """

    def __init__(self, debuglevel=0, context=None, check_hostname=None):
        urllib.request.HTTPHandler.__init__(self, debuglevel)
        self._context = context
        self._check_hostname = check_hostname

    def http_open(self, req):
        url = f"/load?url={ltk.window.encodeURIComponent(req.full_url)}"
        content = _load_with_trampoline(url)
        return PyScriptResponse(req.full_url, 200, content)


class HTTPSHandler(HTTPHandler):
    """ 
    A custom HTTPS handler for urllib.request that uses the PyScript-based XMLHttpRequest
    """

    def https_open(self, req):
        """ Wraps the https_open call, so it can be easily debugged """
        return super(HTTPSHandler, self).http_open(req)


def _patch_request():
    requests.session = PyScriptSession
    opener = urllib.request.build_opener(HTTPHandler(), HTTPSHandler())
    urllib.request._opener = opener # pylint: disable=protected-access


def _patch_fetch():
    """
    Patches the `fetch()` function to use the PyScript-based XMLHttpRequest
    """
    ltk.window.patchFetch(pyscript.window)


def _patch_document():
    if not js.document is ltk.window.document:
        js.document = ltk.window.document  # patch for matplotlib


class WidgetProxy(ltk.Widget):
    """
    Creates a proxy for Widgets to optimize access to the DOM through LTK
    """

    buffer = []

    def __init__(self, selector):
        self.selector = selector
        self.attributes = {}
        ltk.Widget.__init__(self)
        ltk.schedule(self.send_to_main, "Flush widget proxy buffer")

    @property
    def element(self):
        """ Handle the case when the proxy is added to the DOM """
        return ltk.window.jQuery(self.selector)

    @element.setter
    def element(self, value):
        """ Handle setting the element property """

    def __getattr__(self, name):
        ltk.window.console.log(f"__getattr__ {name}")
        value = getattr(ltk.window.jQuery(self.__getattribute__("selector")), name)
        return value

    def find(self, selector):
        """ Wraps existing LTK Widget operation for buffering """
        if not isinstance(selector, str):
            return ltk.window.jQuery(selector)
        return WidgetProxy(f"{self.selector} {selector}")

    def css(self, prop, value=None): # pylint: disable=arguments-renamed
        """ Wraps existing LTK Widget operation for buffering """
        if value is not None:
            WidgetProxy.buffer.append([self.selector, "css", prop, value])
        else:
            self.flush()
            return ltk.window.jQuery(self.selector).css(prop)
        return self

    def attr(self, name, value=None):
        """ Wraps existing LTK Widget operation for buffering """
        if value is not None:
            WidgetProxy.buffer.append([self.selector, "attr", name, value])
            self.attributes[name] = value
        else:
            if name in self.attributes:
                return self.attributes[name]
            else:
                self.flush()
                return ltk.window.jQuery(self.selector).attr(name)
        return self

    def prop(self, name, value=None):
        """ Wraps existing LTK Widget operation for buffering """
        if value is not None:
            WidgetProxy.buffer.append([self.selector, "prop", name, value])
        else:
            self.flush()
            return ltk.window.jQuery(self.selector).prop(name)
        return self

    def val(self, value=None):
        """ Wraps existing LTK Widget operation for buffering """
        if value is not None:
            WidgetProxy.buffer.append([self.selector, "val", value])
        else:
            self.flush()
            return ltk.window.jQuery(self.selector).val()
        return self

    def width(self, value=None):
        """ Wraps existing LTK Widget operation for buffering """
        if value is not None:
            WidgetProxy.buffer.append([self.selector, "width", value])
        else:
            self.flush()
            return ltk.window.jQuery(self.selector).width()
        return self

    def height(self, value=None):
        """ Wraps existing LTK Widget operation for buffering """
        if value is not None:
            WidgetProxy.buffer.append([self.selector, "height", value])
        else:
            self.flush()
            return ltk.window.jQuery(self.selector).height()
        return self

    def addClass(self, classes): # pylint: disable=invalid-name
        """ Wraps existing LTK Widget operation for buffering """
        WidgetProxy.buffer.append([self.selector, "addClass", classes])
        return self

    def removeClass(self, classes): # pylint: disable=invalid-name
        """ Wraps existing LTK Widget operation for buffering """
        WidgetProxy.buffer.append([self.selector, "removeClass", classes])
        return self

    def text(self, text=None):
        """ Wraps existing LTK Widget operation for buffering """
        if text is not None:
            WidgetProxy.buffer.append([self.selector, "text", text])
        else:
            self.flush()
            return ltk.window.jQuery(self.selector).text()
        return self

    def html(self, html=None):
        """ Wraps existing LTK Widget operation for buffering """
        if html is not None:
            WidgetProxy.buffer.append([self.selector, "html", html])
        else:
            self.flush()
            return ltk.window.jQuery(self.selector).html()
        return self

    def empty(self):
        """ Wraps existing LTK Widget operation for buffering """
        WidgetProxy.buffer.append([self.selector, "empty"])
        return self

    def remove(self):
        """ Wraps existing LTK Widget operation for buffering """
        self.flush()
        ltk.window.jQuery(self.selector).remove()
        return self

    def animate(self, properties, duration=None, easing=None, complete=None):
        """ Wraps existing LTK Widget operation for buffering """
        if complete:
            raise ValueError("In the PyOdide worker, LTK animation does not support a 'complete' function")
        WidgetProxy.buffer.append([self.selector, "animate", properties, duration, easing, None])
        return self

    def append(self, *children):
        """ Wraps existing LTK Widget operation for buffering """
        self.flush()
        return ltk.window.jQuery(self.selector).append(*children)

    def parent(self):
        """ Wraps existing LTK Widget operation for buffering """
        self.flush()
        return ltk.window.jQuery(self.selector).parent()

    def flush(self):
        """
        Send the currently recorded operations to the main thread.
        """
        return

    def send_to_main(self):
        """
        Send the currently recorded operations to the main thread.
        """
        if not WidgetProxy.buffer:
            return
        polyscript.xworker.sync.publish(
            "Worker",
            "Application",
            constants.TOPIC_WORKER_WIDGET_PROXY,
            json.dumps({ "operations": WidgetProxy.buffer })
        )
        print(f"flushed {len(WidgetProxy.buffer)} operations to main thread")
        WidgetProxy.buffer.clear()


def _patch_ltk():
    ltk.find = lambda selector: WidgetProxy(selector) if isinstance(selector, str) else ltk.window.jQuery(selector)


def _patch_print():
    def worker_print(*args, file=None, end=""): # pylint: disable=unused-argument
        polyscript.xworker.sync.publish(
            "Worker",
            "Application",
            constants.TOPIC_WORKER_PRINT,
            f"[Worker] {' '.join(str(arg) for arg in args)}"
        )

    builtins.print = worker_print


def patch():
    """ Patch Python modules for compatibility or performance """
    _patch_request()
    _patch_print()
    _patch_document()
    _patch_ltk()
    _patch_fetch()
