import base64
import functools
import io
import json
import ltk
import pyscript # type: ignore
import re
import time


window = pyscript.window
cache = functools.cache if hasattr(functools, "cache") else lambda func: func

@cache
def get_col_row_from_key(key):
    row = 0
    col = 0
    for c in key:
        if c.isdigit():
            row = row * 10 + int(c)
        else:
            col = col * 26 + ord(c) - ord("A") + 1
    return col, row


@cache
def get_column_name(col):
    parts = []
    while col > 0:
        col, remainder = divmod(col - 1, 26)
        parts.insert(0, chr(remainder + ord("A")))
    return "".join(parts)


@cache
def get_key_from_col_row(col, row):
    return f"{get_column_name(col)}{row}"


cell_reference = re.compile("^[A-Z]+[0-9]+$")
cell_range_reference = re.compile("^[A-Z]+[0-9]+ *: *[A-Z]+[0-9]+$")


def is_cell_reference(s):
    return isinstance(s, str) and re.match(cell_reference, s)


def is_cell_range_reference(s):
    return isinstance(s, str) and re.match(cell_range_reference, s)


def find_inputs(script):
    import ast
    class InputFinder(ast.NodeVisitor):
        inputs = set()

        def __init__(self, script):
            self.visit(ast.parse(script))

        def add_input(self, s):
            if is_cell_reference(s):
                self.inputs.add(s)

        def visit_Name(self, node):
            if isinstance(node.ctx, ast.Load):
                self.add_input(node.id)
            return node

        def visit_Constant(self, node):
            if is_cell_range_reference(node.value):
                start, end = node.value.split(":")
                start = start.strip()
                end = end.strip()
                start_col, start_row = get_col_row_from_key(start)
                end_col, end_row = get_col_row_from_key(end)
                for col in range(start_col, end_col + 1):
                    for row in range(start_row, end_row + 1):
                        self.add_input(get_key_from_col_row(col, row))
            return node

        def generic_visit(self, node):
            super().generic_visit(node)

    return list(InputFinder(script).inputs)


def intercept_last_expression(script):
    import ast
    if not script:
        return ""
    tree = ast.parse(script)
    last = tree.body[-1]
    lines = script.split("\n")
    if isinstance(last, (ast.Expr, ast.Assign)):
        lines[last.lineno - 1] = f"_ = {lines[last.lineno - 1]}"
    else:
        lines.append("_ = None")
    return "\n".join(lines)


def to_js(python_object):
    if python_object.__class__.__name__ == "jsobj":
        return python_object
    return window.to_js(json.dumps(python_object))


def index_to_col(index):
    col = ''
    index -= 1
    while index >= 0:
        col = chr(index % 26 + ord('A')) + col
        index = index // 26 - 1
    return col

def wrap_as_file(content):
    try:
        return io.BytesIO(content)
    except:
        return io.StringIO(content)


def shorten(s, length):
    return f"{s[:length - 3]}{s[length - 3:] and '...'}"


network_cache = {}


def load_with_trampoline(url):
    def get(url):
        if url in network_cache:
            when, value = network_cache[url]
            if time.time() - when < 60:
                return value

        xhr = window.XMLHttpRequest.new()
        xhr.open("GET", url, False)
        xhr.send(None)
        if xhr.status != 200:
            raise IOError(f"HTTP Error: {xhr.status} for {url}")
        value = xhr.responseText
        network_cache[url] = time.time(), value 
        return value

    if url and url[0] != "/":
        url = f"/load?url={window.encodeURIComponent(url)}"

    return base64.b64decode(get(url))
   

try:
    def urlopen(url, data=None, timeout=3, *, cafile=None, capath=None, cadefault=False, context=None):
        return wrap_as_file(load_with_trampoline(url))

    import urllib.request
    urllib.request.urlopen = urlopen
except:
    pass

class PySheets():
    def __init__(self, spreadsheet=None, inputs=[]):
        self._spreadsheet = spreadsheet
        self._inputs = inputs

    def sheet(self, selection, headers=True):
        import pandas as pd

        start, end = selection.split(":")
        start_col, start_row = get_col_row_from_key(start)
        end_col, end_row = get_col_row_from_key(end)

        data = {}
        for col in range(start_col, end_col + 1):
            keys = [
                f"{index_to_col(col)}{row}" for row in range(start_row, end_row + 1)
            ]
            values = [ self._inputs.get(key, "") for key in keys ]
            header = values.pop(0) if headers else f"col-{col}"
            data[header] = values
        df = pd.DataFrame.from_dict(data)
        if not isinstance(df, pd.DataFrame):
            return "Error: Incomplete Data"
        return df

    def cell(self, key):
        return self._spreadsheet.get(key) if self._spreadsheet else window.jQuery(f"#{key}")

    def set_cell(self, key, value):
        cell = self.cell(key)
        cell.text(f"{repr(value)}")
        cell.attr("worker-set", f"{repr(value)}")
    
    def get_key(self, column, row):
        return window.getKeyFromColumnRow(column, row)

    def load(self, url, handler=None):
        if handler:
            ltk.get(url, lambda data: handler(data))
        else:
            return urlopen(url)

    def load_sheet(self, url):
        import pandas as pd
        try:
            data = urlopen(url)
        except Exception as e:
            raise ValueError(f"Cannot load url: {e}")
        try:
            return pd.read_excel(data, engine='openpyxl')
        except:
            try:
                return pd.read_csv(data)
            except Exception as e:
                raise ValueError(f"Unsupported formet. Can only load data in Excel or CSV format: {e}")


def get_dict_table(result):
    return "".join([
        "<table border='1' class='dict_table'>",
            "<thead>",
                "<tr><th>key</th><th>value</th></tr>",
            "</thead>",
            "<tbody>",
                "".join(f"<tr><td>{key}</td><td>{get_dict_table(value)}</td></tr>" for key, value in result.items()),
            "</thead>",
        "</table>",
    ]) if isinstance(result, dict) else repr(result)

