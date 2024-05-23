import base64
import io
import json
import ltk
import pyscript # type: ignore
import time

window = pyscript.window


def edit_script(script): # TODO: use ast to parse script
    lines = script.strip().split("\n")
    if lines[-1].startswith("import ") or lines[-1].startswith("from "):
        lines.append("_=None")
    else:
        lines[-1] = f"_={lines[-1]}"
    return "\n".join(lines)


def to_js(python_object):
    if python_object.__class__.__name__ == "jsobj":
        return python_object
    return window.to_js(json.dumps(python_object))

def get_col_row(key):
    column = ''
    row = ''
    for char in key:
        if char.isdigit():
            row += char
        else:
            column += char

    # Convert column letters to a column index (1-based)
    column_index = 0
    for i, c in enumerate(reversed(column)):
        column_index += (ord(c) - ord('A') + 1) * (26 ** i)

    return column_index, int(row)


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
        url = f"/load?u={window.encodeURIComponent(url)}"

    return base64.b64decode(get(window.addToken(url)))
   

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
        start_col, start_row = get_col_row(start)
        end_col, end_row = get_col_row(end)

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

    def set_cell(self, column, row, value):
        cell = self.cell(self.get_key(column, row))
        cell.set(f"={repr(value)}")
        cell.evaluate()
    
    def get_key(self, column, row):
        return window.getKeyFromColumnRow(column, row)

    def load(self, url, handler=None):
        if handler:
            ltk.get(window.addToken(url), lambda data: handler(data))
        else:
            return urlopen(url)

    def load_sheet(self, url):
        import pandas as pd
        try:
            data = urlopen(url)
            return pd.read_excel(data, engine='openpyxl')
        except:
            try:
                return pd.read_csv(data)
            except Exception as e:
                return f"Cannot load {url}: {type(e)}: {e}"


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

