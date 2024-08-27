"""
Copyright (c) 2024 laffra - All Rights Reserved. 

This module defines various classes and functions related to the serialization and
deserialization of models, as well as utility functions for working with cells,
columns, and rows in a spreadsheet-like data structure.
"""

import json

import api
try:
    import constants
except ImportError:
    from static import constants



def encode(model):
    """
    Encodes a model object into a string representation.
    
    Args:
        model (object): The model object to be encoded.
    
    Returns:
        str: The string representation of the model object, with newline and tab characters escaped.
    """
    buffer = []
    model.encode(buffer)
    return "".join(buffer)


def decode(json_string):
    """
    Decodes a JSON string representation of a model object and returns the corresponding model instance.
    
    Args:
        json_string (str): The JSON string representation of the model object.
    
    Returns:
        object: The model object instance.
    
    Raises:
        Exception: If the JSON string is corrupt or cannot be parsed.
    """
    try:
        model_dict = json.loads(json_string.replace("\t", "\\t"))
    except json.JSONDecodeError as error:
        print("Corrupt json:")
        for lineno, line in enumerate(json_string.split("\n")):
            print(f"{lineno+1:5d}", line)
        ch = int(str(error).split()[-1][:-1])
        print("char", ch, repr(json_string[ch]))
        raise
    return convert(model_dict)


def convert(model_dict):
    """
    Converts a model dictionary into an instance of the corresponding model class.
    
    Args:
        model_dict (dict): A dictionary representation of the model object.
        env (dict, optional): A dictionary mapping class names to their corresponding
            classes, used to resolve the class of the model object. Defaults to an empty dictionary.
    
    Returns:
        object: An instance of the model class represented by the input dictionary.
    """
    if "_listeners" in model_dict:
        del model_dict["_listeners"]
    class_name = model_dict["_"]
    if "_" in model_dict:
        del model_dict["_"]
    clazz = globals()[class_name]
    return clazz(**model_dict)


def escape(value: str):
    """
    Escapes a string value by replacing special characters with their escaped counterparts.
    
    Args:
        value (str): The string value to be escaped.
    
    Returns:
        str: The escaped string value.
    """
    if not isinstance(value, str):
        return value
    return json.dumps(value)


def get_sheet(data, uid=None):
    """
    Attempts to decode the provided data into a Sheet object. If the data is empty,
    creates a new Sheet object with the given uid. If the data cannot be decoded,
    prints the data and raises the original exception.
    
    Args:
        data (str): The serialized data to decode into a Sheet object.
        uid (str, optional): The uid to use for the Sheet object if the data is empty. Defaults to None.
    
    Returns:
        Sheet: The decoded Sheet object, or a new Sheet object if the data is empty.
    """
    try:
        return decode(data) if data else Sheet(uid=uid)
    except:
        print("Could not load data", e)
        for lineno,line in enumerate(data.split("\n"), 1):
            print(lineno, line)
        raise



class SerializableDict(dict):
    """
    A serializable dictionary class that provides additional functionality beyond the built-in `dict` class.
    """
    def __init__(self):
        super().__init__()
        self._ = self.__class__.__name__

    def __setattr__(self, name: str, value):
        old_value = getattr(self, name, None)
        if old_value == value:
            return
        object.__setattr__(self, name, value)
        self[name] = value

    def encode(self, buffer: list):
        """
        Encodes the fields of the object into a JSON-formatted string and appends it to the provided buffer.
        
        Args:
            buffer (list): The list to append the encoded fields to.
        """
        buffer.append("{")
        buffer.append(f'"_":"{SHORT_CLASS_NAMES[self.__class__.__name__]}",')
        self.encode_fields(buffer)
        buffer.append("}")

    def encode_fields(self, buffer: list):
        """
        Encodes the fields of the object into a JSON-formatted string and appends it to the provided buffer.
        
        Args:
            buffer (list): The list to append the encoded fields to.
        """
        data_fields = [(key,value) for key,value in self.__dict__.items() if not key.startswith("_")]
        buffer.append(",".join([f'"{key}":{json.dumps(value)}' for key, value in data_fields]))

    def notify_listeners(self, info):
        """
        Notifies all registered listeners of the changes made to the model.
        
        Args:
            info (dict): A dictionary containing information about the changes made to the model.
        """



class Model(SerializableDict):
    """
    A base class for serializable models that provides functionality for notifying listeners of changes to the model.
    """
    def __init__(self):
        super().__init__()
        self._listeners = []

    def listen(self, callback):
        """
        Registers a listener callback function that will be notified of changes to the model.
        
        Args:
            callback (callable): A function that will be called when the model is updated.
            The function should accept two arguments: the model instance and a dictionary
            containing information about the changes made to the model.
        """
        self._listeners.append(callback)

    def __setattr__(self, name: str, value):
        super().__setattr__(name, value)
        if not name.startswith("_"):
            self.notify_listeners({ "name": name })

    def notify(self, listener, info):
        """
        Notifies a registered listener callback function of changes made to the model.

        Args:
            listener (callable): The listener callback function to be notified.
            info (dict): A dictionary containing information about the changes made to the model.
        """
        listener(self, info) # we are running in the server or as unit test

    def notify_listeners(self, info):
        """
        Notifies all registered listeners of the changes made to the model.
        
        Args:
            info (dict): A dictionary containing information about the changes made to the model.
        """
        for listener in self._listeners:
            self.notify(listener, info)


class Sheet(Model):  # pylint: disable=too-many-instance-attributes
    """
    A class representing a sheet in a spreadsheet-like application.
    
    The `Sheet` class is a subclass of the `Model` class and provides functionality
    for managing the cells, columns, rows, and previews within a sheet.
    It includes methods for converting and encoding the sheet's data, as well as 
    retrieving specific cells and previews.
    """
    def __init__(self, uid="", name="Untitled Sheet",    # pylint: disable=too-many-arguments
                 columns=None, rows=None, cells=None, previews=None,
                 selected="A1", screenshot="/screenshot.png",
                 created_timestamp=0, updated_timestamp=0,
                 column_count=constants.DEFAULT_COLUMN_COUNT,
                 row_count=constants.DEFAULT_ROW_COUNT,
                 packages="",
                 _class="Sheet", _="Sheet"):
        super().__init__()
        self.uid = uid
        self.name = name
        self.columns = {} if columns is None else columns
        self.rows = {} if rows is None else rows
        self.cells = self.convert_cells({} if cells is None else cells)
        self.previews = self.convert_previews({} if previews is None else previews)
        self.selected = selected
        self.screenshot = screenshot
        self.created_timestamp = created_timestamp
        self.updated_timestamp = updated_timestamp
        self.column_count = column_count
        self.row_count = row_count
        self.packages = packages

    def convert_cells(self, cells):
        """
        Converts a dictionary of stored cell data into a dictionary of live `Cell` objects.
        
        Args:
            cells (dict[str:dict]): A dictionary of cell keys to cell dictionaries.
        
        Returns:
            dict: A dictionary where the keys are cell keys and the values are `Cell` objects.
        """
        for key, cell_dict in cells.items():
            if not isinstance(cell_dict, Cell):
                cells[key] = Cell(**cell_dict)
        return cells

    def encode_fields(self, buffer: list):
        """
        Encodes the fields of the Sheet object into a buffer.
        
        Args:
            buffer (list): A list to which the encoded fields will be appended.
        """
        self.encode_cells(buffer)
        self.encode_previews(buffer)
        self.row_count = max([constants.DEFAULT_ROW_COUNT] + [cell.row for cell in self.cells.values()])
        self.column_count = max([constants.DEFAULT_COLUMN_COUNT] + [cell.column for cell in self.cells.values()])
        buffer.append(f'"created_timestamp":{json.dumps(self.created_timestamp)},')
        buffer.append(f'"updated_timestamp":{json.dumps(self.updated_timestamp)},')
        buffer.append(f'"rows":{json.dumps(self.rows)},')
        buffer.append(f'"columns":{json.dumps(self.columns)},')
        buffer.append(f'"row_count":{json.dumps(self.row_count)},')
        buffer.append(f'"column_count":{json.dumps(self.column_count)},')
        buffer.append(f'"screenshot":{json.dumps(self.screenshot)},')
        buffer.append(f'"packages":{json.dumps(self.packages)},')
        buffer.append(f'"selected":{json.dumps(self.selected)},')
        buffer.append(f'"uid":{json.dumps(self.uid)},')
        buffer.append(f'"name":{json.dumps(self.name)}')

    def encode_cells(self, buffer: list):
        """
        Encodes the cells of the Sheet object into a buffer.
        
        This method iterates through the cells of the Sheet object and appends
        the encoded cell data to the provided buffer list. It skips over any cells
        that have an empty script and value, as these are considered empty cells.
        
        Args:
            buffer (list): A list to which the encoded cell data will be appended.
        """
        buffer.append('"cells":{')
        needs_comma = False
        for cell in self.cells.values():
            if isinstance(cell, str) or not cell.has_changes():
                continue
            buffer.append(f"{',' if needs_comma else ''}{json.dumps(cell.key)}:")
            buffer.append("{")
            cell.encode_fields(buffer)
            buffer.append("}")
            needs_comma = True
        buffer.append('},')

    def encode_previews(self, buffer: list):
        """
        Encodes the previews of the Sheet object into a buffer.
        
        Args:
            buffer (list): A list to which the encoded preview data will be appended.
        """
        buffer.append('"previews":{')
        needs_comma = False
        for preview in self.previews.values():
            buffer.append(f"{',' if needs_comma else ''}{json.dumps(preview.key)}:")
            buffer.append("{")
            preview.encode_fields(buffer)
            buffer.append("}")
            needs_comma = True
        buffer.append('},')

    def convert_previews(self, previews):
        """
        Converts a dictionary of preview data into a dictionary of Preview objects.
        
        Args:
            previews (dict): A dictionary of preview data, where the keys are the preview keys
            and the values are dictionaries containing the preview properties.
        
        Returns:
            dict: A dictionary of Preview objects, where the keys are the preview keys and
            the values are the corresponding Preview objects.
        """
        self.previews = {}
        for key, preview_dict in previews.items():
            previews[key] = self.get_preview(**preview_dict)
        return previews

    def get_cell_keys(self, from_col, to_col, from_row, to_row):
        """
        Gets a list of cell keys for the specified column and row range.
        
        Args:
            from_col (int): The starting column index (inclusive).
            to_col (int): The ending column index (inclusive).
            from_row (int): The starting row index (inclusive).
            to_row (int): The ending row index (inclusive).
        
        Returns:
            list: A list of cell keys for the specified range.
        """
        assert from_col, f"from_col should be >=1 not {from_col}"
        assert to_col, f"from_col should be >=1 not {to_col}"
        assert from_row, f"from_col should be >=1 not {from_row}"
        assert to_row, f"from_col should be >=1 not {to_row}"
        keys = []
        for col in range(from_col, to_col + 1):
            for row in range(from_row, to_row + 1):
                keys.append(api.get_key_from_col_row(col, row))
        return keys

    def get_cell(self, key):
        """
        Gets a cell from the sheet, creating a new cell if it doesn't exist.
        
        Args:
            key (str): The key of the cell to get.
        
        Returns:
            Cell: The cell with the specified key.
        """
        if not key in self.cells:
            cell = Cell(key=key)
            self.cells[key] = cell
            self.row_count = max(self.row_count, cell.row)
            self.column_count = max(self.column_count, cell.column)
        return self.cells[key]

    def get_preview(self, key, **args):
        """
        Gets a Preview object for the given key, creating a new one if it doesn't exist.
        
        Args:
            key (str): The key of the Preview object to get.
            **args: Additional keyword arguments to pass to the Preview constructor.
        
        Returns:
            Preview: The Preview object for the given key.
        """
        if not key in self.previews:
            self.previews[key] = Preview(key, **args)
        return self.previews[key]

    def set_column_width(self, column, width):
        """ 
        Set the column width
        """
        self.columns[column] = width
        self.notify_listeners({ "name": "columns", "column": column, "width": width })

    def set_row_height(self, row, height):
        """ 
        Set the row height
        """
        self.rows[row] = height
        self.notify_listeners({ "name": "rows", "row": row, "height": height })

    def __eq__(self, other):
        return isinstance(other, Sheet) and other.uid == self.uid


class Preview(Model):
    """
    Represents a preview of a cell's content, such as a MatplotLib element.
    
    Args:
        key (str): The unique key for this preview.
        html (str): The HTML content to display in the preview.
        left (int): The left position of the preview, in pixels.
        top (int): The top position of the preview, in pixels.
        width (int): The width of the preview, in pixels.
        height (int): The height of the preview, in pixels.
    """
    def __init__(self, key, html="", left=0, top=0, width=0, height=0):    # pylint: disable=too-many-arguments
        super().__init__()
        self.key = key
        self.html = html
        self.left = left
        self.top = top
        self.width = width
        self.height = height

    def encode_fields(self, buffer: list):
        html = f"Loading {len(self.html):,} bytes..." if len(self.html) > constants.LARGE_PREVIEW_SIZE else self.html
        buffer.append(f'"html":{json.dumps(html)},')
        buffer.append(f'"left":{json.dumps(self.left)},')
        buffer.append(f'"top":{json.dumps(self.top)},')
        buffer.append(f'"width":{json.dumps(self.width)},')
        buffer.append(f'"height":{json.dumps(self.height)},')
        buffer.append(f'"key":{json.dumps(self.key)}')


class Cell(Model):
    """
    Represents the model for a cell in a sheet.
    """
    def __init__(self,  # pylint: disable=too-many-arguments,redefined-outer-name
                 key="", column=0, row=0, value="", script="", s="",
                 style=None, _class="Cell", _="Cell", k="", prompt=""):  # pylint: disable=redefined-outer-name
        super().__init__()
        self.key = key or k
        if not row or not column:
            column, row = api.get_col_row_from_key(key)
        self.column = column
        self.row = row
        self.value = value
        self.script = script or s or value
        self.prompt = prompt
        self.style = {} if style is None else style

    def has_changes(self):
        """ 
        Checks if the cell has any changes.
        """
        return self.value or self.script or self.style

    def encode_fields(self, buffer: list):
        """
        Encodes the fields of the Cell model instance into a list of JSON-formatted strings.
        
        Args:
            buffer (list): A list to append the encoded fields to.
        """
        if self.value not in ["", self.script]:
            buffer.append(f'"value":{escape(self.value)},')
        if self.prompt:
            buffer.append(f'"prompt":{escape(self.prompt)},')
        buffer.append(f'"key":"{self.key}",')
        self.encode_style(buffer)
        buffer.append(f'"s":{escape(self.script)}')

    def encode_style(self, buffer: list):
        """
        Encodes the style properties of the model instance into a list of JSON-formatted strings.
        
        Args:
            buffer (list): A list to append the encoded style properties to.
        """
        styles = []
        for prop, value in self.style.items():
            if value != constants.DEFAULT_STYLE.get(prop):
                styles.append(f'"{prop}":{escape(value)}')
        if styles:
            buffer.append('"style":{')
            buffer.append(f'{",".join(styles)}')
            buffer.append('},')

    def clear(self, sheet):
        """
        Clears the state of the Cell model instance, including resetting the script,
        prompt, value, style, and removing the cell from the sheet's previews.
        
        Args:
            sheet (Sheet): The Sheet instance that the Cell is associated with.
        """
        if self.script:
            self.script = ""
        if self.prompt:
            self.prompt = ""
        if self.value:
            self.value = ""
        if self.style:
            self.style = {}
        if self.key in sheet.previews:
            del sheet.previews[self.key]


class Edit(SerializableDict):
    """
    Base class for all Edit operations that can be applied to a Sheet.
    
    The `apply` and `undo` methods must be implemented by subclasses to define how
    the Edit is applied and undone on a Sheet instance.
    """
    def apply(self, sheet):
        """
        The `apply` method is responsible for applying the edit to the sheet, 
        and is implemented by each subclass to define the specific behavior of that edit.
        """
        raise NotImplementedError(f"{self.__class__.__name__}.apply")

    def undo(self, sheet):
        """
        This method is overridden by subclasses of `Edit` to provide the implementation
        for undoing the edit operation.
        """
        raise NotImplementedError(f"{self.__class__.__name__}.undo")

    def describe(self):
        """
        This method is overridden by subclasses of `Edit` to provide the implementation
        for describing what this edit does.
        """
        raise NotImplementedError(f"{self.__class__.__name__}.undo")


class EditGroup(Edit):
    """
    Represents a group of edits that can be undone as one.
    """
    def __init__(self, description):
        super().__init__()
        self.description = description
        self.edits = []

    def apply(self, sheet):
        for edit in self.edits:
            edit.apply(sheet)

    def undo(self, sheet):
        for edit in self.edits:
            edit.undo(sheet)

    def describe(self):
        return self.description

    def add(self, edit):
        """
        Add an edit to the current edit group.
        """
        self.edits.append(edit)


class EmptyEdit(Edit):
    """
    Represents an empty edit that does nothing.
    """
    def apply(self, sheet):
        pass

    def undo(self, sheet):
        pass

    def describe(self):
        return "Empty Edit"


class NameChanged(Edit):
    """
    Represents an edit to change the name of a Sheet.
    """
    def __init__(self, _name="", name=""):
        super().__init__()
        self._name = _name
        self.name = name

    def apply(self, sheet: Sheet):
        sheet.name = self.name
        return self

    def undo(self, sheet: Sheet):
        sheet.name = self._name
        return True

    def describe(self):
        return f"The sheet was renamed to '{self.name}'"


class SelectionChanged(Edit):
    """
    Represents an edit to change the selected cell in a Sheet.
    """
    def __init__(self, key=""):
        super().__init__()
        self.key = key

    def apply(self, sheet: Sheet):
        sheet.selected = self.key
        return self

    def undo(self, sheet: Sheet):
        return False

    def describe(self):
        return None


class ScreenshotChanged(Edit):
    """
    Represents an edit to change the screenshot of a Sheet.
    """
    def __init__(self, url=""):
        super().__init__()
        self.url = url

    def apply(self, sheet: Sheet):
        sheet.screenshot = self.url
        return self

    def undo(self, sheet: Sheet):
        return False

    def describe(self):
        return "A new screenshot was saved"


class PackagesChanged(Edit):
    """
    Represents an edit to change the sheet's packages.
    """
    def __init__(self, packages=""):
        super().__init__()
        self.packages = packages

    def apply(self, sheet: Sheet):
        sheet.packages = self.packages
        return self

    def undo(self, sheet: Sheet):
        return False

    def describe(self):
        return "The sheet's packages were changed"


class ColumnChanged(Edit):
    """
    Represents an edit to change the width of a column in a Sheet.
    """
    def __init__(self, column: int=0, width: int=0):
        super().__init__()
        self.column = str(column)
        self._width = self.width = width

    def apply(self, sheet: Sheet):
        self._width = sheet.columns.get(self.column, constants.DEFAULT_COLUMN_WIDTH)
        sheet.set_column_width(self.column, self.width)
        return self

    def undo(self, sheet: Sheet):
        sheet.set_column_width(self.column, self._width)
        return True

    def describe(self):
        return f"Column {api.get_column_name(int(self.column))}: Change width to {self.width}"


class RowChanged(Edit):
    """
    Represents an edit to change the height of a row in a Sheet.
    """
    def __init__(self, row=0, height=0):
        super().__init__()
        self.row = str(row)
        self._height = self.height = height

    def apply(self, sheet: Sheet):
        self._height = sheet.rows.get(self.row, constants.DEFAULT_ROW_HEIGHT)
        sheet.set_row_height(self.row, self.height)
        return self

    def undo(self, sheet: Sheet):
        sheet.set_row_height(self.row, self._height)
        return True

    def describe(self):
        return f"Row {self.row}: Change height to {self.height}"


class CellChanged(Edit):
    """
    Represents an edit to change the properties of a cell in a Sheet.
    """
    def __init__(self, key=""):
        super().__init__()
        self.key = key

    def apply(self, sheet: Sheet):
        cell = sheet.get_cell(self.key)
        for key, value in self.__dict__.items():
            if not key.startswith("_"):
                setattr(cell, key, value)
        return self

    def undo(self, sheet: Sheet):
        cell = sheet.get_cell(self.key)
        for key, value in self.__dict__.items():
            if key != "_" and key.startswith("_"):
                setattr(cell, key[1:], value)
        return True

    def describe(self):
        raise NotImplementedError("description")


class CellValueChanged(CellChanged):
    """
    Represents an edit to change the value of a cell in a Sheet.
    """
    def __init__(self, key="", _value="", value=""):
        super().__init__(key)
        self._value = _value
        self.value = value

    def describe(self):
        return f"{self.key}: change value to '{self.value}'"


class CellScriptChanged(CellChanged):
    """
    Represents an edit to change the script of a cell in a Sheet.
    """
    def __init__(self, key="", _script="", script=""):
        super().__init__(key)
        self._script = _script
        self.script = script

    def describe(self):
        return f"{self.key}: change script to '{self.script}'"


class CellStyleChanged(CellChanged):
    """
    Represents an edit to change the style of a cell in a Sheet.
    """
    def __init__(self, key="", _style=None, style=None):
        super().__init__(key)
        style = style or {}
        _style = _style or {}
        assert isinstance(_style, dict), f"_style must be a dict, not {type(_style)}:{_style}"
        assert isinstance(style, dict), f"style must be a dict, not {type(style)}:{style}"
        self._style = self.cleanup_style(_style)
        self.style = self.cleanup_style(style)

    def cleanup_style(self, style):
        """
        Removes any keys from the provided `style` dictionary that have an empty 
        value or a value that matches the default style value for that key.

        This is used specifically for cut-and-pasted content from Google Sheets.
        
        Args:
            style (dict): A dictionary of style properties and their values.
        
        Returns:
            dict: The cleaned up style dictionary, with any unnecessary keys removed.
        """
        for key, value in list(style.items()):
            if value == "" or value == constants.DEFAULT_STYLE.get(key):
                del style[key]
        return style

    def describe(self):
        return f"{self.key}: changed style to {self.style}"


class PreviewChanged(Edit):
    """
    Represents a change to a preview in a Sheet.
    """
    def __init__(self, key=""):
        super().__init__()
        self.key = key

    def apply(self, sheet: Sheet):
        assert isinstance(sheet, Sheet), f"sheet must be a Sheet, not {type(sheet)}:{sheet}"
        preview = sheet.get_preview(self.key)
        for key, value in self.__dict__.items():
            if not key.startswith("_"):
                setattr(preview, key, value)
        return self

    def undo(self, sheet: Sheet):
        return False

    def describe(self):
        raise NotImplementedError("description")


class PreviewPositionChanged(PreviewChanged):
    """
    Represents a change to the position of a preview in a Sheet.
    """
    def __init__(self, key="", _left=0, _top=0, left=0, top=0):
        super().__init__(key)
        self._left = _left
        self._top = _top
        self.left = left
        self.top = top

    def undo(self, sheet: Sheet):
        preview = sheet.previews[self.key]
        preview.left = self._left
        preview.top = self._top
        return True

    def describe(self):
        return f"{self.key}: Move the preview to [{self.left},{self.top}]"


class PreviewDimensionChanged(PreviewChanged):
    """
    Represents a change to the dimensions of a preview in a Sheet.
    """
    def __init__(self, key="", _width=0, _height=0, width=0, height=0):
        super().__init__(key)
        self._width = _width
        self._height = _height
        self.width = width
        self.height = height

    def undo(self, sheet: Sheet):
        preview = sheet.previews[self.key]
        preview.width = self._width
        preview.height = self._height
        return True

    def describe(self):
        return f"{self.key}: Resize the preview to [{self.width},{self.height}]"


class PreviewValueChanged(PreviewChanged):
    """
    Represents a change to the HTML content of a preview in a Sheet.
    """
    def __init__(self, key="", html=0):
        super().__init__(key)
        self.html = html

    def describe(self):
        return None


class PreviewDeleted(Edit):
    """
    Represents the deletion of a preview in a Sheet.
    """
    def __init__(self, key=""):
        super().__init__()
        self.key = key

    def apply(self, sheet: Sheet):
        if self.key in sheet.previews:
            del sheet.previews[self.key]
        return self

    def undo(self, sheet: Sheet):
        return False

    def describe(self):
        return None


#
# Generate short names to compress the model types when saved
#
a = CellValueChanged        # pylint: disable=invalid-name
c = CellScriptChanged       # pylint: disable=invalid-name
d = CellStyleChanged        # pylint: disable=invalid-name
e = SelectionChanged        # pylint: disable=invalid-name
f = ColumnChanged           # pylint: disable=invalid-name
g = RowChanged              # pylint: disable=invalid-name
h = ScreenshotChanged       # pylint: disable=invalid-name
i = PreviewChanged          # pylint: disable=invalid-name
j = PreviewPositionChanged  # pylint: disable=invalid-name
k = PreviewDimensionChanged # pylint: disable=invalid-name
l = PreviewValueChanged     # pylint: disable=invalid-name
m = PreviewDeleted          # pylint: disable=invalid-name
n = Sheet                   # pylint: disable=invalid-name
o = Cell                    # pylint: disable=invalid-name
p = NameChanged             # pylint: disable=invalid-name


SHORT_CLASS_NAMES = {
    "CellValueChanged": "a",
    "CellScriptChanged": "c",
    "CellStyleChanged": "d",
    "SelectionChanged": "e",
    "ColumnChanged": "f",
    "RowChanged": "g",
    "ScreenshotChanged": "h",
    "PreviewChanged": "i",
    "PreviewPositionChanged": "j",
    "PreviewDimensionChanged": "k",
    "PreviewValueChanged": "l",
    "PreviewDeleted": "m",
    "Sheet": "n",
    "Cell": "o",
    "NameChanged": "p",
}


USER_EDITS = (NameChanged, RowChanged, ColumnChanged, CellChanged, PreviewChanged)
