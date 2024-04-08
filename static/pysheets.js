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

    window.CodeMirror.commands.autocomplete = function (cm) {
        window.CodeMirror.simpleHint(cm, window.CodeMirror.pythonHint);
    } 

    window.create_editor = function (element, config) {
        const editor = window.CodeMirror(element, config);
        editor.on('inputRead', function onChange(editor, input) {
            if (input.text[0] === ';' || input.text[0] === ' ' || input.text[0] === ":") {
                return;
            }
            editor.showHint({
                hint: CodeMirror.pythonHint
            });
        });
        return editor;
    }
    

})();

// Simple-hints.js for CodeMirror
(function() {
    CodeMirror.simpleHint = function(editor, getHints, givenOptions) {
      // Determine effective options based on given values and defaults.
      var options = {}, defaults = CodeMirror.simpleHint.defaults;
      for (var opt in defaults)
        if (defaults.hasOwnProperty(opt))
          options[opt] = (givenOptions && givenOptions.hasOwnProperty(opt) ? givenOptions : defaults)[opt];
      
      function collectHints(previousToken) {
        // We want a single cursor position.
        if (editor.somethingSelected()) return;
  
        var tempToken = editor.getTokenAt(editor.getCursor());
  
        // Don't show completions if token has changed and the option is set.
        if (options.closeOnTokenChange && previousToken != null &&
            (tempToken.start != previousToken.start || tempToken.type != previousToken.type)) {
          return;
        }
  
        var result = getHints(editor, givenOptions);
        if (!result || !result.list.length) return;
        var completions = result.list;
        function insert(str) {
          editor.replaceRange(str, result.from, result.to);
        }
        // When there is only one completion, use it directly.
        if (options.completeSingle && completions.length == 1) {
          insert(completions[0]);
          return true;
        }
  
        // Build the select widget
        var complete = document.createElement("div");
        complete.className = "CodeMirror-completions";
        var sel = complete.appendChild(document.createElement("select"));
        // Opera doesn't move the selection when pressing up/down in a
        // multi-select, but it does properly support the size property on
        // single-selects, so no multi-select is necessary.
        if (!window.opera) sel.multiple = true;
        for (var i = 0; i < completions.length; ++i) {
          var opt = sel.appendChild(document.createElement("option"));
          opt.appendChild(document.createTextNode(completions[i]));
        }
        sel.firstChild.selected = true;
        sel.size = Math.min(10, completions.length);
        var pos = editor.cursorCoords(options.alignWithWord ? result.from : null);
        complete.style.left = pos.left + "px";
        complete.style.top = pos.bottom + "px";
        document.body.appendChild(complete);
        // If we're at the edge of the screen, then we want the menu to appear on the left of the cursor.
        var winW = window.innerWidth || Math.max(document.body.offsetWidth, document.documentElement.offsetWidth);
        if(winW - pos.left < sel.clientWidth)
          complete.style.left = (pos.left - sel.clientWidth) + "px";
        // Hack to hide the scrollbar.
        if (completions.length <= 10)
          complete.style.width = (sel.clientWidth - 1) + "px";
  
        var done = false;
        function close() {
          if (done) return;
          done = true;
          complete.parentNode.removeChild(complete);
        }
        function pick() {
          insert(completions[sel.selectedIndex]);
          close();
          setTimeout(function(){editor.focus();}, 50);
        }
        CodeMirror.on(sel, "blur", close);
        CodeMirror.on(sel, "keydown", function(event) {
          var code = event.keyCode;
          // Enter
          if (code == 13) {CodeMirror.e_stop(event); pick();}
          // Escape
          else if (code == 27) {CodeMirror.e_stop(event); close(); editor.focus();}
          else if (code != 38 && code != 40 && code != 33 && code != 34 && !CodeMirror.isModifierKey(event)) {
            close(); editor.focus();
            // Pass the event to the CodeMirror instance so that it can handle things like backspace properly.
            editor.triggerOnKeyDown(event);
            // Don't show completions if the code is backspace and the option is set.
            if (!options.closeOnBackspace || code != 8) {
              setTimeout(function(){collectHints(tempToken);}, 50);
            }
          }
        });
        CodeMirror.on(sel, "dblclick", pick);
  
        sel.focus();
        // Opera sometimes ignores focusing a freshly created node
        if (window.opera) setTimeout(function(){if (!done) sel.focus();}, 100);
        return true;
      }
      return collectHints();
    };
    CodeMirror.simpleHint.defaults = {
      closeOnBackspace: true,
      closeOnTokenChange: false,
      completeSingle: true,
      alignWithWord: true
    };
  })();

  // Python hint for Codemirror
  (function () {
    function forEach(arr, f) {
      for (var i = 0, e = arr.length; i < e; ++i) f(arr[i]);
    }
  
    function arrayContains(arr, item) {
      if (!Array.prototype.indexOf) {
        var i = arr.length;
        while (i--) {
          if (arr[i] === item) {
            return true;
          }
        }
        return false;
      }
      return arr.indexOf(item) != -1;
    }
  
    function scriptHint(editor, _keywords, getToken) {
      // Find the token at the cursor
      var cur = editor.getCursor(), token = getToken(editor, cur), tprop = token;
      // If it's not a 'word-style' token, ignore the token.
  
      if (!/^[\w$_]*$/.test(token.string)) {
          token = tprop = {start: cur.ch, end: cur.ch, string: "", state: token.state,
                           className: token.string == ":" ? "python-type" : null};
      }
  
      if (!context) var context = [];
      context.push(tprop);
  
      var completionList = getCompletions(token, context);
      completionList = completionList.sort();
      //prevent autocomplete for last word, instead show dropdown with one word
      if(completionList.length == 1) {
        completionList.push(" ");
      }
  
      return {list: completionList,
                from: {line: cur.line, ch: token.start},
                to: {line: cur.line, ch: token.end}};
    }
  
    CodeMirror.pythonHint = function(editor) {
      return scriptHint(editor, pythonKeywordsU, function (e, cur) {return e.getTokenAt(cur);});
    };
  
    var pythonKeywords = "and del from not while as elif global or with assert else if pass yield"
  + "break except import print class exec in raise continue finally is return def for lambda try";
    var pythonKeywordsL = pythonKeywords.split(" ");
    var pythonKeywordsU = pythonKeywords.toUpperCase().split(" ");
  
    var pythonBuiltins = "abs divmod input open staticmethod all enumerate int ord str "
  + "any eval isinstance pow sum basestring execfile issubclass print super"
  + "bin file iter property tuple bool filter len range type"
  + "bytearray float list raw_input unichr callable format locals reduce unicode"
  + "chr frozenset long reload vars classmethod getattr map repr xrange"
  + "cmp globals max reversed zip compile hasattr memoryview round __import__"
  + "complex hash min set apply delattr help next setattr buffer"
  + "dict hex object slice coerce dir id oct sorted intern ";
    var pythonBuiltinsL = pythonBuiltins.split(" ").join("() ").split(" ");
    var pythonBuiltinsU = pythonBuiltins.toUpperCase().split(" ").join("() ").split(" ");
  
    function getCompletions(token, context) {
      var found = [], start = token.string;
      function maybeAdd(str) {
        if (str.indexOf(start) == 0 && !arrayContains(found, str)) found.push(str);
      }
  
      function gatherCompletions(_obj) {
          forEach(pythonBuiltinsL, maybeAdd);
          forEach(pythonBuiltinsU, maybeAdd);
          forEach(pythonKeywordsL, maybeAdd);
          forEach(pythonKeywordsU, maybeAdd);
      }
  
      if (context) {
        // If this is a property, see if it belongs to some object we can
        // find in the current environment.
        var obj = context.pop(), base;
  
        if (obj.type == "variable")
            base = obj.string;
        else if(obj.type == "variable-3")
            base = ":" + obj.string;
  
        while (base != null && context.length)
          base = base[context.pop().string];
        if (base != null) gatherCompletions(base);
      }
      return found;
    }
  })();