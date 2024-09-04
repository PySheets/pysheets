"""
Copyright (c) 2024 laffra - All Rights Reserved. 

Represents a cell view in the sheet, which manages the display and behavior of a single cell.

"""

import ltk
import ltk.pubsub

import api
import constants
import history
import models
import preview
import selection
import state


class CycleError(Exception):
    """
    Represents a circular dependency in the cell calculation graph.
    """



class CellView(ltk.Widget): # pylint: disable=too-many-public-methods
    """
    Represents a cell view in the sheet, managing the display and behavior of a single cell.
    """

    observer = ltk.window.MutationObserver.new(ltk.proxy(lambda records, _: CellView.cellview_mutated(records))) # pylint: disable=unnecessary-lambda
    observer_config = ltk.to_js({
        "childList": True,
        "characterData": True,
        "attributes": True,
        "subtree": True
    })
    sheet = None

    def __init__(self, sheet, key: str, model: models.Cell, td=None):
        super().__init__()
        CellView.sheet= sheet
        self.model = model
        if not key:
            raise ValueError("Missing key for cell")
        if not self.model:
            raise ValueError(f"No model for cell {key}")
        self.element = td or ltk.find(f"#{self.model.key}")
        if not self.element.length:
            ltk.window.fillSheet(model.column, model.row)
            self.element = ltk.find(f"#{self.model.key}")
        self.running = False
        self.needs_worker = False
        self.inputs = set()
        self.dependents = set()
        if self.model.script != self.model.value:
            self.set(self.model.script, evaluate=False)
        self.on("mouseenter", ltk.proxy(lambda event: self.enter()))
        self.model.listen(self.model_changed)
        self.observer.observe(self.element[0], self.observer_config)

    @classmethod
    def cellview_mutated(cls, mutation_records):
        """
        One or more cellviews were mutated.
        """
        for key in set(record.target.id for record in mutation_records):
            if key:
                cls.sheet.cell_views[key].ui_changed()

    def ui_changed(self):
        """
        Updates the cell's value and script based on changes made in the UI.
        """
        new_value = str(self.element.attr("worker-set"))
        if new_value not in ["None", "<undefined>"]:
            self.set(new_value)
            self.element.removeAttr("worker-set")

    def model_changed(self, model, info):
        """
        Handles updates to the cell model, updating the cell's UI.

        Args:
            model (models.Cell): The cell model that was updated.
            info (dict): A dictionary containing information about the update,
            including the name of the property that changed.
        """
        if self.sheet.freeze_notifications:
            return
        if info["name"] == "script":
            self.set(model.script)
        elif info["name"] == "value":
            self.text(model.value)
        elif info["name"] == "style":
            self.css(model.style)
        ltk.schedule(self.sheet.run_ai, "run ai", 3)

    def enter(self):
        """
        Draws cell arrows and raises a preview when the cell is entered.
        """
        selection.remove_arrows(0)
        self.draw_cell_arrows()
        cell_preview = ltk.find(f"#preview-{self.model.key}")
        cell_preview.appendTo(cell_preview.parent()) # raise the preview to the top

    def set(self, script, evaluate=True):
        """
        Sets the script of the cell and evaluates it if necessary.

        Args:
            script (str): The new script to set for the cell.
            evaluate (bool, optional): When false does evaluate the new script.
        """
        self.remove_preview()
        if self.model.script != script:
            history.add(
                models.CellScriptChanged(self.model.key, self.model.script, script)
                    .apply(self.sheet.model)
            )
            self.model.script = script
        if self.sheet.current == self:
            self.sheet.editor.set(self.model.script)
            self.sheet.select(self)
        if not self.is_formula():
            self.sheet.cache[self.model.key] = api.convert(script)
        if evaluate:
            ltk.schedule(self.evaluate, f"eval-{self.model.key}")

    def is_running(self):
        """
        Determines whether the cell is currently running.
        """
        return self.running

    def start_running(self):
        """
        Starts the cell's evaluation.
        """
        self.running = True
        self.sheet.start_running(self)

    def stop_running(self):
        """
        Stops the cell's evaluation.
        """
        self.running = False
        self.sheet.stop_running(self)

    def is_formula(self):
        """
        Determines whether the cell's script is a formula.

        Returns:
            bool: True if the cell's script is a formula, False otherwise.
        """
        return isinstance(self.model.script, str) and self.model.script.startswith("=")

    def update(self, duration, value):
        """
        Updates the cell's text and value, and notifies any dependent cells.

        Args:
            duration (float): The duration in seconds of the last evaluation of the cell's script.
            value (Any): The result of evaluating the cell's script.
        """
        if self.model.script:
            count = self.sheet.counts[self.model.key]
            if count:
                if isinstance(value, str) and not "Error" in value:
                    if count > 1:
                        message = f"Ran in worker {count} times, last run took {duration:.3f}s"
                    else:
                        message = f"Ran once in worker, taking {duration:.3f}s"
                    state.console.write(
                        self.model.key,
                        f"[DAG] {self.model.key}: {message}"
                    )
        self.text(str(value))
        if value not in [self.model.value, self.model.script]:
            history.add(
                models.CellValueChanged(self.model.key, self.model.value, value)
                    .apply(self.sheet.model
                )
            )
        self.notify()
        self.model.value = value
        if self.sheet.current == self:
            self.sheet.selection.val(self.text())
        self.sheet.multi_selection.draw()

    def get_preview(self, value):
        """
        Returns a formatted HTML representation of the provided dict.

        Args:
            value (dict): The object to be converted to html.

        Returns:
            str: An HTML string.
        """
        return api.get_dict_table(value) if isinstance(value, dict) else None


    def notify(self):
        """
        Notifies any dependent cells of changes to this cell.

        This method is called when the cell's value or other properties have been updated,
        in order to trigger re-evaluation of any cells that depend on this cell's value.
        """
        for key in self.dependents:
            self.sheet.get_cell(key).evaluate()

    def worker_ready(self):
        """
        Marks the worker as ready and evaluates the cell.

        This method is called when the worker has finished executing the cell's script.
        It removes the cell from the sheet's cache, sets the running flag to False,
        and then evaluates the cell.
        """
        if self.model.key in self.sheet.cache:
            del self.sheet.cache[self.model.key]
        self.stop_running()
        self.evaluate()

    def select(self):
        """
        Selects the current cell, removes any existing cell arrows, saves the current
        selection position, sets the cell script in the editor, updates the AI prompt
        input, sets the selection text, shows the cell attributes container, sets the
        CSS editors, and scrolls the selection into view.
        """
        self.remove_arrows()
        self.sheet.editor.set(self.model.script)
        ltk.find("#ai-prompt").val(self.model.prompt)
        ltk.find("#selection").text(f"Cell: {self.model.key}")
        ltk.find("#cell-attributes-container").css("display", "block")
        self.set_css_editors()
        selection.scroll(self)

    def set_css_editors(self):
        """
        Sets the CSS editor values for the current cell based on the cell's current CSS styles.
        """
        font_family = self.css("font-family")
        ltk.find("#cell-font-family").val(font_family or constants.DEFAULT_FONT_FAMILY)

        font_size = round(ltk.window.parseFloat(self.css("font-size")))
        ltk.find("#cell-font-size").val(font_size or constants.DEFAULT_FONT_SIZE)

        vertical_align = self.css("vertical-align")
        ltk.find("#cell-vertical-align").val(vertical_align or constants.DEFAULT_VERTICAL_ALIGN)

        text_align = self.css("text-align").replace("start", "left")
        ltk.find("#cell-text-align").val(text_align or constants.DEFAULT_TEXT_ALIGN)

        font_style = self.css("font-style")
        ltk.find("#cell-font-style").val(font_style or constants.DEFAULT_FONT_STYLE)

        font_weight = {"400": "normal", "700": "bold"}[self.css("font-weight")]
        ltk.find("#cell-font-weight").val(font_weight or constants.DEFAULT_FONT_WEIGHT)

        color = api.rgb_to_hex(self.css("color")) or constants.DEFAULT_COLOR
        ltk.find("#cell-color").val(color).css("background", color)

        background = api.rgb_to_hex(self.css("background-color")) or constants.DEFAULT_FILL
        ltk.find("#cell-fill").val(background).css("background", background)

    def clear(self):
        """
        Clears the current cell by:
        - Resetting the cell's CSS styles to default values
        - Removing any preview and completion elements associated with the cell
        - Clearing the cell's text and model data
        - Removing the cell from the sheet's cache and cells dictionary
        - Adding history events for the changes made to the cell
        - Notifying the sheet that the cell has been cleared
        - Reselecting the sheet to update the UI
        """
        self.css({
            "font-family": constants.DEFAULT_FONT_FAMILY,
            "font-size": constants.DEFAULT_FONT_SIZE,
            "font-style": constants.DEFAULT_FONT_STYLE,
            "color": constants.DEFAULT_COLOR,
            "background-color": constants.DEFAULT_FILL,
            "vertical-align": constants.DEFAULT_VERTICAL_ALIGN,
            "font-weight": constants.DEFAULT_FONT_WEIGHT,
            "text-align": constants.DEFAULT_TEXT_ALIGN,
        })

        ltk.find(f"#completion-{self.model.key}").remove()
        state.console.remove(f"ai-{self.model.key}")

        self.text("")
        self.model.clear(self.sheet.model)
        self.inputs.clear()
        if self.model.key in self.sheet.cell_views:
            del self.sheet.cell_views[self.model.key]
        self.sheet.cache[self.model.key] = 0

        history.add(models.CellScriptChanged(key=self.model.key, script=""))
        history.add(models.CellValueChanged(key=self.model.key, value=""))
        history.add(models.CellStyleChanged(key=self.model.key, style={}))
        self.notify()

        self.sheet.reselect()

    def remove_preview(self):
        """
        Removes the preview element associated with the cell and removes the cell from the preview collection.
        """
        ltk.find(f"#preview-{self.model.key}").remove()
        preview.remove(self.model.key)

    def draw_cell_arrows(self):
        """
        Draws the arrows indicating dependencies between cells on the sheet.
        """
        self.draw_arrows([])
        self.adjust_arrows()

    def remove_arrows(self):
        """
        Removes any arrow markers that have been drawn on the sheet.
        """
        selection.remove_arrows()

    def report_cycle(self, seen):
        """
        Detects and reports a dependency cycle in the cell's inputs.
        
        Args:
            seen (list): A list of cell keys that have been visited so far in the dependency graph.
        
        This function is called when a dependency cycle is detected while drawing the cell's
        input arrows.  It appends the current cell's key to the `seen` list,
        constructs a string representation of the cycle, and writes an error message to the console.
        """
        seen.append(self.model.key)
        cycle = " ⬅ ".join(seen)
        state.console.write(
            self.model.key,
            f"[ERROR] {self.model.key}: Dependency cycle detected: {cycle}"
        )

    def draw_arrows(self, seen):
        """
        Draws the arrows indicating dependencies between this cell and other cells on the sheet.
        """
        if self.model.key in seen:
            self.report_cycle(seen)
            return
        seen.append(self.model.key)
        self.remove_arrows()
        if state.mobile():
            return
        if not self.inputs:
            return
        cells = [ self.sheet.get_cell(input) for input in self.inputs ]
        ltk.window.addArrow(self.create_marker(cells, "inputs-marker arrow", seen), self.element)
        self.addClass("arrow")

    def create_marker(self, cells, clazz, seen):
        """
        Creates a marker element that represents a group of cells on the sheet.
        
        The marker is a div element that is positioned to encompass the cells, and has a class
        name that can be used to style it. The marker also has an event handler attached that
        removes any arrow markers when the user moves the mouse over it.
        
        Args:
            cells (list): A list of cell objects that the marker represents.
            clazz (str): A CSS class name to apply to the marker element.
            seen (list): A list of cell keys that have been visited so far in the dependency graph.
        
        Returns:
            The created marker element.
        """
        if not cells:
            return None
        if len(cells) == 1:
            cells[0].draw_arrows(seen)
            return cells[0]
        top, left, bottom, right = 10000, 10000, 0, 0
        for cell in cells:
            position = cell.position()
            left = min(position.left, left)
            top = min(position.top, top)
            right = max(position.left + cell.outerWidth(), right)
            bottom = max(position.top + cell.outerHeight(), bottom)
        return (ltk.Div()
            .addClass("marker")
            .addClass(clazz)
            .css("left", left)
            .css("top", top)
            .width(round(right - left - 4))
            .height(round(bottom - top - 5))
            .on("mousemove", ltk.proxy(lambda event: selection.remove_arrows()))
            .appendTo(ltk.find(".sheet-grid"))
        )

    def adjust_arrows(self):
        """
        Adjusts the position of arrow lines on the sheet to account for scrolling.
        """
        ltk.find(".leader-line").appendTo(ltk.find("#sheet-scrollable"))
        container = ltk.find("#sheet-container")
        scroll_left = container.scrollLeft()
        scroll_top = container.scrollTop()
        for arrow_line in ltk.find_list(".leader-line"):
            arrow_line \
                .css("top", ltk.window.parseFloat(arrow_line.css("top")) + scroll_top - 49) \
                .css("left", ltk.window.parseFloat(arrow_line.css("left")) + scroll_left)

    def edited(self, script):
        """
        Updates the cell's value with the provided script when the user edited the cell.
        
        Args:
            script (str): The new script to set for the cell.
        """
        self.set(script)

    def get_input_cells(self):
        """
        Returns a dictionary of input cell values for the current cell.
        
        The dictionary maps the input cell keys to their current values from the sheet cache.
        This is used to provide the input values when evaluating the cell's formula or script.
        """
        return {
            key: self.sheet.cache.get(key, 0)
            for key in self.inputs
        }

    def evaluate(self):
        """
        Evaluates the cell's value based on its script or formula.
        
        If the cell represents a formula, it resolves the input cells required to evaluate it.
        Otherwise, it updates the cell's value with the provided script.
        """
        state.console.remove(self.model.key)
        if self.is_formula():
            self.resolve_inputs()
        else:
            self.update(0, self.model.script)

    def show_loading(self):
        """
        Shows a loading indicator on the cell if the worker version is set to WORKER_LOADING.
        """
        if state.WORKER_VERSION != constants.WORKER_LOADING:
            return
        text = self.text()
        if not text.startswith(constants.ICON_HOUR_GLASS):
            self.text(f"{constants.ICON_HOUR_GLASS} {text}")

    def resolve_inputs(self):
        """
        Resolves the input cells required to evaluate the current cell's formula or script.
        """
        if self.is_running():
            return
        self.start_running()
        ltk.publish(
            "Application",
            "Worker",
            constants.TOPIC_WORKER_FIND_INPUTS,
            {
                "key": self.model.key, 
                "script": self.model.script[1:]
            },
        )
        # result will arrive in handle_inputs

    def inputs_missing(self):
        """
        Checks if any of the input cells required to evaluate the current cell are missing.
        
        Returns:
            bool: True if any of the input cells are missing, False otherwise.
        """
        for key in self.inputs:
            cell = self.sheet.get_cell(key)
            if cell.is_formula() and not self.sheet.counts[key]:
                return True
        return False

    def set_inputs(self, inputs):
        """
        Sets the input cells for the current cell.
        
        This method is typically called after resolving the input cells
        required to evaluate the current cell.
        """
        self.running = False
        self.inputs = inputs
        for key in self.get_input_cells():
            cell = self.sheet.get_cell(key)
            cell.dependents.add(self.model.key)

    def handle_inputs(self, inputs):
        """
        Handles the result of resolving the input cells required to evaluate
        the current cell's formula or script.
        
        This method is called after the worker has found the input cells needed to
        evaluate the current cell.  It sets the input cells, checks if any are missing,
        and then publishes a message to the worker to run the cell's script.
        
        If any of the input cells are missing, this method will return without publishing
        the message to the worker. The cell will remain in a "loading" state until the
        missing inputs are resolved.
        
        If all input cells are present, this method will increment the cell's execution
        count, mark the cell as needing worker processing, and publish a message to the
        worker to run the cell's script.
        """
        self.stop_running()
        if self.model.key in inputs:
            self.report_cycle(inputs)
        self.set_inputs(inputs)
        if self.inputs_missing():
            return
        self.sheet.counts[self.model.key] += 1
        self.needs_worker = True
        self.show_loading()
        ltk.publish(
            "Application",
            "Worker",
            ltk.TOPIC_WORKER_RUN,
            [self.model.key, self.model.script[1:], self.get_input_cells()]
        )
        # result will arrive in handle_worker_result

    def handle_worker_result(self, result):
        """
        Handles the result of a worker job that was run to evaluate the current cell's script.
        
        This method is called after the worker has finished running the cell's script. It processes the
        result of the worker job, updating the cell's value and state accordingly.
        
        If the worker job encountered an error, this method will handle the error, displaying it in the
        console and marking the line in the editor where the error occurred.
        
        If the worker job completed successfully, this method will update the cell's value and notify
        any dependents of the cell that the value has changed.
        """
        self.stop_running()
        if self.model.script == "":
            self.update(0, "")
            return
        if result["error"]:
            error = result["error"]
            duration = result["duration"]
            lineno = result["lineno"]
            tb = result["traceback"]
            parts = error.split("'")
            if len(parts) == 3 and parts[0] == "name " and parts[2] == " is not defined":
                key = parts[1]
                if key in self.inputs:
                    # The worker job ran out of sequence, ignore this error for now
                    return
            self.update(duration, error)
            if self.sheet.current.model.key == self.model.key:
                self.sheet.editor.mark_line(lineno)
            last_tb_lines = "\n".join(tb.split("\n")[-2:])
            state.console.write(self.model.key, f"[Error] {self.model.key}: Line {lineno}: {last_tb_lines}")
            ltk.window.console.orig_log(tb)
            return
        value = result["value"]
        if isinstance(value, str):
            value = value[1:-1] if value.startswith("'") and value.endswith("'") else value
        self.update(result["duration"], value)
        self.notify()

    def __repr__(self):
        return f"cell[{self.model.key}]"
