import models


def make_css(sheet: models.Sheet):
    lines = []
    for col, width in sheet.columns.items():
        lines.append(f".col-{col} {{ width: {width}px; }}")
    for row, height in sheet.rows.items():
        lines.append(f".row-{row} {{ height: {height}px; }}")
    return "\n".join(lines)


def make_column_label(col: int, sheet: models.Sheet):
    label = models.get_column_name(col)
    return f'<div class="column-label col-{col}" id="col-{col}" col="{col}"">{label}</div>'


def make_column_header(sheet: models.Sheet):
    return "".join((
        [ '<div id="column-header" class="column-header">' ] +
        [ make_column_label(col, sheet) for col in range(1, sheet.column_count + 1) ] +
        [ '</div>' ]
    ))


def make_cell(col, row, sheet):
    key = models.get_key_from_col_row(col, row)
    cell = sheet.cells.get(key, models.Cell())
    value = cell.value or cell.script
    value = value.replace("<", "&lt;").replace(">", "&gt;") if isinstance(value, str) else value
    styles = [f"{name}:{value}" for name, value in cell.style.items()] + [
        "padding:2px",
    ]
    style = f'style="{";".join(styles)};"' if styles else ""
    return f'<div id="{key}" class="cell row-{row} col-{col}" col="{col}" row="{row}" {style}>{value}</div>'


def make_row_label(row: int, sheet: models.Sheet):
    style = f'style="height:{sheet.rows[row]}px;"' if row in sheet.rows else ""
    return f'<div class="row-label row-{row}" {style} row="{row}">{row}</div>\n'


def make_row_header(sheet: models.Sheet):
    return "".join(
        [ f'\n<div id="row-header" class="row-header">'] +
        [ make_row_label(row, sheet) for row in range(1, sheet.row_count + 1) ] +
        [ '</div>\n']
    )


def make_row(row: int, sheet: models.Sheet):
    return "\n".join(
        [ f'\n<div id="row-{row}" class="cell-row">' ] +
        [ make_cell(col, row, sheet) for col in range(1, sheet.column_count + 1) ] +
        [ '</div>\n' ]
    )


def make_html(sheet: models.Sheet):
    assert isinstance(sheet, models.Sheet), f"Expected a Sheet object, not {type(sheet)}"
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
