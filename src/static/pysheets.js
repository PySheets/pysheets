/*
 * Copyright (c) 2024 laffra - All Rights Reserved. 
 * 
 * This file is part of the PySheets projects and contains "native" methods for performance.
 */

(async function pysheets() {

    window.start = new Date().getTime();

    window.time = () => {
        return new Date().getTime() / 1000.0;
    }

    window.get_response_body = (request) => {
        try {
            const bytes = new Uint8Array(request.response);
            for (var i = 0, len = bytes.length; i < len; ++i) {
                bytes[i] = request.response[i];
            }
            return bytes;
        } catch(exception) {
            return request.responseText;
        }
    }

    window.get = (url) => {
        const request = new XMLHttpRequest();
        request.open("GET", url, false);
        request.send(null);
        if (request.status === 200) {
            return window.get_response_body(request);
        }
        return `Get error for ${url}: ${request.status}`
    }

    window.post = (url, data) => {
        const request = new XMLHttpRequest();
        request.open("POST", url, false);
        request.send(data);
        if (request.status === 200) {
            return window.get_response_body(request);
        }
        return `Post error for ${url}: ${request.status}`
    }

    setTimeout(() => $("py-splashscreen").text(""), 10);
    setTimeout(() => $("py-splashscreen").text(""), 100);
    setTimeout(() => $("py-splashscreen").text(""), 1000);

    const divmod = (x, y) => [Math.floor(x / y), x % y];

    window.getColumnName = (col) => {
        const parts = [];
        while (col > 0) {
            var [col, remainder] = divmod(col - 1, 26);
            parts.splice(0, 0, String.fromCharCode(remainder + "A".charCodeAt(0)));
        }
        return parts.join("");
    }

    window.getKeyFromColumnRow = (col, row) => {
        return `${window.getColumnName(col)}${row}`;
    }

    window.fillSheet = (column, row) => {
        if ($(`#${window.getKeyFromColumnRow(column, row)}`).length) return;

        const columnHeader = $("#column-header");
        const rowHeader = $("#row-header");
        const existingColumnCount = columnHeader.children().length;
        const existingRowCount = rowHeader.children().length;
        const newRowCount = Math.max(row + 1, existingRowCount);
        const newColumnCount = Math.max(column, existingColumnCount);

        // Add column headers
        for (var column=existingColumnCount + 1; column <= newColumnCount; column++) {
            if ($(`#col-${column}`).length == 0) {
                makeColumnResizable(
                    $("<div>")
                        .addClass(`column-label col-${column}`)
                        .attr("id", `col-${column}`)
                        .attr("col", column)
                        .text(window.getColumnName(column))
                        .appendTo(columnHeader)
                );
            }
        }

        // fill the top right block
        for (var row=1; row <= existingRowCount; row++) {
            const elements = [];
            for (var column=existingColumnCount + 1; column <= newColumnCount; column++) {
                const key = window.getKeyFromColumnRow(column, row);
                elements.push(
                    `<div id="${key}" class="cell row-${row} col-${column}" col="${column}" row="${row}"></div>`
                );
            }
            $(`#row-${row}`).append($(elements.join("")))
        }

        // add missing row labels
        for (var row=existingRowCount + 1; row < newRowCount; row++) {
            makeRowResizable(
                $("<div>")
                    .addClass(`row-label row-${row}`)
                    .attr("row", row)
                    .text(row)
                    .appendTo(rowHeader)
            )
        }

        // fill the entire bottom section
        const cell_elements = [];
        for (var row=existingRowCount + 1; row < newRowCount; row++) {
            cell_elements.push(`<div id="row-${row}" class="cell-row">`);
            for (var column=1; column <= newColumnCount; column++) {
                const key = window.getKeyFromColumnRow(column, row);
                cell_elements.push(
                    `<div id="${key}" class="cell row-${row} col-${column}" col="${column}" row="${row}"></div>`
                )
            }
            cell_elements.push("</div>")
        }
        $("#sheet-grid").append($(cell_elements.join("\n")));
    }

    window.makeColumnResizable = (node) => {
        node.resizable({
            handles: "e",
            minWidth: 35,
        })
        .on("resize", (event) => columnResizing(event))
        .on("resizestop", (event) => columnResized(event));
    }

    window.makeRowResizable = (node) => {
        node.resizable({
            handles: "s",
            minHeight: 20,
        })
        .on("resize", (event) => rowResizing(event))
        .on("resizestop", (event) => rowResized(event));
    }

    window.makeSheetResizable = () => {
        $(".column-label").each((index, element) => {
            makeColumnResizable($(element));
        });
        $(".row-label").each((index, element) => {
            makeRowResizable($(element));
        });
    }

    window.adjustSheetPosition = () => {
        $("#column-header")
            .css("top", 0)
            .css("left", $(".sheet-grid").css("margin-left"));
        $(".blank")
            .css("top", 0)
            .css("display", "block");
        $("#row-header")
            .css("top", $(".sheet-grid").css("margin-top"));
    }

    window.makeSheetScrollable = () => {
        const sheet = $("#sheet");
        sheet.on("wheel", (event) => {
            $(".leader-line, .inputs-marker").remove()
            const target = $(event.target);
            if (target.hasClass("cell")) {
                const columnHeader = $("#column-header");
                const rowHeader = $("#row-header");
                const container = $("#sheet-container");
                const grid = $(".sheet-grid");

                // compute horizontal position
                const dx = -event.originalEvent.deltaX * 2;
                const left = parseFloat(grid.css("margin-left"));
                const minX = container.width() - columnHeader.width();
                const marginLeft = Math.min(61, Math.max(left + dx, minX))
                grid.css("margin-left", marginLeft);

                // compute vertical position
                const dy = -event.originalEvent.deltaY * 2;
                const top = parseFloat(grid.css("margin-top"));
                const minY = container.height() - rowHeader.height();
                const marginTop = Math.min(30, Math.max(top + dy, minY))
                grid.css("margin-top", marginTop);

                // sync column and row headers
                window.adjustSheetPosition();
                event.preventDefault();
            }
        });
    }

    window.addArrow = (from, to) => {
        if ($("#main").css("opacity") !== "1") return;
        try {
            const start = from[0];
            const end = to[0];
            if (start && end) {
                return $(new LeaderLine(start, end, {
                    dash: { },
                    size: 3,
                    middleLabel: LeaderLine.pathLabel("")
                })).appendTo($(".sheet-grid"));
            }
        } catch(e) {
        }
    }

    window.highlightColRow = (from_col, to_col, from_row, to_row) => {
        // remove old row/col highlights
        $(".column-label").css("background-color", "white")
        $(".row-label").css("background-color", "white")
        // add current row/col highlights
        for (var col=from_col; col<=to_col; col++) {
            $(`.column-label.col-${col}`).css("background-color", "#d3e2fc")
        }
        for (var row=from_row; row<=to_row; row++) {
            $(`.row-label.row-${row}`).css("background-color", "#d3e2fc")
        }
    }

    window.run = (job) => {
        console.log("No worker for", job)
    }

    window.check_loaded = () => {
        $('.load-error').remove();
        if ($('#sheet-container').length === 0) {
            const params = new URLSearchParams(document.location.search);
            const uid = params.get("U");
            const protocol = document.location.protocol;
            const host = document.location.host;
            const url = `${protocol}//${host}/?U=${uid}`;
            if (uid && url !== document.location.href) {
                const nopackages = url;
                const runPyOdide = `${url}&r=pyodide`;
                $("body").append(
                    $("<div>").append(
                        $("<div>")
                            .css("margin", 8)
                            .text("It looks like PySheets could not load the document. Things you can try:"),
                        $("<ul>")
                            .css("margin", 8)
                            .append(
                                $(`<li>Edit the URL to remove the packages that are not pure Python wheels. <a href="${url}">Try this</a>.</li>`),
                                $(`<li>Edit the URL to run main thread with PyOdide. <a href="${runPyOdide}">Try this</a>.</li>`),
                                $(`<li>Reload the current page. <a href="${url}">Try this</a>.</li>`),
                                $(`<li>Check the Chrome Devtools Console (or its equivalent) for errors.</li>`),
                            )
                    )
                    .addClass("load-error")
                )
                setTimeout(window.check_loaded, 3000);
            }
        } 
    }
    setTimeout(window.check_loaded, 10000);

    window.log = (message) => {
        console.log(message);
    }

    // this function is implemented in lsp.py
    window.completePython = (lines, line, pos) => {}

    window.create_codemirror_editor = function (element, config) {
        window.editor = window.CodeMirror(element, config);
        window.editor.on('inputRead', function onChange(editor, input) {
            const cursor = editor.getCursor();
            window.completePython(editor.getValue(), cursor.line, cursor.ch)
        });
        return window.editor;
    }

    window.editorClearLine = () => {
        if (window.editorMarker) {
            window.editorMarker.clear()
        }
    }

    window.editorMarkLine = (lineno) => {
        window.editorClearLine();
        setTimeout(() => {
            window.editorMarker = window.editor.getDoc().markText(
                { line: lineno, ch: 0},
                { line: lineno, ch: 200},
                { className: "editor-error" }
            );
        }, 500);
    }

    window.fixFont = (font) => {
        const fonts = { Arial: "Arial", Courier: "Courier", Roboto: "Roboto" };
        try { return fonts[font]; } catch { return "Arial" }
    }

    window.pasteCell = (column, row, td) => {
        const key = window.getKeyFromColumnRow(column, row);
        const text = td.text();
        const valign = td.css("vertical-align");
        const textAlign = (td.css("text-align") || "left").replace("start", "left").replace("end", "right");
        const fontFamily = window.fixFont(td.css("font-family"));
        const fontSize = td.css("font-size");
        const fontWeight = td.css("font-weight");
        const fontStyle = td.css("font-style");
        const backgroundColor = td.css("background-color");
        const color = td.css("color");

        $(`#${key}`).text(text)
            .css("vertical-align", valign)
            .css("text-align", textAlign)
            .css("font-family", fontFamily)
            .css("font-size", fontSize)
            .css("font-weight", fontWeight)
            .css("font-style", fontStyle)
            .css("background-color", backgroundColor)
            .css("color", color);
        
        const style = {};
        if (valign !== "top") {
            style["vertical-align"] = valign;
        }
        if (textAlign !== "left") {
            style["text-align"] = textAlign;
        }
        if (fontFamily !== "Arial") {
            style["font-family"] = fontFamily;
        }
        if (fontSize !== "12px") {
            style["font-size"] = fontSize;
        }
        if (fontWeight !== "400") {
            style["font-weight"] = fontWeight;
        }
        if (fontStyle !== "normal") {
            style["font-style"] = fontStyle;
        }
        if (backgroundColor !== "rgb(255, 255, 255)") {
            style["background-color"] = backgroundColor;
        }
        if (color !== "rgb(0, 0, 0)") {
            style["color"] = color;
        }
        return [key, text, JSON.stringify(style)];
    }

    window.pasteText = (text, atColumn, atRow, insertDone) => {
        const lines = text.split("\n");
        const cells = {};
        if (lines.length == 0) return;
        var rowCount = lines.length;
        var columnCount = 0;
        window.fillSheet(atColumn + columnCount, atRow + rowCount);
        for (var row=1; row<=lines.length; row++) {
            const line = lines[row];
            const words = line.split("\t");
            if (columnCount == 0) {
                columnCount = words.length;
                window.fillSheet(atColumn + columnCount, atRow + rowCount);
            }
            for (var col=1; col<=words.length; col++) {
                window.pasteCell(atColumn + column, atRow + row, words[col])
                cells[`${col}-${row}`] = td.text();
            }
        }
        setTimeout(() => insertDone(columnCount, rowCount, Object.keys(cells)));
    }

    window.getattr = (obj, property) => {
        return obj[property];
    }

    window.pasteHTML = (text, atColumn, atRow, insertDone) => {
        const html = $(text);
        const rows = html.find("tr");
        const keys = [];
        var rowCount = rows.length;
        var columnCount = 0;
        rows.each((row, tr) => {
            const cols = $(tr).find("td");
            if (columnCount == 0) {
                columnCount = cols.length;
                window.fillSheet(atColumn + columnCount, atRow + rowCount);
            }
            cols.each((col, element) => {
                const td = $(element);
                const info = window.pasteCell(atColumn + col, atRow + row, td);
                keys.push(info);
            });
            columnCount = cols.length;
        });
        html.find("col").each((index, col) => {
            $(`.col-${atColumn + index}`).width($(col).attr("width"))
        });
        setTimeout(() => insertDone(keys));
    }

    window.getClipboard = (handler, includeStyle) => {
        navigator.clipboard.read().then(items => {
            for (const item of items) {
                for (const type of item.types) {
                    item.getType(type).then(blob => {
                        blob.text().then(text => {
                            if (!includeStyle && type == "text/plain") {
                                handler(text);
                            }
                            else if (includeStyle && type == "text/html") {
                                handler(text);
                            }
                        })
                    })
                }
            }
        });
    }

    window.clipboardWrite = (text, html) => {
        return navigator.clipboard.write([
            new ClipboardItem({
                ['text/plain']: new Blob([text], {type: 'text/plain'}),
                ['text/html']: new Blob([html], {type: 'text/html'})
            })
        ]).then(() => {});
    }
   
    const styleOptions = [
        ["vff", "font-family", ["Arial"]],
        ["vfs", "font-size", ["14px"]],
        ["vfw", "font-weight", ["normal", "400"]],
        ["vfu", "font-style", ["normal"]],
        ["vc", "color", ["rgb(33, 37, 41)"]],
        ["vb", "background-color", ["white", "rgb(255, 255, 255)"]],
        ["vva", "vertical-align", ["bottom"]],
        ["vta", "text-align", ["start", "left"]],
    ];

    window.isDefaultStyle = (value, defaultValues) => {
        for (const defaultValue of defaultValues) {
            if (value === defaultValue) {
                return true;
            }
        }
        return false;
    }

    window.getStyle = (element) => {
        const result = {};
        const style = window.getComputedStyle(element);
        for (const [key, name, defaultValues] of styleOptions) {
            const value = style.getPropertyValue(name)
            if (!window.isDefaultStyle(value, defaultValues)) {
                result[key] = value;
            }
        }
        return JSON.stringify(result);
    };

    window.isUndefined = (value) => value === undefined;

})();