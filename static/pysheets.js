(async function pysheets() {

    window.start = new Date().getTime();

    window.getToken = () => {
        return window.localStorage.getItem('t')
    }

    window.addToken = (url) => {
        const sep = url.indexOf("?") == -1 ? "?" : "&";
        return `${url}${sep}t=${getToken()}`
    }

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
        request.open("GET", addToken(url), false);
        request.send(null);
        if (request.status === 200) {
            return window.get_response_body(request);
        }
        return `Get error for ${url}: ${request.status}`
    }

    window.post = (url, data) => {
        const request = new XMLHttpRequest();
        request.open("POST", addToken(url), false);
        request.send(data);
        if (request.status === 200) {
            return window.get_response_body(request);
        }
        return `Post error for ${url}: ${request.status}`
    }

    setTimeout(() => $("py-splashscreen").text(""), 10);
    setTimeout(() => $("py-splashscreen").text(""), 100);
    setTimeout(() => $("py-splashscreen").text(""), 1000);

    window.createBasicSheet = (parentId) => {
        if ($("#sheet").length) {
            return $("#sheet");
        } 
        return $("<table>")
            .attr("id", "sheet")
            .addClass("sheet")
            .append($("<tr>")
                .attr("id", "sheet-header")
                .append(
                    $("<th>").addClass("blank")
                )
            )
            .appendTo($(`#${parentId}`));
    }

    window.createSheet = (column_count, row_count, parentId) => {
        createBasicSheet(parentId)
        window.fillSheet(column_count, row_count);
    }

    const divmod = (x, y) => [Math.floor(x / y), x % y];

    function getColumnName(col) {
        const parts = [];
        col += 1;
        while (col > 0) {
            var [col, remainder] = divmod(col - 1, 26);
            parts.splice(0, 0, String.fromCharCode(remainder + "A".charCodeAt(0)));
        }
        return parts.join("");
    }

    function getKeyFromColumnRow(col, row) {
        return `${getColumnName(col - 1)}${row}`;
    }

    window.fillSheet = (column_count, row_count) => {
        const sheet = $("#sheet");
        const header = $("#sheet-header");
        column_count = Math.max(column_count, header.children().length - 1)
        for (var column=1; column <= column_count; column++) {
            if ($(`#col-${column}`).length == 0) {
                header.append(
                    $("<th>").append(
                        $("<div>")
                            .addClass("column-label")
                            .addClass(`col-${column}`)
                            .attr("id", `col-${column}`)
                            .attr("col", column)
                            .text(getColumnName(column - 1))
                            .resizable({
                                handles: "e",
                                alsoResize: `.col-${column}`,
                            })
                            .on("resize", function(event) { columnResized(event); })
                    )
                );
            }
        }
        row_count = Math.max(row_count, sheet.children().length - 1)
        for (var row=1; row <= row_count; row++) {
            var tr = $(`#row-${row}`);
            if (tr.length == 0) {
                tr = $("<tr>")
                    .attr("id", `row-${row}`)
                    .appendTo(sheet)
                    .append($("<td>")
                        .addClass("row-label")
                        .addClass(`row-${row}`)
                        .text(`${row}`)
                        .attr("row", row)
                        .resizable({
                            handles: "s",
                            alsoResize: `.row-${row}`,
                        })
                        .on("resize", function(event) { rowResized(event); })
                    )
            }
            for (var column=1; column <= column_count; column++) {
                const id = getKeyFromColumnRow(column, row);
                if ($(`#${id}`).length == 0) {
                    tr.append($("<td>")
                        .attr("id", id)
                        .addClass(`cell row-${row} col-${column}`)
                        .attr("col", column)
                        .attr("row", row)
                    );
                }
            }
        }
        sheet
            .attr("column_count", column_count)
            .attr("row_count", row_count);
    }

    // if (window.location.search) { $("#main").empty(); } 
    $("#main").css("display", "block");

    window.addArrow = (from, to, label) => {
        try {
            const start = from[0];
            const end = to[0];
            if (start && end) {
                return $(new LeaderLine(start, end, {
                    dash: { },
                    size: 3,
                    middleLabel: LeaderLine.pathLabel(label || "")
                })).appendTo($("#sheet-scrollable"));
            }
        } catch(e) {
            // ignore
        }
    }

    window.run = (job) => {
        console.log("No worker for", job)
    }

    window.check_loaded = () => {
        if ($('#sheet-container').length === 0) {
            const params = new URLSearchParams(document.location.search);
            const uid = params.get("U");
            const protocol = document.location.protocol;
            const host = document.location.host;
            const url = `${protocol}//${host}/?U=${uid}`;
            if (uid && url !== document.location.href) {
                const nopackages = url;
                const runInMain = `${url}&r=pyodide`;
                $("body").append(
                    $("<div>").append(
                        $("<div>")
                            .css("margin", 8)
                            .text("It looks like PySheets could not load the document. Things you can try:"),
                        $("<ul>")
                            .css("margin", 8)
                            .append(
                                $(`<li>Edit the URL to remove the packages that are not pure Python wheels. <a href="${url}">Try this</a>.</li>`),
                                $(`<li>Edit the URL to run all Python in the main thread. <a href="${runInMain}">Try this</a>.</li>`),
                                $(`<li>Edit the URL to run all Python in the worker'. <a href="${nopackages}">Try this</a>.</li>`),
                                $(`<li>Reload the current page. <a href="${url}">Try this</a>.</li>`),
                                $(`<li>Check the Chrome Devtools Console (or its equivalent).</li>`),
                                $(`<li>Go to the previous document in your browser history.</li>`)
                            )
                    )
                    .css("position", "absolute")
                    .css("left", "10px")
                    .css("top", "190px")
                    .css("color", "red")
                    .css("z-index", 1000000)
                )
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

    window.clipboardInsert = (callback, atColumn, atRow, includeStyle) => {

        function paste_cell(column, row, text, style) {
            const key = getKeyFromColumnRow(atColumn + column, atRow + row);
            var cell = $(`#${key}`);
            if (!cell.length) {
                window.fillSheet(atColumn + column, atRow + row);
                cell = $(`#${key}`);
            }
            cell.text(text);
            if (style) {
                const align = cell.css("text-align").replace("start", "left").replace("end", "right");
                cell.prop("style", style)
                    .css("border", "")
                    .css("text-align", align)
            }
        }

        function paste_text(text) {
            const lines = text.split("\n");
            for (var row=1; row<=lines.length; row++) {
                const line = lines[row];
                const words = text.split("\t");
                for (var col=1; col<=words.length; col++) {
                    paste_cell(column, row, words[col])
                }
            }
        }

        function paste_html(text) {
            const html = $(text)
            const rows = html.find("tr");
            var rowCount = rows.length;
            var columnCount = 0;
            rows.each((row, tr) => {
                const cols = $(tr).find("td");
                cols.each((col, td) => {
                    paste_cell(col + 1, row + 1, $(td).text(), $(td).attr("style"))
                });
                columnCount = cols.length;
            });
            html.find("col").each((index, col) => {
                $(`.col-${atColumn + index + 1}`).width($(col).attr("width"))
            });
            callback(columnCount, rowCount);
        }

        navigator.clipboard.read().then(items => {
            for (const item of items) {
                for (const type of item.types) {
                    item.getType(type).then(blob => {
                        blob.text().then(text => {
                            if (!includeStyle && type == "text/plain") {
                                paste_text(text);
                            }
                            else if (includeStyle && type == "text/html") {
                                paste_html(text);
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

    window.getStyle = (element) => {
        try {
            return window.getComputedStyle(element)
        } catch {
            return {}
        }
    }
})();