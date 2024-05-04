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

    window.createSheet = (columnCount, rowCount, parentId) => {
        createBasicSheet(parentId)
        window.fillSheet(columnCount, rowCount);
    }

    const divmod = (x, y) => [Math.floor(x / y), x % y];

    window.getColumnName = (col) => {
        const parts = [];
        col += 1;
        while (col > 0) {
            var [col, remainder] = divmod(col - 1, 26);
            parts.splice(0, 0, String.fromCharCode(remainder + "A".charCodeAt(0)));
        }
        return parts.join("");
    }

    window.getKeyFromColumnRow = (col, row) => {
        return `${window.getColumnName(col - 1)}${row}`;
    }

    window.fillSheet = (column, row) => {
        if ($(`#${window.getKeyFromColumnRow(column, row)}`).length) return;

        const sheet = $("#sheet");
        const header = $("#sheet-header");
        const existingColumnCount = header.children().length;
        const existingRowCount = sheet.find("tr").length;
        const newRow = Math.max(row, existingRowCount - 1);
        const newColumn = Math.max(column, existingColumnCount - 1);

        // Add sheet headers
        for (var column=existingColumnCount; column <= newColumn; column++) {
            if ($(`#col-${column}`).length == 0) {
                header.append(
                    $("<th>")
                        .addClass("column-label")
                        .addClass(`col-${column}`)
                        .attr("id", `col-${column}`)
                        .attr("col", column)
                        .text(window.getColumnName(column - 1))
                        .resizable({
                            handles: "e",
                            alsoResize: `.col-${column}`,
                        })
                        .on("resize", function(event) { columnResized(event); })
                );
            }
        }

        // fill the top right block
        for (var row=1; row <= existingRowCount; row++) {
            const elements = [];
            for (var column=existingColumnCount; column <= newColumn; column++) {
                const key = window.getKeyFromColumnRow(column, row);
                elements.push(
                    `<td id="${key}" class="cell row-${row} col-${column}" col="${column}" row="${row}">`
                );
            }
            const html = elements.join("");
            $(`#row-${row}`).append($(html))
        }

        // fill the entire bottom section
        const elements = [];
        for (var row=existingRowCount; row <= newRow; row++) {
            elements.push(`<tr id="row-${row}" row="${row}">`);
            elements.push(`<td new="true" class="row-label row-${row}" row="${row}">${row}</td>`);
            for (var column=1; column <= newColumn; column++) {
                const key = window.getKeyFromColumnRow(column, row);
                elements.push(
                    `<td id="${key}" class="cell row-${row} col-${column}" col="${column}" row="${row}">`
                )
            }
            elements.push("</tr>")
        }
        const html = elements.join("\n");
        sheet.append($(html));

        sheet.find('td[new="true"]').each((index, element) => {
            const td = $(element);
            const row = td.attr('row');
            td
                .resizable({
                    handles: "s",
                    minHeight: 22,
                    alsoResize: `.row-${row}`,
                })
                .removeAttr("new")
                .on("resize", function(event) { rowResized(event); })
        });
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

    window.clipboardInsert = (insertDone, atColumn, atRow, includeStyle) => {

        function pasteCell(column, row, text, style) {
            const key = window.getKeyFromColumnRow(atColumn + column, atRow + row);
            var cell = $(`#${key}`).text(text);
            if (style) {
                const align = cell.css("text-align").replace("start", "left").replace("end", "right");
                cell.prop("style", style)
                    .css("border", "")
                    .css("padding", "")
                    .css("text-align", align)
            }
        }

        function paste_text(text) {
            const lines = text.split("\n");
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
                    pasteCell(column, row, words[col])
                }
            }
            setTimeout(() => insertDone(columnCount, rowCount));
        }

        function pasteHTML(text) {
            const html = $(text)
            const rows = html.find("tr");
            var rowCount = rows.length;
            var columnCount = 0;
            rows.each((row, tr) => {
                const cols = $(tr).find("td");
                if (columnCount == 0) {
                    columnCount = cols.length;
                    window.fillSheet(atColumn + columnCount, atRow + rowCount);
                }
                cols.each((col, td) => {
                    pasteCell(col + 1, row + 1, $(td).text(), $(td).attr("style"))
                });
                columnCount = cols.length;
            });
            html.find("col").each((index, col) => {
                $(`.col-${atColumn + index + 1}`).width($(col).attr("width"))
            });
            setTimeout(() => insertDone(columnCount, rowCount));
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
                                pasteHTML(text);
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