import collections
import ltk
import state
import constants

import logging

logger = logging.getLogger("root")
counts = collections.defaultdict(int)
worker = state.start_worker()


class Cache:
    cache = {}

    def set(self, key, value):
        self.cache[key] = value

    def has(self, key):
        return key in self.cache

    def get(self, key):
        return self.cache.get(key)

    def remove(self, key):
        if key in self.cache:
            del self.cache[key]


cache = Cache()


class Layer:
    frozen = False

    def __enter__(self):
        self.frozen = True
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.frozen = False
        return None


layer = Layer()


def get_col_row_from_key(key):
    row = 0
    col = 0
    for c in key:
        if c.isdigit():
            row = row * 10 + int(c)
        else:
            col = col * 26 + ord(c) - ord("A") + 1
    return col - 1, row - 1


def get_key_from_col_row(col, row):
    return f"{get_column_name(col)}{row + 1}"


def get_column_name(col):
    parts = []
    col += 1
    while col > 0:
        col, remainder = divmod(col - 1, 26)
        parts.insert(0, chr(remainder + ord("A")))
    return "".join(parts)


def convert(value):
    try:
        return float(value) if "." in value else int(value)
    except:
        return value


class Node(object):
    inputs = []
    nodes = {}

    def __init__(self, key, value):
        self.invalid = False
        self.script = value
        self.value = convert(value)
        self.key = key
        self.preview = None
        Node.nodes[key] = self

    def get(self):
        return self.value

    def debug_get_info(self):
        td = ltk.find(f"#{self.key}").parent()
        if td.find(".debug-info").length:
            return td.find(".debug-info")
        return ltk.Text().addClass("debug-info").appendTo(td)

    def reset(self):
        pass

    def update(self, kind, value):
        self.invalid = False
        if kind in ["str", "int", "float"]:
            preview = None
        else:
            self.kind = kind
            value, preview = kind, value
        changed = cache.get(self.key) != value
        cache.set(self.key, value)
        if changed:
            self.value = value
            self.preview = preview
            if not layer.frozen:
                ltk.publish(
                    constants.PUBSUB_DAG_ID,
                    constants.PUBSUB_SHEET_ID,
                    constants.TOPIC_NODE_CHANGED,
                    self.key,
                )
            Formula.handle_node_changed(self.key)

    def run_in_worker(self):
        pass

    def reload(self):
        pass

    def to_dict(self):
        return {
            constants.DATA_KEY_VALUE_FORMULA: self.value,
        }

    def __repr__(self):
        one_line = lambda s: s.replace("\n", "\\n") if isinstance(s, str) else s
        return f"{self.__class__.__name__}[{self.key}|{one_line(self.value)}|{one_line(self.script)}]"


class String(Node):
    pass


class Boolean(Node):
    pass


class Number(Node):
    pass


class Formula(Node):
    def __init__(self, key, script, kind, preview):
        Node.__init__(self, key, script)
        self.value = kind
        self.kind = kind
        self.preview = preview
        self.loading = False
        self.inputs = self.get_inputs(script)
        cache.remove(self.key)
        if preview and not layer.frozen:
            ltk.publish(
                constants.PUBSUB_DAG_ID,
                constants.PUBSUB_SHEET_ID,
                constants.TOPIC_NODE_CHANGED,
                self.key,
            )
        ltk.schedule(self.get, f"get {self.key}")

    def get(self):
        state.console.write(f"worker-run-{self.key}", f"{self.key}: Running")
        if self.loading:
            return f"{constants.ICON_HOUR_GLASS}"
        if cache.has(self.key):
            state.console.write(
                f"worker-run-{self.key}", f"{self.key}: Cached => {cache.get(self.key)}"
            )
            return cache.get(self.key)
        self.loading = True
        state.console.clear(self.key)
        try:
            invalid_nodes = [
                key
                for key in self.inputs
                if key in Node.nodes and Node.nodes[key].invalid
            ]
            if any(invalid_nodes):
                for key in invalid_nodes:
                    if key in Node.nodes:
                        Node.nodes[key].reset()
                state.console.write(
                    f"worker-run-{self.key}", f"{self.key}: {self.value}"
                )
                return self.value
            inputs = dict(
                (key, Node.nodes[key].get()) for key in self.inputs if key in Node.nodes
            )
            try:
                value = eval(self.script[1:], inputs)
                kind = value.__class__.__name__
                self.update(kind, value)
                state.console.write(
                    f"worker-run-{self.key}", f"{self.key}: Eval => {value}"
                )
            except:

                def edit_script(script):  # TODO: use ast to parse script
                    lines = script.strip().split("\n")
                    lines[-1] = f"_={lines[-1]}"
                    return "\n".join(lines)

                try:
                    _locals = inputs
                    _locals["ltk"] = ltk
                    exec(edit_script(self.script[1:]), _locals)
                    self.value = _locals["_"]
                    self.update(self.value.__class__.__name__, _locals["_"])
                    cache.set(self.key, _locals["_"])
                    self.loading = False
                    kind = self.value
                    state.console.write(
                        f"worker-run-{self.key}", f"{self.key}: Ran locally => {kind}"
                    )
                    return self.value
                except Exception as e:
                    state.console.write(
                        f"worker-run-{self.key}", f"{self.key}: Exec => {e}"
                    )
                    self.invalid = True
                    self.loading = False
                    self.run_in_worker()
            return self.value or f"{constants.ICON_HOUR_GLASS}"
        except Exception as e:
            state.console.write(
                f"worker-run-{self.key}", f"{self.key}: Cannot run locally => {e}"
            )
        finally:
            self.loading = False

    def reload(self):
        if not cache.has(self.key):
            self.reset()

    def reset(self):
        if self.loading:
            return
        self.loading = False
        cache.remove(self.key)
        self.get()

    def run_in_worker(self):
        if not worker or self.loading:
            return
        status = "Running" if state.worker_ready[id(worker)] else "Pending"
        state.console.write(
            f"worker-run-{self.key}",
            f"{self.key}: {status} {constants.ICON_HOUR_GLASS}",
        )
        self.loading = True
        inputs = dict(
            (key, Node.nodes[key].get()) for key in self.inputs if key in Node.nodes
        )
        ltk.publish(
            "Application",
            "Worker",
            ltk.TOPIC_WORKER_RUN,
            [self.key, self.script[1:], inputs],
        )

    def get_inputs(self, script):
        if "# no-inputs" in script:
            return []
        # TODO: sort first and last by min/max col/row
        inputs = []
        index = 0
        is_col = lambda c: c >= "A" and c <= "Z"
        is_row = lambda c: c.isdigit()
        string = self.script[1:]
        while index < len(string):
            c = string[index]
            if is_col(string[index]):
                start = index
                while index < len(string) and is_col(string[index]):
                    index += 1
                if index < len(string) and is_row(string[index]):
                    while index < len(string) and is_row(string[index]):
                        index += 1
                    key = string[start:index]
                    if start > 0 and string[start - 1] == ":" and inputs:
                        inputs.extend(self.get_input_range(inputs.pop(), key))
                    else:
                        inputs.append(key)
            index += 1
        return inputs

    def get_input_range(self, start, end):
        start_col, start_row = get_col_row_from_key(start)
        end_col, end_row = get_col_row_from_key(end)
        return [
            get_key_from_col_row(col, row)
            for row in range(start_row, end_row + 1)
            for col in range(start_col, end_col + 1)
        ]

    def to_dict(self):
        return {
            constants.DATA_KEY_VALUE_FORMULA: self.script,
            constants.DATA_KEY_VALUE_KIND: self.kind,
            constants.DATA_KEY_VALUE_PREVIEW: self.preview,
        }

    @classmethod
    def handle_job_result(cls, result):
        try:
            key, duration, kind, value = result
            node = Node.nodes[key]
            node.update(kind, value)
            if value and value.startswith("Traceback"):
                state.console.write(key, f"{key}: Error {value}")
            else:
                counts[key] += 1
                state.console.write(
                    f"worker-run-{key}",
                    f"{key}: {counts[key]} run{'s' if counts[key] > 1 else ''}, {duration:.3f}s => {value if kind == 'str' else kind}",
                )
        except Exception as e:
            logger.error(f"Worker Error: {e} {str(result)[:32]}")

    @classmethod
    def handle_cell_changed(cls, key):
        for node in Node.nodes.values():
            if key in node.inputs:
                node.reset()

    @classmethod
    def handle_node_changed(cls, key):
        for node in Node.nodes.values():
            if key in node.inputs:
                node.reset()


ltk.subscribe(
    constants.PUBSUB_DAG_ID, ltk.TOPIC_WORKER_RESULT, Formula.handle_job_result
)
ltk.subscribe(
    constants.PUBSUB_DAG_ID, constants.TOPIC_CELL_CHANGED, Formula.handle_cell_changed
)


def create(key, value):
    if isinstance(value, dict):
        script, kind, value = (
            value[constants.DATA_KEY_VALUE_FORMULA],
            value.get(constants.DATA_KEY_VALUE_KIND, None),
            value.get(constants.DATA_KEY_VALUE_PREVIEW, None),
        )
    else:
        script, kind, value = value, None, None
    if isinstance(script, str) and script.startswith("="):
        node = Formula(key, script, kind, value)
    else:
        types = {
            str: String,
            int: Number,
            float: Number,
            bool: Boolean,
        }
        node = types[type(script)](key, script)
    return node


def worker_ready(data):
    state.worker_ready[id(worker)] = True
    version = data[1:].split()[0]
    state.console.write(
        "worker", f"Browser Worker: Pyton={version}. VM={state.vm_type(data)}."
    )
    for node in Node.nodes.values():
        node.reload()


ltk.subscribe(constants.PUBSUB_DAG_ID, ltk.pubsub.TOPIC_WORKER_READY, worker_ready)


