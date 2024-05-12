import constants
import ltk
import state

class Profiler():
    tasks = []

    def __init__(self):
        self.enabled = state.pyodide and state.mode == constants.MODE_DEVELOPMENT
        if self.enabled:
            self.active = ltk.window.localStorage.getItem("profiler-active")
            self.toggle = (
                ltk.Checkbox(self.active)
                    .addClass("profiler-toggle")
                    .css("width", 15)
                    .css("height", 15)
                    .css("border-color", "gray")
                    .on("change", ltk.proxy(lambda event: self.toggle_active()))
                    .appendTo(ltk.find("body"))
            )

    def toggle_active(self):
        self.active = not self.active
        ltk.window.localStorage.setItem("profiler-active", "true" if self.active else "")
    
    def start(self, task):
        if not self.enabled or not self.active:
            return
        self.tasks.append(task)
        if len(self.tasks) == 1:
            from cProfile import Profile
            self.profile = Profile()
            self.profile.enable()

    def stop(self):
        if not self.enabled or not self.active:
            return
        print("Profiling result for task", self.tasks.pop(), self.tasks)
        if len(self.tasks) == 0:
            self.profile.disable()
            self.report()

    def report(self):
        if not self.enabled:
            return

        import builtins
        import io
        from pstats import SortKey, Stats

        tmp_print = builtins.print
        builtins.print = builtins.orig_print
        s = io.StringIO()
        (
            Stats(self.profile, stream=s)
                .strip_dirs()
                .sort_stats(SortKey.CUMULATIVE)
                .print_stats(21)
        )
        builtins.print = tmp_print
        for line in s.getvalue().strip().split("\n"):
            print(line.replace(" ", "&nbsp;"))

profiler = Profiler()

start = profiler.start
stop = profiler.stop





