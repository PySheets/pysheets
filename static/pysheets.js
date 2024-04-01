(function pysheets() {

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
            .css({
            })
            .append($("<tr>")
                .attr("id", "sheet-header")
                .append(
                    $("<th>").addClass("blank")
                )
            )
            .appendTo($(`#${parentId}`));
    }

    window.createSheet = (column_count, row_count, parentId) => {
        const sheet = createBasicSheet(parentId);
        const header = $("#sheet-header");
        for (var column=1; column <= column_count; column++) {
            if ($(`#col-${column}`).length == 0) {
                header.append(
                    $("<th>").append(
                        $("<div>")
                            .addClass("column-label")
                            .addClass(`col-${column}`)
                            .attr("id", `col-${column}`)
                            .attr("col", column)
                            .text(String.fromCharCode("A".charCodeAt(0) + column - 1))
                            .resizable({
                                handles: "e",
                                alsoResize: `.col-${column}`,
                            })
                            .on("resize", function(event) { columnResized(event); })
                    )
                );
            }
        }
        for (var row=1; row <= row_count; row++) {
            var tr = $(`#row-${row}`);
            if (tr.length == 0) {
                tr = $("<tr>")
                    .appendTo(sheet)
                    .append($("<td>")
                        .attr("id", `row-${row}`)
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
            function key(col, row) {
                return `${String.fromCharCode("A".charCodeAt(0) + col - 1)}${row}`
            }
            for (var column=1; column <= column_count; column++) {
                if ($(`#td-${column}-${row}`).length == 0) {
                    tr.append($("<td>")
                        .attr("id", key(column, row))
                        .addClass(`cell row-${row} col-${column}`)
                        .attr("col", column)
                        .attr("row", row)
                    );
                }
            }
        }
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
                }));
            }
        } catch(e) {
            // ignore
        }
    }

    window.run = (job) => {
        console.log("No worker for", job)
    }

    window.log = (message) => {
        console.log(message);
    }

})();