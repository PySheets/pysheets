"""
CopyRight (c) 2024 - Chris Laffra - All Rights Reserved.

This module contains the global state and utility functions for the PySheets application.
"""

import sys

import builtins
import ltk
import constants

from polyscript import XWorker # type: ignore   pylint: disable=import-error


PYODIDE = "Clang" in sys.version
WORKER_VERSION = constants.WORKER_LOADING
WORKER_DOTS = ""
UID = ltk.get_url_parameter(constants.SHEET_ID)
SHEET = None


def set_title(title):
    """
    Sets the title of the PySheets application window.
    
    Args:
        title (str): The title to set for the application window.
    """
    show_message(title)
    ltk.window.document.title = f"{title} {'- ' if title else ''}PySheets"


def show_message(message):
    """
    Shows a message in the title of the PySheets application window with a fade-in animation.
    
    Args:
        message (str): The title to set for the application window.
    """
    ltk.find("#title").val(message).css("opacity", 0).animate(ltk.to_js({ "opacity": 1 }), 2000)


def clear():
    """
    Clears the state of the PySheets application.
    """
    set_title("")
    ltk.find(".dataframe-preview").remove()
    ltk.find(".arrow").removeClass("arrow")
    ltk.find(".leader-line").remove()
    ltk.find(".inputs-marker").remove()


def mobile():
    """
    Determines whether the current device is a mobile device based on the width of the body element.
    
    Returns:
        bool: True if the body element width is less than 800 pixels, False otherwise.
    """
    return ltk.find("body").width() < 800


class ConsoleLogger(ltk.Logger):
    """
    Logs messages to the application console.
    """
    def _add(self, level, *args, **argv):
        console.print(args)


class Console():
    """
    The `Console` class is responsible for logging messages to the application console.
    It overrides the default console logging functions and provides methods for writing,
    formatting, and rendering console messages.
    """
    messages = {}
    ignore_log = [ "[Debug]", "[Worker] Starting PyOdide" ]

    def __init__(self):
        ltk.window.console.orig_log = ltk.window.console.log
        ltk.window.console.orig_warn = ltk.window.console.warn
        ltk.window.console.orig_error = ltk.window.console.error
        ltk.window.console.log = self.console_log
        ltk.window.console.warn = self.console_log
        ltk.window.console.error = self.console_log
        if PYODIDE:
            import warnings # pylint: disable=import-outside-toplevel
            warnings.warn = self.console_log
        builtins.orig_print = builtins.print
        builtins.print = self.print
        self.setup_py_error()

    def setup(self):
        """
        Initializes the state
        """
        ltk.find(".console-filter") \
            .on("keyup", ltk.proxy(lambda event: self.render()))
        self.render()

    def print(self, *args, **vargs): # pylint: disable=unused-argument
        """
        Writes a formatted message to the console.
        """
        self.write(f"{ltk.get_time()}", f"[print] {self.format(*args)}")

    def format(self, *args):
        """
        Formats the provided arguments as a string by joining them together with spaces,
        and escaping any less-than characters (`<`) by replacing them with the HTML entity `<`.
        
        Args:
            *args: The arguments to format as a string.
        
        Returns:
            A string representation of the provided arguments, with less-than characters escaped.
        """
        return " ".join(str(arg).replace("<", "&lt;") for arg in args)

    def clear(self, key=None):
        """
        Clears the console messages, either for a specific key or for all messages.
        
        Args:
            key (str, optional): The key of the message to clear. If not provided, all messages will be cleared.
        """
        if key is None:
            self.messages.clear()
            self.render()
        elif key in self.messages:
            del self.messages[key]
            self.render()

    def contains(self, key):
        """
        Checks if the state object contains a message with the given key.
        
        Args:
            key (str): The key of the message to check for.
        
        Returns:
            bool: True if a message with the given key exists, False otherwise.
        """
        return key in self.messages

    def write(self, key, *args, action=None):
        """
        Writes a message to the console with the current timestamp.
        
        Args:
            key (str): A unique identifier for the message.
            *args: The message to be written to the console.
            action (Optional[Any]): An optional action to be associated with the message.
        """
        message = " ".join(str(arg) for arg in args)
        if message.startswith("[Console] [Network]"):
            return
        now = ltk.window.Date.new()
        ts = f"{now.getHours()}:{now.getMinutes():02d}:{now.getSeconds():02d}.{now.getMilliseconds():03d}"
        self.messages[key] = ts, f"{ts} {message}", action
        if "RuntimeError: pystack exhausted" in message:
            self.messages["critical"] = ts, f"{ts}s  [Critical] MicroPython Error. Try running with 'PyOdide'."
        self.render_message(key, *self.messages[key])

    def render(self):
        """
        Schedules the rendering of the console messages.
        """
        ltk.schedule(self.render_now, "render later", 0.1)

    def render_now(self):
        """
        Renders the console messages.
        """
        ltk.find(".console .ltk-tr").remove()
        for key, (when, message, action) in sorted(self.messages.items(), key=lambda pair: pair[1][0]):
            self.render_message(key, when, message, action)

    def get_filter(self):
        """
        Returns the current value of the console filter input element, or an empty string if the input is empty.
        
        Returns:
            str: The current value of the console filter input, or an empty string.
        """
        return str(ltk.find(".console-filter").val() or "")

    def remove(self, key):
        """
        Removes the console message with the given key from the console table.
        
        Args:
            key (str): The unique identifier of the console message to remove.
        """
        ltk.find(f"#console-{key}").remove()

    def render_message(self, key, when, message, action=None): # pylint: disable=unused-argument
        """
        Renders a console message with the given key, timestamp, and message text.
        The message is filtered based on the current value of the console filter 
        nput element, and the message is removed from the console table if it matches the filter.
        
        Args:
            key (str): A unique identifier for the console message.
            when (str): The timestamp of the console message.
            message (str): The text of the console message.
            action (Optional[Any]): An optional action to be associated with the console message.
        """
        action = ltk.Span("") if action is None else action
        filter_text = self.get_filter()
        if filter_text and not filter_text in message:
            return
        self.remove(key)
        parts = message.split()
        clazz = parts[1][1:-1].lower() # [Debug] becomes debug
        ltk.find(".console table").append(
            ltk.TableRow(
                ltk.TableData(ltk.Preformatted(parts[0])),
                ltk.TableData(ltk.Preformatted(parts[1])),
                ltk.TableData(
                    ltk.HBox(
                        action.css("margin-left", 0).css("margin-top", 0),
                        ltk.Preformatted(" ".join(parts[2:]).replace("<", "&lt;")),
                    )
                ).css("width", "100%")
            )
            .attr("id", f"console-{key}").addClass(clazz)
        )

    def console_log(self, *args, category=None, stacklevel=0, source=None):  # pylint: disable=unused-argument
        """
        Logs a console message with the given arguments.
        """
        message = " ".join(str(arg) for arg in args)
        if message.startswith("js_callable_proxy"):
            return # ignore message generated by the PyScript runtime
        if "Error loading background-image http" in message:
            return # ignore message generated by the html2canvas library
        if not message.startswith("💀🔒 - "):
            key = "Network" if message.startswith("[Network]") else f"{ltk.get_time()}"
            self.write(key, f"[Console] {message}")

    def contains_runtime_error(self, text):
        """
        Checks if the given text indicates a runtime error.
        
        Args:
            text (str): The text to check for runtime errors.
        
        Returns:
            bool: True if the text indicates a runtime error, False otherwise.
        """
        if "RuntimeError: pystack exhausted" in text:
            return True
        if "Uncaught" in text and not "<string>" in text:
            return True
        return False

    def setup_py_error(self):
        """
        Checks for and handles Python runtime errors in the PySheets application.
        """
        def find_errors():
            py_error = ltk.find(".py-error")
            try:
                if py_error.length > 0:
                    text = py_error.text()
                    if self.contains_runtime_error(text):
                        ltk.window.alert("\n".join([
                            "The Python runtime reported a programming error in PySheets.",
                            "This does not look like a problem with your scripts.",
                            "Please reload the sheet again, adding '&runtime=py' to the URL.",
                            "This should produce better error messages for PySheets.",
                            "",
                        ]))
                    else:
                        self.write("py-error", f"[Error] {text}")
            finally:
                py_error.remove()
        ltk.repeat(find_errors, 5)


console = Console()
print = console.print # pylint: disable=redefined-builtin


def vm_type(sys_version):
    """
    Determines the type of VM to use based on the Python version.
    
    Args:
        sys_version (str): The version string of the Python runtime.
    
    Returns:
        str: The type of VM to use, either "PyOdide" or "MicroPython".
    """
    return "PyOdide" if "Clang" in sys_version else "MicroPython"


def show_worker_status():
    """
    Displays the status of the PyOdide worker, including the time it has been running and a loading indicator.
    """
    global WORKER_DOTS # pylint: disable=global-statement
    if WORKER_VERSION == constants.WORKER_LOADING:
        WORKER_DOTS += "."
        if len(WORKER_DOTS) == 6:
            WORKER_DOTS = "."
        console.write(
            "worker-status",
            f"[Worker] Starting PyOdide {constants.ICON_HOUR_GLASS} {round(ltk.get_time())}s {WORKER_DOTS}"
        )
        ltk.schedule(show_worker_status, "worker-status", 0.95)
    else:
        console.write(
            "worker-status", 
            f"[Worker] Running PyOdide; Python v{WORKER_VERSION}; Worker startup took {ltk.get_time():.3f}s."
        )


def start_worker():
    """
    Starts the PyOdide worker when we are editing a sheet.
    
    Args:
        None
    
    Returns:
        None
    """
    if not UID:
        return
    show_worker_status()
    packages = SHEET.packages.split(" ") if SHEET.packages else []
    start_worker_with_packages(packages)


def start_worker_with_packages(packages):
    """
    Starts the PyOdide worker with the specified packages.
    
    Args:
        packages (List[str]): A list of additional packages to include in the PyOdide worker.
    
    Returns:
        XWorker: The started PyOdide worker.
    """
    config = {
        "interpreter": "pyodide/pyodide.js",
        "packages": [ 
            "pandas",
            "matplotlib",
            "numpy",
            "requests"
        ] + packages,
        "files": {
            "static/api.py": "./api.py",
            "static/constants.py": "./constants.py",
            "static/lsp.py": "./lsp.py",
            "static/ltk/jquery.py": "ltk/jquery.py",
            "static/ltk/widgets.py": "ltk/widgets.py",
            "static/ltk/pubsub.py": "ltk/pubsub.py",
            "static/ltk/__init__.py": "ltk/__init__.py",
            "static/ltk/logger.py": "ltk/logger.py",
            "static/ltk/ltk.js": "ltk/ltk.js",
            "static/ltk/ltk.css": "ltk/ltk.css"
        }
    }
    worker = XWorker("./worker.py", config=ltk.to_js(config), type="pyodide")
    ltk.register_worker("pyodide-worker", worker)
    ltk.schedule(lambda: check_worker(packages), "check-worker", 10)
    return worker


def check_worker(packages):
    """
    Checks the status of the PyOdide worker and displays a message if the worker
    takes longer than expected to start.
    """
    if WORKER_VERSION == constants.WORKER_LOADING:
        def fix_packages(event): # pylint: disable=unused-argument
            protocol = ltk.window.document.location.protocol
            host = ltk.window.document.location.host
            ltk.window.location = f"{protocol}//{host}/?U=${UID}"

        packages_note = "Note that only full-Python wheels are supported by PyScript." if packages else ""

        console.write(
            "worker-failed",
            f"[Error] It takes longer for the worker to start than expected. {packages_note}",
            action=ltk.Button("⚠️ Fix", fix_packages).addClass("small-button completion-button")
        )


def worker_ready(data):
    """
    Handles the event when the PyOdide worker is ready.
    
    Args:
        data (str): The data associated with the worker ready event.
    
    This function is called when the PyOdide worker is ready to be used. It updates the global
    `WORKER_VERSION` variable with the version of the worker, and removes the
    "worker-failed" message from the console if it was previously displayed.
    """
    global WORKER_VERSION   # pylint: disable=global-statement
    WORKER_VERSION = data[1:].split()[0]
    console.remove("worker-failed")
    show_support_message()

def show_support_message():
    """
    Displays a message on the console to support the open-source PySheets project.
    """
    action = ltk.Link("https://github.com/PySheets/pysheets",
        ltk.Button("Star", click=lambda event: None)
            .addClass("star-button")
            .css("min-width", 45)
    )
    console.write(
        "star",
        "[Github] PySheets is open-source. Give it a star ⭐.",
        action=action
    )


ltk.subscribe(constants.PUBSUB_STATE_ID, ltk.pubsub.TOPIC_WORKER_READY, worker_ready)


def check_lastpass():
    """
    Checks if the LastPass browser extension is detected on the page, and if so, writes
    a warning message to the console.
    """
    if ltk.find("div[data-lastpass-root]").length:
        console.write(
            "lastpass", 
            "[Error] Lastpass was detected. It slows down PySheets. Please disable it for this page."
        )


ltk.window.addEventListener("popstate", lambda event: print("popstate"))


try:
    check_lastpass()
except TypeError: # handle unit test mock error
    pass
