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

class Document():
    uid = ltk.get_url_parameter(constants.DATA_KEY_UID)
    name = ""
    timestamp = 0
    edits = {}
    edit_count = 0
    dirty = False
    last_edit = 0
    edit_count = 0

    def __init__(self):
        self.empty_edits()

    def empty_edits(self):
        self.edits = {
            constants.DATA_KEY_CELLS: {},
            constants.DATA_KEY_COLUMNS: {},
            constants.DATA_KEY_ROWS: {},
            constants.DATA_KEY_PREVIEWS: {},
        }


class User():
    def __init__(self):
        self.email = local_storage.getItem(constants.DATA_KEY_EMAIL) or ""
        self.token = local_storage.getItem(constants.DATA_KEY_TOKEN) or ""
        self.photo = ""
        self.name = ""

    def login(self, email, token, name="", photo=""):
        self.email = email
        self.token = token
        self.name = name
        self.photo = photo

    def clear(self):
        self.email = ""
        self.photo = ""
        self.name = ""
        self.token = ""

    def __repr__(self):
        return f"User[{self.email},{self.name},{self.photo},{self.token}]"


doc = Document()
user = User()
minimized = __name__ != "state"
mode = constants.MODE_PRODUCTION if minimized else constants.MODE_DEVELOPMENT
sync_edits = True


def login(email, token):
    local_storage.setItem(constants.DATA_KEY_EMAIL, email)
    local_storage.setItem(constants.DATA_KEY_TOKEN, token)
    user.login(email, token)

            
def create_user_image(email, timestamp):
    if not email or ltk.find(f'.other-editor[{constants.DATA_KEY_EMAIL}="{email}"]').length != 0:
        return
    first_letter = email[0].upper()
    color = constants.IMAGE_COLORS[ord(first_letter) % len(constants.IMAGE_COLORS)]
    ltk.find(".user-image-container").prepend(
        (ltk.Text(first_letter)
            .attr(constants.DATA_KEY_EMAIL, email)
            .attr(constants.DATA_KEY_TIMESTAMP, timestamp)
            .attr("title", f"{email} - {timestamp}")
            .css("background", color)
            .addClass("other-editor"))
    )


def logout(event=None):
    local_storage.removeItem(constants.DATA_KEY_EMAIL)
    local_storage.removeItem(constants.DATA_KEY_TOKEN)
    user.clear()
    window.location = "/"


def set_title(title):
    show_message(title)
    window.document.title = f"{title} {'- ' if title else ''}PySheets"
    email = local_storage.getItem(constants.DATA_KEY_EMAIL)
    ltk.find(".user-image-container").prepend(
        create_user_image(email, 0)
    )


def show_message(message):
    ltk.find("#title").val(message)


def clear():
    global doc
    set_title("")
    ltk.find("#main").empty()
    ltk.find(".dataframe-preview").remove()
    ltk.find(".arrow").removeClass("arrow")
    ltk.find(".leader-line").remove()
    ltk.find(".inputs-marker").remove()
    doc = Document()


def switch_logger(event=None):
    logger = local_storage.getItem("logger") != "true"
    local_storage.setItem("logger", "true" if logger else "false")
    window.location.reload()
    

def logger_enabled():
    return local_storage.getItem("logger") == "true"


def show_logger():
    if mode == constants.MODE_DEVELOPMENT:
        if logger_enabled():
            ltk.jQuery(window.document.body).append(ltk.Logger().element)
        else:
            ltk.find(".ltk-log-list").remove()
            ServerLogger()


def forget_result(result):
    if "removed" in result:
        logout()
    window.location = "/"


def really_forget_me():
    ServerLogger.log("really_forget_me activated")
    ltk.get(add_token(f"/forget"), ltk.proxy(forget_result))

    
def forget_me(event):
    button = ltk.Button("Continue", lambda event: None) \
        .css("padding", 10) \
        .css("color", "white") \
        .css("background", "gray") \
        .attr("disabled", True)
    dialog = ltk.VBox(
        ltk.Heading1("⚠️⚠️⚠️ WARNING ⚠️⚠️⚠️")
            .css("color", "red"),
        ltk.Text(f"This action results in permanent changes for {user.email}:"),
        ltk.UnorderedList(
            ltk.ListItem(f"All sheets owned by {user.email} be deleted and can never be recovered, not even by PySheets admins."),
            ltk.ListItem(f"Login details for {user.email} will be removed from PySheet's storage. You will have to register again."),
        ),
        ltk.Text(f"Some logging information related to {user.email} will be kept for PySheet's continued operation. However, all sheet data will be removed."),
        ltk.Break(),
        ltk.Label("I understand this is a permanent operation.",
            ltk.Checkbox(False)
                .on(
                    "change", 
                    ltk.proxy(lambda *args: button
                        .attr("disabled", button.attr("disabled") != "disabled")
                        .css("background", "grey" if button.attr("disabled") == "disabled" else "red")
                    )
                )
        ).css("font-size", 18),
        ltk.Break(),
        ltk.HBox(
            ltk.Button("Cancel", lambda event: dialog.remove())
                .css("padding", 10)
                .css("color", "white")
                .css("background", "green")
                .css("margin-right", "30px"),
            button
                .on("click", ltk.proxy(lambda event: (dialog.remove(), really_forget_me())))
        )
    ).dialog()
    dialog.parent().css("width", 400)


def show_settings(event):
    button = ltk.find(event.target)
    popup = ltk.MenuPopup(
        ltk.MenuItem("👋", "Sign out", "", ltk.proxy(logout)),
        ltk.MenuItem("💀", "Forget me", "", ltk.proxy(forget_me)),
    )
    if mode == constants.MODE_DEVELOPMENT:
        popup.append(
            ltk.MenuItem("🐞", "Hide logger" if logger_enabled() else "Show logger", "", switch_logger).element
        )
    popup.css("display", "block")
    popup.show(button.parent())


from ltk import Logger


def add_token(url):
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}{constants.DATA_KEY_TOKEN}={user.token}"


class ServerLogger(Logger):
    ignore = False
    instance = None

    def __init__(self):
        ServerLogger.instance = self

    def _add(self, level, *args, **argv):
        if self.ignore or not sync_edits:
            return
        def done(response):
            self.ignore = False
        self.ignore = True
        message = " ".join(args)
        ltk.post(add_token("/log"), { 
            constants.DATA_KEY_UID: doc.uid,
            constants.DATA_KEY_ENTRY: {
                constants.DATA_KEY_MESSAGE: message,
                constants.DATA_KEY_WHEN: ltk.get_time(),
            }
        }, ltk.proxy(done))

    @classmethod
    def log(cls, *args, **argv):
        if cls.instance:
            cls.instance._add("", *args, **argv)


class Console():
    messages = {}

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
        builtins.print = self.print
    
    def setup(self):
        ltk.find(".console-filter").on(
            "keyup",
            ltk.proxy(lambda event: self.render())
        )
    
    def print(self, *args):
        self.write(f"{ltk.get_time()}", " ".join(str(arg).replace("<", "&lt;") for arg in args))

    def clear(self, key):
        if key in self.messages:
            del self.messages[key]
        self.render()

    def write(self, key, *args):
        try:
            message = " ".join(args)
        except Exception as e:
            message = f"Error writing {key}: {e}"
        when = ltk.get_time()
        self.messages[key] = when, f"{when:4.3f}s  {message}"
        if "RuntimeError: pystack exhausted" in message:
            self.messages["critical"] = when, f"{when:4.3f}s  [Critical] MicroPython Error. Enable 'Run in main' and reload the page."
        self.render()

    def render(self):
        filter = str(ltk.find(".console-filter").val())
        console = ltk.find(".console").empty()
        for key, (when, message) in sorted(self.messages.items(), key=lambda pair: pair[1][0]):
            if filter and not filter in message: continue
            clazz = "error" if "error" in message.lower() else "warning" if "warning" in message.lower() else ""
            console.append(ltk.Preformatted(message).element.addClass(clazz))

    def console_log(self, *args):
        message = " ".join(str(arg) for arg in args)
        if not message.startswith("💀🔒 - Possible deadlock"):
            key = "Network" if message.startswith("[Network]") else f"{ltk.get_time()}"
            self.write(key, message)
        window.console.orig_log(message)

    def _setup_py_error(self):
        def find_errors():
            py_error = ltk.find(".py-error")
            try:
                if py_error.length > 0:
                    self.write("py-error", py_error.text())
            finally:
                py_error.remove()
        ltk.repeat(find_errors, 1)

console = Console()
print = console.print

def vm_type(sys_version):
    return "PyOdide" if "Clang" in sys_version else "MicroPython"


def show_worker_status():
    global worker_dots
    if worker_version == constants.WORKER_LOADING:
        worker_dots += "."
        if len(worker_dots) == 6:
            worker_dots = "." 
        console.write("worker-status", f"[Worker] Starting PyOdide {constants.ICON_HOUR_GLASS} {worker_dots}")
        ltk.schedule(show_worker_status, "worker-status", 1)
    else:
        console.write("worker-status", f"[Worker] PyOdide; Python v{worker_version} ✅")


def start_worker():
    if not doc.uid:
        return
    show_worker_status()
    url_packages = ltk.get_url_parameter(constants.DATA_KEY_PACKAGES)
    packages = url_packages.split(" ") if url_packages else []
    config = {
        "packages": [ "pandas", "matplotlib", "pyscript-ltk", "numpy", "requests" ] + packages,
    }
    worker = XWorker(f"./worker{window.app_version}.py", config=ltk.to_js(config), type="pyodide")
    ltk.register_worker("pyodide-worker", worker)
    return worker


def worker_ready(data):
    global worker_version
    worker_version = data[1:].split()[0]


ltk.subscribe(constants.PUBSUB_STATE_ID, ltk.pubsub.TOPIC_WORKER_READY, worker_ready)

def check_lastpass():
    if ltk.find("div[data-lastpass-root]").length:
        console.write("lastpass", f"Warning: Lastpass was detected. It slows down PySheets. Please disable it for this page.")

ltk.find(".menu-button").on("click", ltk.proxy(show_settings))
ltk.window.addEventListener("popstate", lambda event: print("popstate"))
show_logger()
check_lastpass()