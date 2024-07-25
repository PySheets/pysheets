import ltk
import state
import sys
import time


colors = [ "#FFE5E5", "#FFEFD5", "#FFFACD", "#E6E6FA", "#D8BFD8", "#DDA0DD", "#EEE9E9", "#F0FFF0", "#E0FFFF", "#FFDAB9", "#FFF0F5", "#FFE4E1", "#FFE4B5", "#D8BFD8", "#F5DEB3", "#F0E68C" ]
color_map = {}


class Call():
    def __init__(self, when, depth, frame):
        self.when = when
        self.depth = depth
        self.frame = frame
        self.filename = frame.f_globals.get("__file__", "")
        self.lineno = frame.f_lineno
        self.duration = 0
       

class Span(ltk.Widget):
    classes = [ "call" ]
    height = 20

    def __init__(self, when, call, pixels_per_second):
        ltk.Widget.__init__(self)
        module = call.frame.f_globals.get("__name__", "").replace("__main__", "pysheets")
        instance = call.frame.f_locals.get("self")
        clazz = ""
        if instance is not None:
            clazz = instance.__class__.__name__
            module = instance.__module__
        filename = call.filename.replace('/home/pyodide/', '')
        short_name = call.frame.f_code.co_name.replace("<", "&lt;")
        full_name = f"{module}.{clazz}.{short_name}"
        label = f"{short_name} | {call.duration:.2f}s at {when:.2f}s | {full_name}"
        self.html(f"<a href={self.get_vscode_link(filename, call.lineno)}>{label}</a>")
        self.attr("title", label)
        self.css("background-color", self.get_color(full_name))
        self.css("left", 8 + (call.when - when) * pixels_per_second)
        self.css("top", 40 + Span.height * call.depth)
        self.css("width", max(2, pixels_per_second * call.duration))
        
    def get_vscode_link(self, filename, lineno):
        return f"vscode://file/{ltk.window.path}/{filename}:{lineno}"

    def get_color(self, name):
        if not name in color_map:
            color = colors[hash(name) % len(colors)]
            color_map[name] = color
        return color_map[name]

    def __eq__(self, other):
        return isinstance(other, Span) and self.key == other.key


class FlameGraph(ltk.VBox):
    classes = [ "flame" ]

    def __init__(self, calls):
        ltk.VBox.__init__(self)
        self.calls = calls
        self.scale = 1
        self.container = ltk.Div().on("wheel", lambda event: self.zoom(-event.originalEvent.deltaY))
        call = self.calls[-1]
        name = call.frame.f_code.co_name.replace("<", "&lt;")
        self.append(
            ltk.VBox(
                ltk.HBox(
                    ltk.Text(f"{name} took {call.duration}s").addClass("flame-title"),
                    ltk.Span("").css("flex", 1),
                    ltk.Button("-", lambda event: self.zoom_out(event)),
                    ltk.Button("+", lambda event: self.zoom_in(event)),
                    ltk.Button("x", lambda event: self.remove()).css("margin-right", 14),
                ).addClass("flame-header"),
            ),
            self.container
        )
        self.render()

    def render(self):
        last = self.calls[-1]
        min_duration = 0 if self.scale > 1 else 0.01
        spans = [
            Span(last.when, call, self.scale * 300)
            for call in self.calls
            if call.duration > min_duration and not call.filename == "/home/pyodide/timeline.py"
        ]
        self.container.empty().append(*[span.element for span in spans])
        max_depth = max(call.depth for call in self.calls if call.duration > min_duration)
        self.css("width", max(span.width() + 20 for span in spans))
        self.css("height", 52 + (max_depth + 1) * Span.height)
        self.find(".flame-title").css("visibility", "visible" if self.scale > 1 else "hidden")

    def zoom(self, dy):
        self.scale = max(1, self.scale / 3) if dy < 0 else self.scale * 3
        self.render()

    def zoom_out(self, event):
        self.scale = max(1, self.scale / 3)
        self.render()

    def zoom_in(self, event):
        self.scale *= 3
        self.render()

class Profiler():
    MIN_DURATION = 0.1

    calls = [] # when, duration, depth, frame
    stack = [] # when, frame

    def __init__(self):
        self.epoch = time.time()
        ltk.schedule(self.add_toggle, "add profiler toggle")
        self.enable_profile()

    def enabled(self):
        return ltk.window.localStorage.getItem("timeline-enabled") == "true"
        
    def enable(self, enabled):
        ltk.window.localStorage.setItem("timeline-enabled", enabled)
    
    def add_toggle(self):
        ltk.find(".timeline-container").append(
            ltk.Switch("enabled", self.enabled())
                .addClass("timeline-switch")
                .on("change", ltk.proxy(lambda event: self.toggle(ltk.find(event.target))))
        )

    def toggle(self, checkbox):
        self.enable(checkbox.prop("checked"))
        self.enable_profile()
    
    def enable_profile(self):
        sys.setprofile(self.profile if self.enabled() else None)

    def profile(self, frame, event, arg=None):
        now = round(time.time() - self.epoch, 3)
        if event == "call":
            Profiler.stack.append(Call(now, len(Profiler.stack), frame))

        if Profiler.stack and event == "return":
            call = Profiler.stack.pop()
            if call.depth < 13:
                call.duration = round(now - call.when, 3)
                self.calls.append(call)
                if call.depth == 0:
                    if call.filename != "/home/pyodide/timeline.py" and call.duration > Profiler.MIN_DURATION:
                        name = call.frame.f_code.co_name
                        state.console.write(f"timeline-{name}", f"[Timeline] Call to '{name}' took {call.duration}s. See timeline. 🔔️")
                        ltk.find(".timeline-container").append(
                            FlameGraph(self.calls)
                        )
                    Profiler.calls = []

        return self.profile


def setup():
    if not 'unittest' in sys.modules and hasattr(sys, "setprofile"):
        Profiler()