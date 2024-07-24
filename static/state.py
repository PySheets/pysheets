import builtins
import ltk
from pyscript import window # type: ignore
from polyscript import XWorker # type: ignore
import constants
import sys

pyodide = "Clang" in sys.version
micropython = "Clang" not in sys.version
local_storage = window.localStorage
worker_version = constants.WORKER_LOADING
worker_dots = ""
force_pyodide = True
uid = ltk.get_url_parameter(constants.SHEET_ID)
sheet = None
minimized = __name__ != "state"
mode = constants.MODE_PRODUCTION if minimized else constants.MODE_DEVELOPMENT


def set_title(title):
    show_message(title)
    window.document.title = f"{title} {'- ' if title else ''}PySheets"


def show_message(message):
    ltk.find("#title").val(message).css("opacity", 0).animate(ltk.to_js({ "opacity": 1 }), 2000)


def clear():
    set_title("")
    ltk.find(".dataframe-preview").remove()
    ltk.find(".arrow").removeClass("arrow")
    ltk.find(".leader-line").remove()
    ltk.find(".inputs-marker").remove()


def mobile():
    return ltk.find("body").width() < 800


class ConsoleLogger(ltk.Logger):
    def _add(self, level, *args, **argv):
        console.print(args)


class Console():
    messages = {}
    ignore_log = [ "[Debug]", "[Worker] Starting PyOdide" ]

    def __init__(self):
        window.console.orig_log = window.console.log
        window.console.orig_warn = window.console.warn
        window.console.orig_error = window.console.error
        window.console.log = self.console_log
        window.console.warn = self.console_log
        window.console.error = self.console_log
        if pyodide:
            import warnings
            warnings.warn = self.console_log
        builtins.orig_print = builtins.print
        builtins.print = self.print
        self.setup_py_error()
        self.skip = False
    
    def setup(self):
        ltk.find(".console-filter") \
            .on("keyup", ltk.proxy(lambda event: self.render()))
        self.render()
    
    def print(self, *args, **vargs):
        self.write(f"{ltk.get_time()}", f"[print] {self.format(*args)}")
    
    def format(self, *args):
        return " ".join(str(arg).replace("<", "&lt;") for arg in args)
        
    def save(self, message, action=None):
        for ignore in self.ignore_log:
            if message.startswith(ignore):
                return
    
    def clear(self, key=None):
        if key is None:
            self.messages.clear()
            self.render()
        elif key in self.messages:
            del self.messages[key]
            self.render() 

    def contains(self, key):
        return key in self.messages

    def write(self, key, *args, action=None):
        try:
            message = " ".join(str(arg) for arg in args)
        except Exception as e:
            message = f"Error writing {key}: {e}"
        if message.startswith("[Console] [Network]"):
            return
        now = window.Date.new()
        try:
            ts = f"{now.getHours()}:{now.getMinutes():02d}:{now.getSeconds():02d}.{now.getMilliseconds():03d}"
        except:
            ts = str(now)
        self.messages[key] = ts, f"{ts} {message}", action
        if "RuntimeError: pystack exhausted" in message:
            self.messages["critical"] = ts, f"{ts}s  [Critical] MicroPython Error. Enable 'PyOdide' and reload the page."
        self.render_message(key, *self.messages[key])
        self.save(message, action)

    def render(self):
        ltk.schedule(lambda: self.render_later(), "render later", 0.1)

    def render_later(self):
        ltk.find(".console .ltk-tr").remove()
        for key, (when, message, action) in sorted(self.messages.items(), key=lambda pair: pair[1][0]):
            self.render_message(key, when, message, action)
    
    def get_filter(self):
        return str(ltk.find(".console-filter").val() or "")
    
    def remove(self, key):
        ltk.find(f"#console-{key}").remove()
    
    def render_message(self, key, when, message, action=None):
        if self.skip:
            return
        self.skip = True
        try:
            action = ltk.Span("") if action is None else action
            filter = self.get_filter()
            if filter and not filter in message:
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
        except:
            pass
        finally:
            self.skip = False

    def console_log(self, *args, category=None, stacklevel=0, source=None):
        if self.skip:
            return
        self.skip = True
        try:
            message = " ".join(str(arg) for arg in args)
            if message.startswith("js_callable_proxy"):
                return
            if not message.startswith("💀🔒 - Possible deadlock"):
                key = "Network" if message.startswith("[Network]") else f"{ltk.get_time()}"
                self.write(key, f"[Console] {message}")
        except:
            pass
        finally:
            self.skip = False

    def runtime_error(self, text):
        if "RuntimeError: pystack exhausted" in text:
            return True
        if "Uncaught" in text and not "<string>" in text:
            return True

    def setup_py_error(self):
        def find_errors():
            py_error = ltk.find(".py-error")
            try:
                if py_error.length > 0:
                    text = py_error.text()
                    if self.runtime_error(text):
                        window.alert("\n".join([
                            "The Python runtime reported a programming error in PySheets.",
                            "This does not look like a problem with your scripts.",
                            "Please reload the sheet and add '&runtime=pyodide' to the URL and try again.",
                            "This should produce better error messages for PySheets.",
                            "",
                        ]))
                    else:
                        self.write("py-error", f"[Error] {text}")
            finally:
                py_error.remove()
        ltk.repeat(find_errors, 5)

console = Console()
print = console.print

def vm_type(sys_version):
    return "PyOdide" if "Clang" in sys_version else "MicroPython"


def print_stack(exc = None):
    try:
        import traceback
        traceback.print_stack()
    except:
        raise exc
    print(f"{exc.__class__.__name__}: {exc}")


def show_worker_status():
    global worker_dots
    if worker_version == constants.WORKER_LOADING:
        worker_dots += "."
        if len(worker_dots) == 6:
            worker_dots = "." 
        console.write("worker-status", f"[Worker] Starting PyOdide {constants.ICON_HOUR_GLASS} {round(ltk.get_time())}s {worker_dots}")
        ltk.schedule(show_worker_status, "worker-status", 0.95)
    else:
        console.write("worker-status", f"[Worker] Running PyOdide; Python v{worker_version}; Worker startup took {ltk.get_time():.3f}s.")


def start_worker():
    if not uid:
        return
    show_worker_status()
    url_packages = ltk.get_url_parameter(constants.PYTHON_PACKAGES)
    packages = url_packages.split(" ") if url_packages else []
    start_worker_with_packages(packages)


def start_worker_with_packages(packages):
    config = {
        "packages": [ 
            "pandas",
            "matplotlib",
            "pyscript-ltk",
            "numpy",
            "requests"
        ] + packages,
        "files": {
            "static/api.py": "./api.py",
            "static/constants.py": "./constants.py",
            "static/lsp.py": "./lsp.py",
        }
    }
    worker = XWorker(f"./worker.py", config=ltk.to_js(config), type="pyodide")
    ltk.register_worker("pyodide-worker", worker)
    ltk.schedule(lambda: check_worker(packages), "check-worker", 10)
    return worker


def check_worker(packages):
    if worker_version == constants.WORKER_LOADING:
        def fix_packages(event):
            protocol = window.document.location.protocol
            host = window.document.location.host
            window.location = f"{protocol}//{host}/?U=${sheet.uid}"
        packages_note = "Note that only full-Python wheels are supported by PyScript." if packages else ""
        console.write(
            "worker-failed",
            f"[Error] It takes longer for the worker to start than expected. {packages_note}",
            action=ltk.Button(f"⚠️ Fix", fix_packages).addClass("small-button completion-button")
        )


def worker_ready(data):
    global worker_version
    worker_version = data[1:].split()[0]
    console.remove("worker-failed")


ltk.subscribe(constants.PUBSUB_STATE_ID, ltk.pubsub.TOPIC_WORKER_READY, worker_ready)

def check_lastpass():
    if ltk.find("div[data-lastpass-root]").length:
        console.write("lastpass", f"[Error] Lastpass was detected. It slows down PySheets. Please disable it for this page.")

ltk.window.addEventListener("popstate", lambda event: print("popstate"))
check_lastpass()