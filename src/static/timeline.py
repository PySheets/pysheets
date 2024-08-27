"""
CopyRight (c) 2024 - Chris Laffra - All Rights Reserved.

Shows edit history and versions.

When running on PyOdide, also profiles the execution of PySheets and generates a
flamegraph visualization of the function calls for operations taking more than
100ms.
"""

import sys
import time
import ltk

import models
import state


COLORS = [
    "#FFE5E5", "#FFEFD5", "#FFFACD", "#E6E6FA", "#D8BFD8", "#DDA0DD", "#EEE9E9", "#F0FFF0",
    "#E0FFFF", "#FFDAB9", "#FFF0F5", "#FFE4E1", "#FFE4B5", "#D8BFD8", "#F5DEB3", "#F0E68C"
]
COLOR_MAP = {}


class Call():  # pylint: disable=too-few-public-methods
    """
    Represents a call in the execution timeline of a Python program.
    
    Attributes:
        when (float): The time in seconds when the call occurred.
        depth (int): The depth or nesting level of the call in the call stack.
        frame (frame): The Python frame object for the call.
        filename (str): The filename where the call occurred.
        lineno (int): The line number where the call occurred.
        duration (float): The duration of the call in seconds.
    """
    def __init__(self, when, depth, frame):
        self.when = when
        self.depth = depth
        self.frame = frame
        self.filename = frame.f_globals.get("__file__", "")
        self.lineno = frame.f_lineno
        self.duration = 0


class Span(ltk.Widget):
    """
    Represents a timespan for a call in the flame graph timeline visualization.
    """
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
        """
        Returns a VSCode URL link for the specified filename and line number.
        
        Args:
            filename (str): The filename to include in the VSCode URL.
            lineno (int): The line number to include in the VSCode URL.
        
        Returns:
            str: A VSCode URL link for the specified filename and line number.
        """
        return f"vscode://file/{ltk.window.path}/{filename}:{lineno}"

    def get_color(self, name):
        """
        Returns a unique color for the given name.
        
        Args:
            name (str): The name to get a color for.
        
        Returns:
            str: The color for the given name, in CSS format (e.g. "#FFFFFF" for white).
        """
        if not name in COLOR_MAP:
            color = COLORS[hash(name) % len(COLORS)]
            COLOR_MAP[name] = color
        return COLOR_MAP[name]

    def __eq__(self, other):
        return isinstance(other, Span) and self.key == other.key


class FlameGraph(ltk.VBox):
    """
    A `FlameGraph` widget that displays a flame graph visualization of the profiled function calls.
    
    The `FlameGraph` class inherits from `ltk.VBox` and is responsible for rendering a flame graph
    visualization of the profiled function calls. It takes a list of `Call` objects as input and
    displays a flame graph with the function call durations and names.
    
    The flame graph can be zoomed in and out using the provided buttons, and the entire widget
    can be removed from the timeline container.
    """
    classes = [ "flame" ]

    def __init__(self, calls):
        ltk.VBox.__init__(self)
        self.calls = calls
        self.scale = 1
        call = self.calls[-1]
        name = call.frame.f_code.co_name.replace("<", "&lt;")

        def zoom(dy):
            self.scale = max(1, self.scale / 3) if dy < 0 else self.scale * 3
            self.render()

        def zoom_out(event): # pylint: disable=unused-argument
            self.scale = max(1, self.scale / 3)
            self.render()

        def zoom_in(event): # pylint: disable=unused-argument
            self.scale *= 3
            self.render()

        self.container = ltk.Div().on("wheel", ltk.proxy(lambda event: zoom(-event.originalEvent.deltaY)))

        self.append(
            ltk.VBox(
                ltk.HBox(
                    ltk.Text(f"{name} took {call.duration}s").addClass("flame-title"),
                    ltk.Span("").css("flex", 1),
                    ltk.Button("-", lambda event: zoom_out(event)), # pylint: disable=unnecessary-lambda
                    ltk.Button("+", lambda event: zoom_in(event)), # pylint: disable=unnecessary-lambda
                    ltk.Button("x", lambda event: self.remove()).css("margin-right", 14), # pylint: disable=unnecessary-lambda
                ).addClass("flame-header"),
            ),
            self.container
        )
        self.render()

    def render(self):
        """
        Renders the flame graph visualization of the profiled function calls.
        """
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


class Profiler():
    """
    The `Profiler` class is responsible for profiling the execution of a Python program and
    generating a flame graph visualization of the profiled function calls.
    """
    MIN_DURATION = 0.1

    calls = [] # when, duration, depth, frame
    stack = [] # when, frame

    def __init__(self):
        self.epoch = time.time()
        ltk.schedule(self.add_toggle, "add profiler toggle")
        self.enable_profile()

    def enabled(self):
        """
        Returns whether the timeline profiling is currently enabled.
        """
        return ltk.window.localStorage.getItem("timeline-enabled") == "true"

    def enable(self, enabled):
        """
        Enables or disables the timeline profiling functionality.
        
        Args:
            enabled (bool): True to enable the timeline profiling, False to disable it.
        """
        ltk.window.localStorage.setItem("timeline-enabled", enabled)

    def add_toggle(self):
        """
        Adds a toggle switch to the timeline container that enables or disables the timeline profiling functionality.
        """
        ltk.find(".timeline-container").append(
            ltk.Switch("enabled", self.enabled())
                .addClass("timeline-switch")
                .on("change", ltk.proxy(lambda event: self.toggle(ltk.find(event.target))))
        )

    def toggle(self, checkbox):
        """
        Toggles the profiling functionality of the Profiler class.
        
        Args:
            checkbox (ltk.Widget): The checkbox widget that represents the profiling toggle.
        """
        self.enable(checkbox.prop("checked"))
        self.enable_profile()

    def enable_profile(self):
        """
        Enables or disables the profiling functionality of the Profiler class.
        
        When profiling is enabled, the `sys.setprofile()` function is set to the `self.profile`
        method, which is responsible for recording function call information.
        When profiling is disabled, `sys.setprofile()` is set to `None` to stop the profiling.
        """
        sys.setprofile(self.profile if self.enabled() else None)

    def profile(self, frame, event, arg=None): # pylint: disable=unused-argument
        """
        Records function call information for the timeline profiling functionality.
        
        This method is set as the `sys.setprofile()` function when the timeline profiling is enabled.
        It is responsible for recording function call information, including the timestamp, call depth,
        and duration of each function call. The recorded information is stored in the `self.calls` list.
        
        If a function call takes longer than the `Profiler.MIN_DURATION` threshold, a console message is
        written with the function name and duration, and a FlameGraph is appended to the timeline container.
        
        Args:
            frame (frame): The current stack frame.
            event (str): The event type, either "call" or "return".
            arg (Any, optional): The argument passed to the function, if any.
        """
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
                        name = call.frame.f_code.co_name.replace("<","").replace(">","")
                        state.console.write(
                            f"timeline-{name}", 
                            f"[Timeline] Call to '{name}' took {call.duration}s. See timeline. 🔔️"
                        )
                        ltk.find(".timeline-container").append(
                            FlameGraph(self.calls)
                        )
                    Profiler.calls = []

        return self.profile


class Edit(ltk.TableRow):
    """
    An `Edit` widget that displays an edit made by the user.
    """
    classes = [ "edit" ]

    def __init__(self, edit):
        self.edit = edit
        description = edit.describe()
        if description:
            ltk.TableRow.__init__(self,
                ltk.TableData(self.get_timestamp()),
                ltk.TableData(
                    ltk.Button("undo", lambda event: self.undo()).addClass("undo-button"),
                ),
                ltk.TableData(
                    ltk.Span(description),
                )
            )
            self.attr("id", f"edit-{id(edit)}")

    def get_timestamp(self):
        """
        Get a human-readable timestamp for the edit.
        """
        try:
            now = ltk.window.Date.new()
            return f"{now.getHours()}:{now.getMinutes():02d}:{now.getSeconds():02d}"
        except TypeError:
            return "00:00:00"

    def undo(self):
        """
        Undoes the edit and removes it from the timeline.
        """
        print("undo edit", self.edit.undo)
        self.edit.undo(state.SHEET)
        self.remove()


def add_edit(edit):
    """
    Adds an edit to the timeline view, so the user can inspect the edit history.
    """
    if isinstance(edit, (models.EmptyEdit, models.ScreenshotChanged)):
        return
    ltk.find(".timeline-container").prepend(
        Edit(edit).element
    )


def setup():
    """
    Enables the timeline profiling functionality by creating a new `Profiler` instance.
    
    This function is called to set up the timeline profiling feature. It checks if the
    `unittest` module is not loaded and if the `sys.setprofile()` function is available.
    If these conditions are met, it creates a new `Profiler` instance to start recording
    function call information for the timeline.
    """
    if 'unittest' not in sys.modules and hasattr(sys, "setprofile"):
        Profiler()


def remove(edit):
    """
    Removes it from the timeline.
    
    Args:
        edit (Edit): The edit to be undone.
    """
    ltk.find(f"#edit-{id(edit)}").remove()
