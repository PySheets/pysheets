"""
CopyRight (c) 2024 - Chris Laffra - All Rights Reserved.

This module patches the PyOdide runtime to:
 - Make it work more like a standard Python runtime by handling requests better.
 - Buffering DOM access through LTK to improve performance.
"""

import builtins
import json

import constants
import ltk
import requests

import js # type: ignore    pylint: disable=import-error
import polyscript # type: ignore    pylint: disable=import-error


OriginalSession = requests.Session


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


def _patch_request():
    requests.Session = PyScriptSession
    requests.session = PyScriptSession


def _patch_document():
    if not js.document is ltk.window.document:
        js.document = ltk.window.document  # patch for matplotlib


class WidgetProxy():
    """
    Creates a proxy for Widgets to optimize access to the DOM through LTK
    """

    buffer = []

    def __init__(self, selector):
        self.selector = selector
        self.attributes = {}
        ltk.schedule(self.send_to_main, "Flush widget proxy buffer")

    def __getattr__(self, name):
        return getattr(ltk.window.jQuery(self.selector), name)

    def find(self, selector):
        """ Wraps existing LTK Widget operation for buffering """
        if not isinstance(selector, str):
            return ltk.window.jQuery(selector)
        return WidgetProxy(f"{self.selector} {selector}")

    def css(self, prop, value=None):
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

    def text(self, value=None):
        """ Wraps existing LTK Widget operation for buffering """
        if value is not None:
            WidgetProxy.buffer.append([self.selector, "text", value])
        else:
            self.flush()
            return ltk.window.jQuery(self.selector).text()
        return self

    def html(self, value=None):
        """ Wraps existing LTK Widget operation for buffering """
        if value is not None:
            WidgetProxy.buffer.append([self.selector, "html", value])
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
        WidgetProxy.buffer.append([self.selector, "remove"])
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
        polyscript.xworker.sync.publish(
            "Worker",
            "Application",
            constants.TOPIC_WORKER_WIDGET_PROXY,
            json.dumps({ "operations": WidgetProxy.buffer })
        )
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
