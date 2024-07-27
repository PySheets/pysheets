"""
Copyright (c) 2024 laffra - All Rights Reserved. 

This module creates the HTML for the sheet.
"""

import api
import models


def make_css(sheet: models.Sheet):
    """
    Generates the CSS styles for the sheet based on the column widths and row heights defined in the `sheet` object.
    """
    lines = []
    for col, width in sheet.columns.items():
        lines.append(f".col-{col} {{ width: {width}px; }}")
    for row, height in sheet.rows.items():
        lines.append(f".row-{row} {{ height: {height}px; }}")
    return "\n".join(lines)


def make_column_label(col: int):
    """
    Generates the HTML label for a column in the sheet.
    
    Args:
        col (int): The column index, starting from 1.
        sheet (models.Sheet): The sheet object containing the column information.
    
    Returns:
        str: The HTML markup for the column label.
    """
    label = api.get_column_name(col)
    return f'<div class="column-label col-{col}" id="col-{col}" col="{col}"">{label}</div>'


def make_column_header(sheet: models.Sheet):
    """
    Generates the HTML for the column header of the sheet.
    """
    return "".join((
        [ '<div id="column-header" class="column-header">' ] +
        [ make_column_label(col) for col in range(1, sheet.column_count + 1) ] +
        [ '</div>' ]
    ))


def make_cell(col, row, sheet):
    """
    Generates the HTML markup for a single cell in the sheet.
    
    Args:
        col (int): The column index of the cell, starting from 1.
        row (int): The row index of the cell, starting from 1.
        sheet (models.Sheet): The sheet object containing the cell information.
    
    Returns:
        str: The HTML markup for the cell.
    """
    key = api.get_key_from_col_row(col, row)
    cell = sheet.cells.get(key, models.Cell())
    value = cell.value or cell.script
    value = value.replace("<", "&lt;").replace(">", "&gt;") if isinstance(value, str) else value
    styles = [f"{name}:{value}" for name, value in cell.style.items()] + [
        "padding:2px",
    ]
    style = f'style="{";".join(styles)};"' if styles else ""
    return f'<div id="{key}" class="cell row-{row} col-{col}" col="{col}" row="{row}" {style}>{value}</div>'


def make_row_label(row: int, sheet: models.Sheet):
    """
    Generates the HTML label for a row in the sheet.
    
    Args:
        row (int): The row index, starting from 1.
        sheet (models.Sheet): The sheet object containing the row information.
    
    Returns:
        str: The HTML markup for the row label.
    """
    style = f'style="height:{sheet.rows[row]}px;"' if row in sheet.rows else ""
    return f'<div class="row-label row-{row}" {style} row="{row}">{row}</div>\n'


def make_row_header(sheet: models.Sheet):
    """
    Generates the HTML markup for the row header of the sheet, which includes the row labels.
    
    Args:
        sheet (models.Sheet): The sheet object containing the row information.
    
    Returns:
        str: The HTML markup for the row header.
    """
    return "".join(
        [ '\n<div id="row-header" class="row-header">' ] +
        [ make_row_label(row, sheet) for row in range(1, sheet.row_count + 1) ] +
        [ '</div>\n']
    )


def make_row(row: int, sheet: models.Sheet):
    """
    Generates the HTML markup for a row in the sheet, containing the cells for that row.
    
    Args:
        row (int): The row index, starting from 1.
        sheet (models.Sheet): The sheet object containing the row information.
    
    Returns:
        str: The HTML markup for the row.
    """
    return "\n".join(
        [ f'\n<div id="row-{row}" class="cell-row">' ] +
        [ make_cell(col, row, sheet) for col in range(1, sheet.column_count + 1) ] +
        [ '</div>\n' ]
    )


def make_html(sheet: models.Sheet):
    """
    Generates the HTML markup for the entire sheet, including the column header, row header, and grid of cells.
    
    Args:
        sheet (models.Sheet): The sheet object containing the data to be rendered.
    
    Returns:
        str: The HTML markup for the entire sheet.
    """
    return "".join(
        [
            "<div class='sheet' id='sheet' font-family:Arial; font-size: 14px;'>",
                make_column_header(sheet),
                make_row_header(sheet),
                "<div class='sheet-grid' id='sheet-grid'>",
                    "\n\n".join([ make_row(row, sheet) for row in range(1, sheet.row_count + 1) ]),
                "</div>",
                "<div class='blank'>",
            "</div>",
        ]
    )
