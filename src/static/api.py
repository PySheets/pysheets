"""
Copyright (c) 2024 laffra - All Rights Reserved. 

Utility functions for working with spreadsheets used by both the worker and the UI.
"""

import base64
import functools
import io
import json
import re
import time

import constants

import ltk

import polyscript # type: ignore    pylint: disable=import-error


cache = functools.cache if hasattr(functools, "cache") else lambda func: func

@cache
def get_col_row_from_key(key: str):
    """
    Converts a cell reference key (e.g. "A1", "BC45") to the corresponding column and row indices.
    
    Args:
        key (str): The cell reference key to convert.
    
    Returns:
        Tuple[int, int]: The column and row indices corresponding to the input cell reference key.
    """
    row = 0
    col = 0
    for c in key:
        if c.isdigit():
            row = row * 10 + int(c)
        else:
            col = col * 26 + ord(c) - ord("A") + 1
    return col, row


@cache
def get_column_name(col: int):
    """
    Converts a column index to its corresponding column name.
    
    Args:
        col (int): The column index to convert.
    
    Returns:
        str: The column name corresponding to the input column index.
    """
    parts = []
    while col > 0:
        col, remainder = divmod(col - 1, 26)
        parts.insert(0, chr(remainder + ord("A")))
    return "".join(parts)


@cache
def get_key_from_col_row(col: int, row: int):
    """
    Converts a column and row index to the corresponding cell reference key.
    
    Args:
        col (int): The column index.
        row (int): The row index.
    
    Returns:
        str: The cell reference key (e.g. "A1", "BC45") corresponding to the input column and row indices.
    """
    return f"{get_column_name(col)}{row}"


cell_reference = re.compile("^[A-Z]+[0-9]+$")
cell_range_reference = re.compile("^[A-Z]+[0-9]+ *: *[A-Z]+[0-9]+$")


def convert(value: str):
    """
    Attempts to convert the given `value` to a float if it contains a decimal point, otherwise to an integer.
    If the conversion fails, returns the original `value` if it is truthy, otherwise 0.
    
    Args:
        value (str): The value to be converted.
    
    Returns:
        Union[float, int, str]: The converted value, or the original value if conversion fails.
    """
    try:
        return float(value) if "." in value else int(value)
    except ValueError:
        return value if value else 0


def rgb_to_hex(rgb):
    """
    Converts an RGB color tuple to a hexadecimal color string.
    
    Args:
        rgb (str): An RGB color tuple in the format "(r, g, b)".
    
    Returns:
        str: The hexadecimal color string in the format "#RRGGBB".
    """
    try:
        r, g, b = map(int, rgb[4:-1].split(", "))
        return f"#{r:02x}{g:02x}{b:02x}"
    except ValueError:
        return "#FF3333"


def is_cell_reference(s: str):
    """
    Checks if the given string `s` is a valid cell reference.
    
    A cell reference is a string that represents a single cell in a spreadsheet, such as "A1", "BC45", etc.
    
    Args:
        s (str): The string to check.
    
    Returns:
        bool: True if `s` is a valid cell reference, False otherwise.
    """
    return isinstance(s, str) and re.match(cell_reference, s)


def is_cell_range_reference(s: str):
    """
    Checks if the given string `s` is a valid cell range reference.
    
    A cell range reference is a string that represents a range of cells in a spreadsheet,
    such as "A1:B2", "BC45:DE67", etc.
    
    Args:
        s (str): The string to check.
    
    Returns:
        bool: True if `s` is a valid cell range reference, False otherwise.
    """
    return isinstance(s, str) and re.match(cell_range_reference, s)


def find_inputs(script: str):
    """
    Finds all the input cell references in the given Python script.
    
    This function uses the `ast` module to parse the script and visit each node in
    the abstract syntax tree. It identifies any names that represent cell references
    and any constant values that represent cell range references, and adds them to a set of
    input cell references.
    
    Args:
        script (str): The Python script to analyze.
    
    Returns:
        list: A list of all the input cell references found in the script.
    """
    import ast # pylint: disable=import-outside-toplevel

    class InputFinder(ast.NodeVisitor):
        """
        A class that visits the nodes of a Python script's abstract syntax tree
        (AST) to find all the input cell references in the script.
        """
        inputs = set()

        def __init__(self, script):
            self.visit(ast.parse(script))

        def add_input(self, s):
            """ Adds an input key to the set of input keys. """
            if is_cell_reference(s):
                self.inputs.add(s)

        def visit_Name(self, node): # pylint: disable=invalid-name
            """ Visit an ast.Name node """
            if isinstance(node.ctx, ast.Load):
                self.add_input(node.id)
            return node

        def visit_Constant(self, node): # pylint: disable=invalid-name
            """ Visit an ast.Constant node """
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

    try:
        return list(InputFinder(script).inputs)
    except SyntaxError:
        return []


def intercept_last_expression(script):
    """
    Intercepts the last expression in the given Python script and assigns it to the variable `_`.
    
    Args:
        script (str): The Python script to analyze.
    
    Returns:
        str: The modified script with the last expression assigned to `_`.
    """
    import ast # pylint: disable=import-outside-toplevel
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
    """
    Converts a Python object to a JavaScript object.
    
    Args:
        python_object (Any): The Python object to be converted.
    
    Returns:
        Any: The JavaScript representation of the Python object. If the input is already a
                JavaScript object, it is returned as-is.
    """
    if python_object.__class__.__name__ == "jsobj":
        return python_object
    return ltk.window.to_js(json.dumps(python_object))


def index_to_col(index: int):
    """
    Converts a numerical index to a column letter in a spreadsheet-like format.
    
    Args:
        index (int): The numerical index to convert to a column letter.
    
    Returns:
        str: The column letter corresponding to the given index.
    """
    col = ''
    index -= 1
    while index >= 0:
        col = chr(index % 26 + ord('A')) + col
        index = index // 26 - 1
    return col

def wrap_as_file(content):
    """
    Wraps the provided content as a file-like object.
    
    Args:
        content (bytes or str): The content to be wrapped as a file-like object.
    
    Returns:
        file-like object: A file-like object containing the provided content.
    """
    return io.StringIO(content) if isinstance(content, str) else io.BytesIO(content)


def shorten(s: str, length: int):
    """
    Shortens a given string to a maximum length, appending an ellipsis if the string is truncated.
    
    Args:
        s (str): The input string to be shortened.
        length (int): The maximum length of the output string.
    
    Returns:
        str: The shortened string, with an ellipsis appended if the string was truncated.
    """
    return f"{s[:length - 3]}{s[length - 3:] and '...'}"


network_cache = {}


def load_with_trampoline(url):
    """
    Loads the content from the provided URL using a trampoline mechanism to cache the response.
    
    Args:
        url (str): The URL to load the content from.
    
    Returns:
        bytes: The decoded content from the URL.
    
    This function first checks if the URL is already cached in the `network_cache` dictionary.
    If the cached content is less than 60 seconds old, it returns the cached value.
    Otherwise, it makes a GET request to the URL using `window.XMLHttpRequest` and caches
    the response text. If the HTTP status code is not 200, it raises an `IOError` with the status code.
    """
    def get(url):
        if url in network_cache:
            when, value = network_cache[url]
            if time.time() - when < 60:
                return value

        xhr = ltk.window.XMLHttpRequest.new()
        xhr.open("GET", url, False)
        xhr.send(None)
        if xhr.status != 200:
            raise IOError(f"HTTP Error: {xhr.status} for {url}")
        value = xhr.responseText
        network_cache[url] = time.time(), value
        return value

    if url and url[0] != "/":
        url = f"/load?url={ltk.window.encodeURIComponent(url)}"

    content = base64.b64decode(get(url))
    return content


try:
    import urllib.request

    def urlopen(url, **args): # pylint: disable=unused-argument
        """ Patch request.urlopen to bypass CORS restrictions. """
        return wrap_as_file(load_with_trampoline(url))

    urllib.request.urlopen = urlopen
except ImportError:
    pass


class PySheets():
    """
    A class that provides a simple interface for working with spreadsheet data.
    
    The `PySheets` class provides methods for loading, accessing, and modifying spreadsheet data.
    It supports loading data from URLs and provides a convenient way to work with the data as a Pandas DataFrame.
    """
    def __init__(self, spreadsheet=None, inputs=None):
        self._spreadsheet = spreadsheet
        self._inputs = inputs or []
        self._cells_to_set = {}

    def get_sheet(self, selection:str, headers:bool=True):   # pylint: disable=too-many-locals
        """
        Generates a Pandas DataFrame from a spreadsheet selection.
        
        Args:
            selection (str): A string representing the spreadsheet selection, in the format "start_key:end_key".
            headers (bool): If True, the first row of the selection is used as the column headers.
        
        Returns:
            pandas.DataFrame: A Pandas DataFrame containing the data from the specified spreadsheet selection.
        """
        assert isinstance(selection, str), f"Parameter selection must be a str, not {type(selection)}"
        assert isinstance(headers, bool), f"Parameter headers must be a bool, not {type(headers)}"
        import pandas as pd # pylint: disable=import-outside-toplevel,import-error

        try:
            start, end = selection.split(":")
            start_col, start_row = get_col_row_from_key(start)
            end_col, end_row = get_col_row_from_key(end)
        except Exception as exc: # pylint: disable=broad-except
            raise ValueError(f"Parameter selection must be a range like 'A1:F14', not {selection}") from exc

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

    def get_cell(self, key:str):
        """
        Returns the cell object for the given key.
        
        If the spreadsheet is set, it retrieves the cell object from the spreadsheet. Otherwise,
        it uses jQuery to select the cell element by its ID.
        
        Args:
            key (str): The key of the cell to retrieve.
        
        Returns:
            object: The cell object for the given key.
        """
        assert isinstance(key, str), f"Parameter key must be a str, not {type(key)}"
        return self._spreadsheet.get(key) if self._spreadsheet else ltk.window.jQuery(f"#{key}")

    def set_cell(self, key, value, flush=True):
        """
        Sets the value of a cell in the spreadsheet.

        This call happens in the worker and needs to be sent to the UI. To improve
        performance, we bundle up all cells being set in the current execution
        and send them to the UI.
        
        Args:
            key (str): The key of the cell to set.
            value (object): The value to set the cell to.
        """
        assert isinstance(key, str), f"Parameter key must be a str, not {type(key)}"
        assert isinstance(value, (int, float, str)), f"Parameter value must be a str/int/float, not {type(key)}"
        self._cells_to_set[key] = value if isinstance(value, (int, float)) else str(value)
        if flush:
            ltk.schedule(lambda: self._flush_set_cells(), "flushing cells to set") # pylint: disable=unnecessary-lambda

    def _flush_set_cells(self):
        """
        Sets the value of a cell in the spreadsheet.
        """
        polyscript.xworker.sync.publish(
            "Worker",
            "Application",
            constants.TOPIC_API_SET_CELLS,
            json.dumps(self._cells_to_set)
        )
        self._cells_to_set.clear()

    def get_col_row_from_key(self, key:str):
        """
        Returns the column and row for the given key.

        Args:
            key (str): The key to get the column and row for.

        Returns:
            tuple: A tuple containing the column and row for the given key.
        """
        assert isinstance(key, str), f"Parameter key must be a str, not {type(key)}"
        return get_col_row_from_key(key)

    def get_key(self, column:int, row:int):
        """
        Returns the key for the given column and row.
        
        Args:
            column (int): The column index.
            row (int): The row index.
        
        Returns:
            str: The key for the given column and row.
        """
        assert isinstance(column, int), f"Parameter column must be an integer, not {type(column)}"
        assert isinstance(row, int), f"Parameter row must be an integer, not {type(row)}"
        return ltk.window.getKeyFromColumnRow(column, row)

    def load_url(self, url:str, handler:callable=None):
        """
        Loads data from the provided URL synchronously. To make the call asynchronous,
        pass a handler function to be called when the data is available.
        
        Args:
            url (str): The URL to load data from.
            handler (callable, optional): A function to call with the loaded data.
                    If not provided, the function will simply return the loaded data.
        
        Returns:
            object: The loaded data, or the result of calling the handler function.
        """
        assert isinstance(url, str), f"Parameter url must be a str, not {type(url)}"
        if handler:
            return ltk.get(url, handler)
        return urlopen(url)

    def load_sheet(self, url:str):
        """
        Loads data from the provided URL and attempts to read it as an Excel or CSV file.
        
        Args:
            url (str): The URL to load data from.
        
        Returns:
            pandas.DataFrame: The loaded data as a pandas DataFrame.
        
        Raises:
            ValueError: If the URL cannot be loaded or the data cannot be parsed as an Excel or CSV file.
        """
        assert isinstance(url, str), f"Parameter url must be a str, not {type(url)}"
        import pandas as pd # pylint: disable=import-outside-toplevel,import-error
        try:
            data = urlopen(url).read()
        except Exception as e: # pylint: disable=broad-except
            raise ValueError(f"Cannot load url: {e}") from e
        try:
            return pd.read_csv(io.StringIO(data.decode("utf-8")))
        except Exception as e1: # pylint: disable=broad-except
            try:
                return pd.read_excel(data, engine='openpyxl')
            except Exception as e2:
                print(e2, url, data)
                raise ValueError(f"Cannot load as Excel ({e1}) or CSV ({e2})") from e2

    def import_csv(self, url:str, start_key:str):
        """
        Imports CSV data from the provided URL and set the values in the spreadsheet.

        Args:
            url (str): The URL to load data from.
            start_key (str): The key for thw starting cell to insert the data into.
        """
        assert isinstance(url, str), f"Parameter url must be a str, not {type(url)}"
        assert isinstance(start_key, str), f"Parameter start_key must be a str, not {type(start_key)}"
        start_col, start_row = get_col_row_from_key(start_key)
        content = urlopen(url).read().decode("utf-8")
        skip_row_id = False
        for row, line in enumerate(content.split("\n")):
            for col, value in enumerate(line.split(",")):
                if col == 0:
                    if value == "csvbase_row_id":
                        skip_row_id = True
                    if skip_row_id:
                        continue
                self.set_cell(
                    f"{get_column_name(start_col + col - (1 if skip_row_id else 0))}{start_row + row}", 
                    value,
                    False
                )
        summary = f"[{len(self._cells_to_set)} cells]"
        self._flush_set_cells()
        return summary


def get_dict_table(result):
    """
    Recursively generates an HTML table representation of a dictionary.
    
    Args:
        result (dict): The dictionary to be represented as an HTML table.
    
    Returns:
        str: An HTML table representation of the input dictionary.
    """
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
