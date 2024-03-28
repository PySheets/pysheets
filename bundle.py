import ast
import io
import json
import os
import re
import sys
import textwrap
import traceback

found_modules = set()
files = []
module_children = {}
global_imports = { }
names = [
    "Blank", "Cell", "progress", "hide_progress", "show_progress",
    "setup", "normalize_key", "add_token", "post_with_token", "get_with_token",
    "Document", "User", "Progress", "set_title", "login", "logout",
    "empty_edits", "uid", "name", "timestamp", "edits", "dirty", "last_edit",
    "email", "token", "photo", "self", "ltk", "js", "json", "logging", 
    "base64", "io", "collections",
    "convert_from_json", "handle_job_result", "load_doc", "repeat", "doc",
    "user", "editing", "in_edit_mode", "state", "menu", "logger", 
    "create_menu", "delete_doc", "share", "close_share_dialog", 
    "new_sheet", "share_sheet", "set_state", "kind", "value",
    "render", "render_preview", "dependents", "dependent", "is_int.py",
    "render_image", "show_image", "render_list", "render_dict", 
    "render_table", "update_image", "setup_login", "setup_account_menu",
    "setup_logger", "watch", "hide_main", "show_main", "show_hide_main", 
    "check_edits", "hide_header", "mousemove", "popup", "show_account_menu", 
    "list_sheets", "show_document_list", "create_topbar", "load_file", 
    "documents", "go_home", "saveit", "cell", "cells", "event", "table", "pysheets",
    "key", "settings", "column", "add_label", "add_preview", "save_preview", "dragstart",
    "dragstop", "resize", "make_resizable", "email_to_class", "resize_editor", "sync",
    "motion", "switch_logger", "update_input", "node_changed", "rgb_to_hex",

    "confirm", "save", "get_col_row", "to_human", "get_input_range",
    "set_inputs", "select", "get_cell", "compute_in_worker", "to_human", "create_spreadsheet",
    "draw_cell_arrows", "draw_arrows", "create_marker", "add_marker", "enter",
    "leave", "draw_draggable_arrow", "reset", "is_int", "add_image", "stop_drag_image",
    "resize_image", "load_image", "convert", "keydown", "keyup", "changed", "edited",

    "to_dict", "handle_edits", "load_images", "remove_arrows", "load_cells", "draw_arrows",
    "load_data", "update_editor", "remove_old_editors", "save_edits", "save_file", "save_done",
    "save_changes", "get_plot_screenshot", "done", "get_data", "handle_login", "register",
    "set_name", "update_cell", "set_font", "set_style", "set_layout", "set_font_size",
    "set_color", "set_background", "set_main_state", "toggle_edit", "create_card", "select_doc",
    "result", "response", "index", "option", "function", "timeout_seconds",
    "create_user_image", "ServerLogger", "Editor", "load_previews", "previews",
    "load_history", "restore_history", "load_history_chunk", "Console",

    "DEFAULT_ROW_HEIGHT", "DEFAULT_COLUMN_WIDTH", "DEFAULT_FONT_FAMILY",
    "DEFAULT_FONT_SIZE", "DEFAULT_COLOR", "DEFAULT_FILL",
    "DEFAULT_STYLE", "DEFAULT_LAYOUT", "ICON_HOUR_GLASS",
    "ICON_DATAFRAME", "ICON_JSON", "ICON_PLOT", "ICON_LIST",
    "CELL_COLORS", "CELL_STATE_NAMES", "FONT_NAMES", "FONT_SIZES", "STYLES", "LAYOUTS",
    "SAVE_DELAY_MULTIPLE_EDITORS", "SAVE_DELAY_SINGLE_EDITOR",

    "get_col_row_from_key", "get_key_from_col_row", "debug_get_info", "run_in_worker", "get_inputs",
    "handle_cell_changed", "nodes", "inputs", "is_col", "is_row", "show_logger",
    "invalid", "invalid_nodes", "preview", "worker_ready", "create_editor", "main_editor",
    "constants", "String", "Boolean", "Number", "Formula", "network",
    "clear_error", "render_errors", "report_error", "save_packages", "reload_with_packages",
    "remainder", "col", "row", "handler", "first_letter", "other", "color", "logger_enabled",
    "show_settings", "errors", "arg", "Cache", "cache", 
    "parts", "packages", "editor", "show_buttons", "sep", "mode", 
    "sync_edits", "ignore", "message", "td", "buttons", "local_storage",
    "remove_marker", "summarize_edit", "history", "changed_cells", "get_timestamp",

    "DEFAULT_ROW_HEIGHT", "DEFAULT_COLUMN_WIDTH", "DEFAULT_FONT_FAMILY", "DEFAULT_FONT_SIZE",
    "DEFAULT_COLOR", "DEFAULT_FILL", "DEFAULT_STYLE", "DEFAULT_LAYOUT",
    "ICON_HOUR_GLASS", "ICON_DATAFRAME", "ICON_JSON", "ICON_PLOT",
    "ICON_LIST", "MODE_PRODUCTION", "MODE_DEVELOPMENT", "IMAGE_COLORS",
    "FONT_NAMES", "FONT_SIZES", "SAVE_DELAY_MULTIPLE_EDITORS", "SAVE_DELAY_SINGLE_EDITOR",
    "TOPIC_NODE_CHANGED", "TOPIC_CELL_CHANGED", "DATA_KEY_VALUE", "DATA_KEY_COLUMNS",
    "DATA_KEY_CELLS", "DATA_KEY_ROWS", "DATA_KEY_IMAGES", "DATA_KEY_NAME",
    "DATA_KEY_TIMESTAMP", "DATA_KEY_STATUS", "DATA_KEY_STACK", "DATA_KEY_UID",
    "DATA_KEY_EDIT", "DATA_KEY_ENTRY", "DATA_KEY_ERROR", "DATA_KEY_SCREENSHOT",
    "DATA_KEY_EMAIL", "DATA_KEY_PASSWORD", "DATA_KEY_URL", "DATA_KEY_TOKEN",
    "DATA_KEY_MESSAGE", "DATA_KEY_WHEN", "DATA_KEY_TITLE", "DATA_KEY_IDS",
    "DATA_KEY_WIDTH", "DATA_KEY_HEIGHT", "DATA_KEY_EMAIL", "DATA_KEY_PASSWORD",
    "DATA_KEY_EXPIRATION", "DATA_KEY_EDITS", "DATA_KEY_RESULT", "DATA_KEY_LOGS",
    "DATA_KEY_PREVIEWS", "DATA_KEY_EDITOR_HEIGHT", "DATA_KEY_CELL", "DATA_KEY_CURRENT",
    "DATA_KEY_VALUE_FORMULA", "DATA_KEY_VALUE_KIND", "DATA_KEY_VALUE_PREVIEW", "DATA_KEY_VALUE_FONT_FAMILY",
    "DATA_KEY_VALUE_FONT_SIZE", "DATA_KEY_VALUE_LAYOUT", "DATA_KEY_VALUE_COLOR", "DATA_KEY_VALUE_FILL",
    "DATA_KEY_VALUE_STYLE", "PUBSUB_STATE_ID", "PUBSUB_SHEET_ID", "OTHER_EDITOR_TIMEOUT",
    "DATA_KEY_EDITOR_WIDTH", "DATA_KEY_PACKAGES",
    "DATA_KEY_TIMESTAMP", "DATA_KEY_BEFORE", "DATA_KEY_AFTER",

]
short_names = {}

current_ordinal = 300

def shorten(name):
    global current_ordinal
    if name in names:
        if name in short_names:
            return short_names[name]
        while True:
            current_ordinal += 1
            current_char = chr(current_ordinal)
            try:
                exec(f"{current_char}=0")
                short_names[name] = current_char
                # print(current_char, name)
                return current_char
            except Exception as e:
                pass
    return name


def bundle(folder, module_name, out):
    if module_name in found_modules:
        return True
    found_modules.add(module_name)

    base = os.path.join(folder, module_name.replace(".", "/"))
    filename = f"{base}.py"
    if not os.path.exists(filename):
        filename = f"{base}/__init__.py"
    if not os.path.exists(filename):
        if module_name not in ["pandas", "warnings"] and not "." in module_name:
            global_imports[module_name] = True
        return False
    with open(filename, 'r') as f:
        source = f.read()
    tree = ast.parse(source)
    imports = []
    module_children[module_name.replace(".", "_")] = children = []

    def remove_docstring(node):
        if hasattr(node, "body") and isinstance(node.body[0], ast.Expr):
            if isinstance(node.body[0].value, ast.Str):
                node.body = node.body[1:]
                if len(node.body)<1:
                    node.body.append(ast.Pass())


    class ImportResolver(ast.NodeTransformer):
        def visit_Import(self, node: ast.Import):
            names = []
            for name in node.names:
                if not bundle(folder, name.name, out):
                    names.append(name)
            node.names = names
            return None if not names else node

        def visit_ImportFrom(self, node: ast.ImportFrom):
            if node.module == "unittest.mock":
                raise ValueError(f"synthetic module {node.module}")
            other = node.module.replace(".", "_")
            for alias in node.names:
                imports.append((alias.name,  other))
                alias.name = alias.name if alias.name == shorten(alias.name) else f"{alias.name} as {shorten(alias.name)}"
            bundle(folder, node.module, out)
            return node

        def visit_FunctionDef(self, node: ast.FunctionDef):
            for decorator in node.decorator_list:
                self.visit(decorator)
            remove_docstring(node)
            children.append(node)
            for arg in node.args.args:
                arg.arg = shorten(arg.arg)
            for default in node.args.defaults:
                self.visit(default)
            for statement in node.body:
                self.visit(statement)
            node.name = shorten(node.name)
            return node

        def visit_Lambda(self, node: ast.Lambda):
            for arg in node.args.args:
                arg.arg = shorten(arg.arg)
            self.visit(node.body)
            return node

        def visit_Assign(self, node: ast.Assign):
            for target in node.targets:
                target.name = ast.unparse(target)
                if target.name == "__all__":
                    return None
                self.visit(target)
            self.visit(node.value)
            return node 

        def visit_Attribute(self, node: ast.Attribute):
            node.attr = shorten(node.attr)
            self.visit(node.value)
            return node

        def visit_Expr(self, node: ast.Expr):
            self.visit(node.value)
            return node

        def visit_Global(self, node: ast.Global):
            node.names = [ shorten(name) for name in node.names ]
            return node

        def visit_Name(self, node: ast.Name):
            node.id = shorten(node.id)
            return node

        def visit_NameConstant(self, node: ast.NameConstant):
            node.kind = shorten(node.kind)
            return node

        def visit_Call(self, node: ast.Call):
            if isinstance(node.func, ast.Name):
                node.func.id = shorten(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                node.func.attr = shorten(node.func.attr)
                self.visit(node.func.value)
            for arg in node.args:
                self.visit(arg)
            for keyword in node.keywords:
                self.visit(keyword)
            return node

        def visit_ClassDef(self, node: ast.ClassDef):
            remove_docstring(node)
            children.append(node)
            node.name = shorten(node.name)
            for child in node.body:
                self.visit(child)
                remove_docstring(child)
            return node
    try:
        tree = ImportResolver().visit(tree)
    except ValueError:
        return

    def cleanup(source):
        source = re.sub("from __future__ import annotations", "", source)
        source = re.sub("\n\w*\n", "\n", source)
        source = re.sub("[^']# .*\n", "\n", source)
        return source

    def generate():
        module = f"{module_name.replace('.', '_')}"
        print(textwrap.indent(cleanup(ast.unparse(tree)), ""), file=out)
        print(f"{shorten(module)} = M(locals())", file=out)
        files.append(module)

    generate()
    return True

def indent(line):
    index = 0
    while line[index] == " ":
        index += 1
    return index

def chunks(minified):
    lines = minified.split("\n")
    chunks = []
    chunk = []
    for line in lines:
        if "M(locals()" in line and len(chunk) > 200:
            chunks.append(chunk)
            chunk = []
        chunk.append(line)
    chunks.append(chunk)
    return chunks

def main():
    try:
        filename = sys.argv[1]
        if not os.path.exists(filename):
            raise ValueError(f"No such file: {filename}")
        buffer = io.StringIO()
        module = os.path.basename(filename)[:-3].replace("/", ".")
        folder = os.path.abspath(os.path.dirname(filename))
        bundle(folder, module, buffer)
        lines = []
        last_line = ""
        for line in buffer.getvalue().split("\n"):
            if last_line and line and indent(last_line) == indent(line) and not last_line.endswith(":") and not line.strip().startswith(("@", "class ", "with ", "try:", "def ", "for ", "while ", "if ")):
                last_line = f"{last_line}; {line.strip()}"
                lines.pop()
                lines.append(last_line)
                continue
            last_line = line
            lines.append(line)
        minified = "\n".join(lines)
        for n, chunk in enumerate(chunks(minified)):
            output_filename = filename.replace(".py", f"_min_{n}.py")
            with open(output_filename, "w") as out:
                print("import", ",".join(
                    module if module == shorten(module) else f"{module} as {shorten(module)}"
                    for module in global_imports), file=out)
                if n > 0:
                    print(f"from {filename.replace('.py', f'_min_{n - 1}')} import *", file=out)
                print(f"class M():", file=out)
                print(f"    def __init__(s, f):", file=out)
                print(f"        for k,v in f.items(): setattr(s,k,v)", file=out)
                print("\n".join(chunk), file=out)
        print("bundled", files)
    except:
        traceback.print_exc()
        print(f"usage: python3 {sys.argv[0]} path-to-module")

main()