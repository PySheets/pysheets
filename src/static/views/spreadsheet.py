"""
Copyright (c) 2024 laffra - All Rights Reserved. 

The SpreadsheetView class is responsible for rendering and managing the spreadsheet user interface.
It handles user interactions, such as cell selection, editing, and navigation, as well as
integrating with the underlying spreadsheet model and other components like the timeline and console.
"""

import collections
import random

import ltk
import ltk.pubsub
import api
import constants
import history
import menu
import models
import preview
import timeline
import html_maker
import selection
import state
import editor

from views.cell import CellView

completion_cache = {}


class SpreadsheetView():     # pylint: disable=too-many-instance-attributes,too-many-public-methods
    """
    The SpreadsheetView class is responsible for managing the user interface and interactions of a
    spreadsheet-like application. It handles the rendering of the spreadsheet cells, selection and
    navigation, and integration with the underlying spreadsheet model.
    """
    def __init__(self, model):
        self.model = model
        self.model.listen(self.model_changed)
        self.current = None
        self.freeze_notifications = False
        self.clear()
        ltk.subscribe(constants.PUBSUB_SHEET_ID, ltk.TOPIC_WORKER_RESULT, self.handle_worker_result)
        ltk.subscribe(constants.PUBSUB_SHEET_ID, ltk.pubsub.TOPIC_WORKER_READY, self.worker_ready)
        ltk.subscribe(constants.PUBSUB_SHEET_ID, constants.TOPIC_API_SET_CELLS, self.handle_set_cells)
        self.cell_views = {}
        self.selection = ltk.Input("").addClass("selection")
        self.multi_selection = selection.MultiSelection(self)
        self.selection_edited = False
        self.mousedown = False
        self.fill_cache()
        self.create_ui()
        self.setup_pubsub()
        ltk.window.addEventListener("beforeunload", ltk.proxy(lambda event: self.before_unload()))

    def no_notification(self):
        """ Do not notify any UI elements when models changes """
        sheet = self
        class NoNotifications:
            """ No notifications context manager """

            def __enter__(self):
                """ Enter the context manager """
                sheet.freeze_notifications = True
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                """ Leave the context manager """
                sheet.freeze_notifications = False

        return NoNotifications()

    def handle_set_cells(self, cells):
        """
        Handle a request from the worker to set a collection of cells.
        """
        with history.SingleEdit(f"Set {len(cells)} cells"):
            with self.no_notification():
                for key, value in cells.items():
                    cell = self.get_cell(key)
                    cell.set(value)

    def fill_cache(self):
        """
        Fills the completion cache with the converted values of all cells in the spreadsheet model.
        
        This cache is used by cells to provide input cell values to the worker.
        """
        for model in self.model.cells.values():
            self.cache[model.key] = api.convert(model.value)

    def model_changed(self, sheet, info):
        """
        This method is called when the underlying spreadsheet model has changed.
        
        Args:
            sheet (models.Sheet): The spreadsheet model that has changed.
            info (dict): A dictionary containing information about the specific change that occurred.
            The keys in this dictionary depend on the type of change that occurred, but may include:
                - "name": The new name of the spreadsheet.
                - "row": The row that was changed.
                - "height": The new height of the row.
                - "column": The column that was changed.
                - "width": The new width of the column.
        
        This method updates the UI.
        """
        with self.no_notification():
            field_name = info["name"]
            if field_name == "rows":
                ltk.find(f".row-{info['row']}").css("height", info['height'])
                self.reselect()
            elif field_name == "columns":
                ltk.find(f".col-{info['column']}").css("width", info['width'])
                self.reselect()
            elif field_name == "name":
                new_name = sheet.name
                if ltk.window.document.title != new_name:
                    ltk.window.document.title = new_name
                    ltk.find("#title").val(new_name)
                    history.add(models.NameChanged("", new_name).apply(self.model))
            elif field_name == "style":
                print("Change style", info)
            self.sheet_resized()

    def setup_window_listeners(self):
        """
        Sets up event listeners for column and row resizing in the spreadsheet window.
        """
        ltk.window.columnResizing = ltk.proxy(lambda event: self.column_resizing(event)) # pylint: disable=unnecessary-lambda
        ltk.window.columnResized = ltk.proxy(lambda event: self.column_resized(event)) # pylint: disable=unnecessary-lambda
        ltk.window.rowResizing = ltk.proxy(lambda event: self.row_resizing(event)) # pylint: disable=unnecessary-lambda
        ltk.window.rowResized = ltk.proxy(lambda event: self.row_resized(event)) # pylint: disable=unnecessary-lambda

    def sheet_resized(self):
        """
        Updates the multi-selection UI and reselects the current cell after the spreadsheet has been resized.
        
        This method is called after the spreadsheet has been resized by the user resizing rows or columns.
        It updates the multi-selection UI to reflect the new size of the spreadsheet, and then reselects
        the current cell to ensure that the UI is properly updated.
        """
        self.multi_selection.draw()
        self.select(self.current)

    def column_resizing(self, event):
        """
        This method is called when the user starts resizing a column in the spreadsheet.
        
        Args:
            event (Event): The event object containing information about the column resizing.
        
        This method finds the column label element that is being resized, extracts the column
        index, and updates the width of all cells in that column to match the new column width.
        It then calls the `sheet_resized()` method to update the UI and reselect the current cell.
        """
        label = ltk.find(event.target)
        column = label.attr('col')
        ltk.find(f".cell.col-{column}").css("width", round(label.width()))
        self.sheet_resized()

    def column_resized(self, event):
        """
        This method is called when the user has finished resizing a column in the spreadsheet.
        
        Args:
            event (Event): The event object containing information about the column resizing.
        
        This method finds the column label element that was resized, extracts the column index,
        updates the width of all cells in that column to match the new column width, and then
        adds a ColumnChanged event to the history to record the change.
        """
        label = ltk.find(event.target)
        column = label.attr('col')
        width = round(label.width())
        history.add(models.ColumnChanged(int(column), width).apply(self.model))

    def row_resizing(self, event):
        """
        This method is called when the user starts resizing a row in the spreadsheet.
        
        Args:
            event (Event): The event object containing information about the row resizing.
        
        This method finds the row label element that is being resized, extracts the row
        index, and updates the height of all cells in that row to match the new row height.
        It then calls the `sheet_resized()` method to update the UI and reselect the current cell.
        """
        label = ltk.find(event.target)
        row = label.attr('row')
        ltk.find(f".cell.row-{row}").css("height", round(label.height()))
        self.sheet_resized()

    def row_resized(self, event):
        """
        This method is called when the user has finished resizing a row in the spreadsheet.
        
        Args:
            event (Event): The event object containing information about the row resizing.
        
        This method finds the row label element that was resized, extracts the row index,
        updates the height of all cells in that row to match the new row height, and then
        adds a RowChanged event to the history to record the change.
        """
        label = ltk.find(event.target)
        row = int(label.attr('row'))
        height = round(label.height())
        history.add(models.RowChanged(row, height).apply(self.model))

    def get_cell(self, key):
        """
        Get the CellView instance for the given cell key.
        
        Args:
            key (str): The cell key, e.g. 'A2'.
        
        Returns:
            CellView: The CellView instance for the given cell key.
        """
        assert api.is_cell_reference(key), f"Bad key, got '{key}', expected something like 'A2'"
        if key not in self.cell_views:
            cell_model = self.model.get_cell(key)
            self.cell_views[key] = CellView(self, key, cell_model)
        return self.cell_views[key]

    def clear(self):
        """
        Clears the state of the spreadsheet, resetting the cells, cache, and counts. Also sets the current cell to None.
        """
        self.cell_views = {}
        self.cache = {}
        self.counts = collections.defaultdict(int)
        self.current = None

    def copy(self, from_cell, to_cell):
        """
        Copies the contents from one cell to another.
        
        Args:
            from_cell (CellView): The cell to copy from.
            to_cell (CellView): The cell to copy to.
        """
        to_cell.set(from_cell.model.script)
        to_cell.value.get()
        to_cell.store_edit()
        from_cell.store_edit()
        to_cell.attr("style", from_cell.attr("style"))

    def handle_worker_result(self, result):
        """
        Handles the result from the worker, updating the UI and adding a completion button if necessary.
        
        Args:
            result (dict): A dictionary containing the result from the worker process, including
                the cell key, a preview, and potentially a prompt.
        """
        key = result["key"]
        preview.add(self, key, result["preview"])
        cell: CellView = self.get_cell(key)
        cell.handle_worker_result(result)
        if result.get("prompt"):
            self.add_completion_button(key, result["prompt"])
        self.reselect()

    def add_completion_button(self, key, prompt):
        """
        Adds a AI prompt completion button to the UI for the given cell key and prompt.
        
        Args:
            key (str): The cell key, e.g. 'A2'.
            prompt (str): The prompt to be inserted when the completion button is clicked.
        """
        if ltk.find(f"#completion-{key}").length:
            return
        ltk.find(".ai-button-container").append(
            ltk.Button(f"{constants.ICON_STAR} {key}", ltk.proxy(lambda event: self.insert_prompt(prompt)))
                .addClass("small-button toolbar-button")
                .attr("id", f"completion-{key}")
        )

    def insert_prompt(self, prompt):
        """
        Inserts the given prompt into the AI prompt input field, clearing any existing prompt first.
        
        Args:
            prompt (str): The prompt to be inserted into the AI prompt input field.
        """
        ltk.find("#ai-prompt").val("")
        self.add_prompt(prompt.strip())
        self.complete_prompt()

    def add_prompt(self, extra_text):
        """
        Appends the given extra_text to the current AI prompt input field.
        
        Args:
            extra_text (str): The text to be appended to the current AI prompt.
        """
        prompt = ltk.find("#ai-prompt").val()
        newline = '\n' if prompt else ''
        ltk.find("#ai-prompt").val(f"{prompt}{newline}{extra_text}")

    def update_current_cell(self, event=None): # pylint: disable=unused-argument
        """
        Updates the current cell with the script from the editor and evaluates the cell.
        
        Args:
            event (Optional[Any]): An optional event object, not used in this method.
        """
        script = self.editor.get()
        cell = self.current
        cell.model.prompt = ltk.find("#ai-prompt").val()
        if cell and cell.model.script != script:
            cell.set(script)
            cell.evaluate()
        self.sync()

    def run_ai(self):
        """
        Schedule tasks to scan the spreadsheet for cells to make AI suggestions for.

        Searches the spreadsheet for cells that contain a url, and for rectangular regions
        of cells that could represent Pandas DataFrames.
        """
        ltk.schedule(self.find_pandas_data_frames, "find frames", 1)
        ltk.schedule(self.find_urls, "find urls", 1)

    def before_unload(self):
        """
        The user exited the page, so sync all pending changes.
        """
        self.save_screenshot()

    def sync(self):
        """
        Schedules a task to save a screenshot of the spreadsheet after a 5 second delay.
        """
        ltk.schedule(self.save_screenshot, "check edits", 5)

    def find_pandas_data_frames(self):
        """
        Scans the spreadsheet for rectangular regions of cells that could represent Pandas DataFrames,
        and adds a button to the UI to convert those regions to Pandas DataFrames.
        """
        visited = set()
        def get_width(cell_model):
            col = cell_model.column
            while True:
                col += 1
                key = api.get_key_from_col_row(col, cell_model.row)
                visited.add(key)
                if not key in self.model.cells:
                    break
            return col - cell_model.column

        def get_height(cell_model):
            row = cell_model.row
            while True:
                row += 1
                key = api.get_key_from_col_row(cell_model.column, row)
                visited.add(key)
                if not key in self.model.cells:
                    break
            return row - cell_model.row

        def add_frame(cell_model, width, height):
            for col in range(cell_model.column, cell_model.column + width):
                for row in range(cell_model.row, cell_model.row + height):
                    other_key = api.get_key_from_col_row(col, row)
                    visited.add(other_key)
            prompt = f"Convert the spreadsheet cells in range '{cell_model.key}:{other_key}'" \
                     f"by calling 'pysheets.get_sheet(range)'."
            self.add_completion_button(cell_model.key, prompt)

        cell = self.get_cell("A1")
        width = get_width(cell.model)
        height = get_height(cell.model)
        if width > 1 and height > 1:
            add_frame(cell.model, width, height)

    def save_current_position(self, key):
        """
        Saves the current selection position in the spreadsheet model's history.

        Args:
            key (Optional[str]): the key of the cell being selected.
        """
        history.add(models.SelectionChanged(key=key).apply(self.model))

    def get_url_keys(self):
        """
        Returns a list of keys for cells in the spreadsheet model that contain a URL starting with "https:".
        """
        return [
            key
            for key, cell in self.model.cells.items()
            if cell.script.startswith("https:")
        ]

    def find_urls(self):
        """
        Finds all the URLs stored in the spreadsheet model and generates a prompt to load
        the data from those URLs into a Pandas dataframe.
        """
        for key in self.get_url_keys():
            prompt = f"Load the data URL already stored in variable {key} into a " \
                     f"Pandas dataframe by calling 'pysheets.load_sheet(url)'."
            cell_model = self.get_cell(key).model
            self.add_completion_button(cell_model.key, prompt)

    def setup_selection(self):
        """
        This code sets up the event handlers for mouse interactions on the spreadsheet cells.
        """

        def mousedown(event):
            self.mousedown = False
            if ltk.find(event.target).hasClass("selection"):
                self.selection.css("caret-color", "black").focus()
                self.selection_edited = True
                return
            self.mousedown = True
            element = ltk.find(event.target).closest(".cell")
            if element.length == 0:
                return
            key = element.attr("id")
            cell = self.get_cell(key)
            if cell.hasClass("cell"):
                self.save_selection()
                if event.shiftKey:
                    self.multi_selection.extend(cell, force=True)
                else:
                    self.multi_selection.start(cell)
            event.preventDefault()

        def mousemove(event):
            if not self.mousedown:
                return
            element = ltk.find(event.target).closest(".cell")
            if element.length == 0:
                return
            key = element.attr("id")
            cell = self.get_cell(key)
            self.multi_selection.extend(cell)
            event.preventDefault()

        def mouseup(event):
            if not self.mousedown:
                return
            element = ltk.find(event.target).closest(".cell")
            if element.length == 0:
                return
            key = element.attr("id")
            cell = self.get_cell(key)
            self.multi_selection.stop(cell)
            event.preventDefault()
            ltk.find(event.target).trigger("click")

        ltk.find("#sheet") \
            .on("mousedown", ltk.proxy(mousedown)) \
            .on("mousemove", ltk.proxy(mousemove)) \
            .on("mouseup", ltk.proxy(mouseup)) \

    def keydown(self, event):
        """
        Handles navigation events for the spreadsheet application.
        
        This method dispatches navigation events to the appropriate handler based on the target element. 
        If the target is a "selection" element, it handles navigation within the selected cells. 
        If the target is a "main" element, it handles navigation within the main spreadsheet area.
        """
        target = ltk.find(event.target)
        if target.hasClass("selection"):
            self.navigate_selection(event)
        if target.hasClass("main"):
            self.navigate_main(event)

    def navigate_selection(self, event):
        """
        Handles navigation events for the selected cells in the spreadsheet application.

        This method dispatches navigation events to the appropriate handler based on the key pressed.
        If the key is "Escape", it selects the current cell.
        If the key is one of the navigation keys (Tab, Enter, Arrow keys, Page Up/Down, Home, End),
        it delegates the navigation to the `navigate_main` method.
        Otherwise, the current selection has changes and the currently selected cell is copied to the editor.
        """
        navigation_keys = [
            "Tab", "Enter", "ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "PageUp", "PageDown", "Home", "End"
        ]
        if event.key == "Escape":
            self.select(self.current)
        elif event.key in navigation_keys:
            self.navigate_main(event)
        else:
            ltk.schedule(self.copy_selection_to_editor, "copy-to-editor")
            return
        ltk.find("#main").focus()

    def save_selection(self, event=None): # pylint: disable=unused-argument
        """
        Saves the current selection in the spreadsheet application.
        
        If the selection has been edited and the current cell is not the same as the selection,
        the current cell is marked as edited with the new value from the selection. Then, the 
        spreadsheet state is synchronized.
        """
        if self.selection_edited and self.current and self.selection.val() != self.current.text():
            self.current.edited(self.selection.val())
        self.sync()

    def copy_selection_to_editor(self):
        """
        Copies the currently selected cell in the spreadsheet to the editor.
        """
        self.editor.set(self.selection.val())
        ltk.find("#ai-prompt").val(self.current.model.prompt)

    def navigate_main(self, event): # pylint: disable=too-many-branches
        """
        Handles navigation events for the main spreadsheet area.
        
        This method dispatches navigation events to the appropriate handler based on the key pressed.
        It updates the current cell selection based on the navigation keys pressed, such as
        arrow keys, Tab, Enter, Page Up/Down, Home, and End. If a single character key is pressed, 
        it sets the selection as edited and copies the current selection to the editor. 
        If the current cell has changed, it saves the current selection before navigating to the new cell.
        """
        if not self.current or event.key == "Meta":
            return
        current = self.multi_selection.cell2 if event.shiftKey else self.current
        column, row = current.model.column, current.model.row
        if event.key == "Tab":
            column += -1 if event.shiftKey else 1
        elif event.key in ["Delete", "Backspace"]:
            self.multi_selection.clear()
        elif event.key == "ArrowLeft":
            column = max(1, column - 1)
        elif event.key == "Home":
            column = 1
        elif event.key == "ArrowRight":
            column += 1
        elif event.key == "End":
            column = ltk.find("#column-header").children().length - 1
        elif event.key == "ArrowUp":
            row = max(1, row - 1)
        elif event.key == "PageDown":
            row = row + 25
        elif event.key == "PageUp":
            row = max(1, row - 25)
        elif event.key in ["ArrowDown", "Enter"]:
            row += 1

        if len(event.key) == 1:
            if self.is_command_key(event):
                self.multi_selection.handle(event)
            if event.metaKey or event.ctrlKey:
                return
            self.selection_edited = True
            self.selection.css("caret-color", "black").val("").focus()
            ltk.schedule(self.copy_selection_to_editor, "copy-to-editor")
        else:
            if self.current and (column != self.current.model.column or row != self.current.model.row):
                self.save_selection()
            cell = self.get_cell(api.get_key_from_col_row(column, row))
            if event.shiftKey:
                self.multi_selection.extend(cell, force=True)
            else:
                self.select(cell)
            event.preventDefault()

    def is_command_key(self, event):
        """
        Determines whether the given event represents a command key press, based on the user's operating system.
        
        Args:
            event (Event): The keyboard event to check.
        
        Returns:
            bool: True if the event represents a command key press, False otherwise.
        """
        is_mac = ltk.window.navigator.platform.upper().startswith("MAC")
        is_ios = ltk.window.navigator.platform.upper().startswith("I")
        is_apple = is_mac or is_ios
        return (event.metaKey or event.ctrlKey) if is_apple else event.ctrlKey

    def select(self, cell: CellView, force=False):
        """
        Selects the given cell in the spreadsheet, updating the UI to reflect the selection.
        
        Args:
            cell (CellView): The cell to select.
            force (bool, optional): If True, the selection will be updated even if the given cell
                is already selected. Defaults to False.
        """
        if self.current is cell and not force:
            return
        ltk.find(".selection").remove()
        if self.current and not self.current is cell:
            self.save_current_position(cell.model.key)
        self.current = cell
        self.multi_selection.select(cell)
        cell.select()
        self.selection_edited = False
        self.selection \
            .css("background-color", "white") \
            .css("padding", "") \
            .attr("style", cell.attr("style")) \
            .css("position", "absolute") \
            .css("color", cell.css("color")) \
            .css("left", 0) \
            .css("top", 0) \
            .css("height", "calc(100% - 8px)") \
            .css("width", "calc(100% - 8px)") \
            .appendTo(cell.element) \
            .attr("class", self.current.attr("class").replace("cell", "selection")) \
            .val(cell.text())
        self.selection.css("caret-color", "transparent")

    def reselect(self):
        """
        Reselects the currently selected cell in the spreadsheet, forcing the selection to be updated.
        """
        cell = self.current
        ltk.schedule(lambda: self.select(cell, force=True), "reselect")

    def show_loading(self):
        """
        Marks all cells in the spreadsheet that have a formula (start with "=") as loading,
        indicating that their values are being calculated.
        """
        for key, cell in self.model.cells.items():
            if cell.script.startswith("="):
                self.get_cell(key).show_loading()

    def start_running(self, cell: CellView):
        """
        Starts the cell's evaluation.
        """
        if self.current is cell:
            self.editor.start_running()

    def stop_running(self, cell: CellView):
        """
        Stops the cell's evaluation.
        """
        if self.current is cell:
            self.editor.stop_running()

    def worker_ready(self, data): # pylint: disable=unused-argument
        """
        This method is called when the worker is ready to process cells in the spreadsheet.

        It iterates through all the formula cells in the model and runs them.
        """
        for key, cell in self.model.cells.items():
            if cell.script.startswith("="):
                self.get_cell(key).worker_ready()
        self.sync()
        if self.editor.get() == "Loading...":
            self.complete_prompt()

    def save_screenshot(self):
        """
        Saves a screenshot of the spreadsheet and adds it to the history.
        
        Args:
            self (Spreadsheet): The Spreadsheet instance.
        """
        self.take_screenshot(
            lambda data_url: history.add(models.ScreenshotChanged(url=data_url or self.model.screenshot)
                .apply(self.model)
            )
        )

    def take_screenshot(self, callback):
        """
        Takes a screenshot of the spreadsheet and calls the provided callback function with the screenshot data URL.
        
        Args:
            self (Spreadsheet): The Spreadsheet instance.
            callback (callable): A function to call with the screenshot data URL.
        """
        if state.SHEET.screenshot:
            callback(state.SHEET.screenshot)

        def done(screenshot):
            state.SHEET.screenshot = screenshot
            callback(screenshot)

        if len(self.model.cells) > 300:
            done(self.get_plot_screenshot())
        else:
            options = ltk.to_js({
                "width": 200 * 4,
                "height": 150 * 4,
                "x": 0,
                "y": 48,
                "scale": 0.25,
            })
            ltk.window.html2canvas(ltk.window.document.body, options) \
                .then(ltk.proxy(lambda canvas: done(canvas.toDataURL())))

    def get_plot_screenshot(self):
        """
        Gets a screenshot of the spreadsheet's preview image, or a default screenshot.
        
        Returns:
            str: The data URL of the screenshot image.
        """
        src = ltk.find(".preview img").attr("src")
        return src if isinstance(src, str) else "/icons/screenshot.png"

    def complete_prompt(self, event=None): # pylint: disable=unused-argument
        """
        Completes a prompt by sending it to an AI model for generation, and handles the response.
        
        Args:
            self (Spreadsheet): The Spreadsheet instance.
            event (Optional[Any]): An optional event object, not used in this method.
        """
        if not ltk.find("#ai-prompt").val():
            ltk.window.alert("Please enter a prompt and then press 'generate code' again.")
        elif not self.editor.get() and "AI-generated" in self.editor.get():
            ltk.window.alert("Please select an empty cell and press 'generate code' again.")
        else:
            ltk.find("#ai-prompt").prop("disabled", "true")
            ltk.find("#ai-generate").attr("disabled", "true")
            self.editor.set("Loading...")
            prompt = ltk.find("#ai-prompt").val()
            self.request_completion(self.current.model.key, prompt)
            ltk.schedule(self.check_completion, "check-openai", 5)

    def request_completion(self, key, prompt):
        """
        Requests a code completion from an AI model and handles the response.
        
        Args:
            self (Spreadsheet): The Spreadsheet instance.
            key (str): A unique key to identify the completion request.
            prompt (str): The prompt to send to the AI model for completion.
        """
        ltk.publish(
            "Application",
            "Worker",
            constants.TOPIC_WORKER_COMPLETE,
            {
                "key": key, 
                "prompt": prompt,
            },
        )
        # the answer will arrive in self.handle_completion_request

    def check_completion(self):
        """
        Checks the status of a code completion request and updates the UI accordingly.
        
        This method is called to check the status of a code completion request.
        """
        if ltk.find("#ai-text").text() == "Loading...":
            ltk.find("#ai-generate").removeAttr("disabled")
            ltk.find("#ai-insert").attr("disabled", "true")
            ltk.find("#ai-text").text("It looks like OpenAI is overloaded. Please try again.")

    def handle_completion_request(self, completion):
        """
        Handles the response from a code completion request made to an AI model.
        
        Args:
            self (Spreadsheet): The Spreadsheet instance.
            completion (dict): A dictionary containing the key, text, and prompt of the completed code.
        """
        try:
            key = completion["key"]
            text = completion["text"]
            text = f"# This code was generated by an AI. Please check it for errors.\n\n{text.strip()}"

            if ltk.find("#ai-text").length:
                ltk.find("#ai-text").text(text)
                ltk.find("#ai-insert").removeAttr("disabled")
                return

            completion_cache[key] = text
            self.editor.set(f"=\n{text}")
            self.set_random_color()
            self.update_current_cell()
            self.run_current()
        finally:
            ltk.find("#ai-prompt").prop("disabled", "")
            ltk.find("#ai-generate").attr("disabled", "")

    def handle_code_completion(self, completions):
        """
        Handles the response from a code completion request made to an AI model.
        
        This method is called when the AI model has completed a code completion request.
        It updates the editor with the generated code and performs additional actions like
        setting the background color and running the current cell.
        
        Args:
            self (Spreadsheet): The Spreadsheet instance.
            completions (dict): A dictionary containing the key, text, and prompt of the completed code.
        """
        self.editor.handle_code_completion(completions)

    def run_current(self, event=None): # pylint: disable=unused-argument
        """
        Evaluates the current cell in the spreadsheet.
        """
        selection.remove_arrows()
        self.current.evaluate()

    def set_random_color(self):
        """
        Sets a random background color for the current cell and the selection.
        """
        pastels = [ "#ffb3ba", "#ffdfba", "#ffffba", "#baffc9", "#bae1ff" ]
        color = random.choice(pastels)
        cell = self.current
        cell.css("background-color", color)
        self.selection.css("background-color", color)
        _style = cell.model.style.copy()
        cell.model.style["background-color"] = color
        history.add(models.CellStyleChanged(cell.model.key, _style, cell.model.style).apply(self.model))

    def setup_pubsub(self):
        """
        Sets up the necessary PubSub subscriptions for handling various events related to the spreadsheet.
        """
        ltk.subscribe(constants.PUBSUB_SHEET_ID, constants.TOPIC_WORKER_COMPLETION, self.handle_completion_request)
        ltk.subscribe(constants.PUBSUB_SHEET_ID, constants.TOPIC_WORKER_CODE_COMPLETION, self.handle_code_completion)
        ltk.subscribe(constants.PUBSUB_SHEET_ID, constants.TOPIC_WORKER_INPUTS, self.handle_inputs)

    def handle_inputs(self, data):
        """
        Handles the inputs calculated by the worker for a cell in the spreadsheet.
        
        Args:
            self (Spreadsheet): The Spreadsheet instance.
            data (dict): A dictionary containing the key of the cell and the input data.
        """
        cell = self.get_cell(data["key"])
        cell.handle_inputs(data["inputs"])

    def create_ui(self):  # pylint: disable=too-many-locals
        """
        Creates the user interface for the spreadsheet, including the editor, console, timeline,
        and AI-related components.
        
        This method sets up the various UI elements and event handlers for the spreadsheet, such as the editor,
        console, timeline, and AI-related components. It also handles the layout and resizing of these elements,
        and performs other setup tasks like injecting CSS, setting the window title, and making the
        sheet scrollable and resizable.
        """
        self.editor = editor.Editor()
        self.editor.attr("id", "editor") \
            .css("overflow", "hidden") \
            .on("change",
                ltk.proxy(lambda event: self.update_current_cell(event))  # pylint: disable=unnecessary-lambda
            )

        def resize_ai(*args): # pylint: disable=unused-argument
            selection.remove_arrows()
            self.editor.refresh()

        def resize_editor(*args): # pylint: disable=unused-argument
            selection.remove_arrows()
            self.editor.refresh()

        def show_reload_button(event=None): # pylint: disable=unused-argument
            ltk.find("#reload-button").css("display", "block").addClass("small-button")

        ltk.schedule(self.editor.refresh, "refresh editor", 3)

        console = ltk.VBox(
            ltk.HBox(
                ltk.Input("")
                    .addClass("console-filter")
                    .attr("placeholder", "Filter the console..."),
                ltk.Button("clear", ltk.proxy(lambda event: state.console.clear()))
                    .addClass("console-clear")
                    .attr("title", "Clear the console")
            ),
            ltk.Div(ltk.Table()).addClass("console"),
        ).addClass("console-container internals").attr("name", "Console")

        tabs = ltk.Tabs(
            console,
            ltk.Div().addClass("timeline-container").attr("name", "Timeline"),
        ).addClass("internals")

        def set_plot_kind(index, option): # pylint: disable=unused-argument
            self.add_prompt(f"When you create the plot, make it {list(chart_options.values())[index]}.")

        chart_options = {
            "bar": "a bar graph",
            "barh": "a horizontal bar graph",
            "line": "a line plot",
            "pie": "a pie chart",
            "stem": "a stem plot",
            "stairs": "a stairs graph",
            "scatter": "a scatter plot",
            "stack": "a stack plot",
            "fill": "a fill between graph",
        }
        chart_type = ltk.Select([ltk.Option(kind) for kind in chart_options], 0, ltk.proxy(set_plot_kind))

        ai = ltk.VBox(
            ltk.HBox(
                ltk.Text().text("LLM Prompt")
                    .css("margin-right", 8),
                ltk.Button("generate code", ltk.proxy(lambda event: self.complete_prompt(event))) # pylint: disable=unnecessary-lambda
                    .addClass("small-button")
                    .attr("id", "generate-button"),
                ltk.Button("load from web", ltk.proxy(lambda event: self.load_from_web(event))) # pylint: disable=unnecessary-lambda
                    .addClass("small-button")
                    .attr("id", "load-from-web-button"),
                ltk.HBox().addClass("ai-button-container"),
                ltk.Text().text("Chart type:"),
                chart_type,
            ).addClass("ai-header"),
            ltk.TextArea(
            ).attr("id", "ai-prompt").addClass("ai-prompt").attr("placeholder", "Enter your prompt here..."),
        ).addClass("ai-container").on("resize", ltk.proxy(resize_ai))

        editor_container = ltk.VBox(
            ltk.HBox(
                ltk.Text().attr("id", "selection")
                    .text("f(x)")
                    .css("width", 70),
                ltk.HBox(
                    ltk.Text("Packages:"),
                    ltk.Input("")
                        .attr("id", "packages")
                        .css("width", 150)
                        .on("keyup", ltk.proxy(show_reload_button))
                        .val(self.model.packages),
                    ltk.Button("Reload", ltk.proxy(lambda event: self.save_packages(event))) # pylint: disable=unnecessary-lambda
                        .attr("id", "reload-button")
                        .css("display", "none"),
                    ltk.Button("run script", ltk.proxy(lambda event: self.run_current(event))) # pylint: disable=unnecessary-lambda
                        .addClass("small-button toolbar-button")
                        .attr("id", "run-button"),
                ).addClass("packages-container"),
            ),
            self.editor,
        ).addClass("editor-container").on("resize", ltk.proxy(resize_editor))

        ltk.inject_css(html_maker.make_css(self.model))
        left_panel = ltk.Div(
            ltk.Div(
                ltk.jQuery(html_maker.make_html(self.model))
            ).attr("id", "sheet-scrollable")
        ).attr("id", "sheet-container")

        editor_and_tabs = ltk.VerticalSplitPane(
            editor_container,
            tabs,
            "editor-and-console",
        )
        right_panel = ltk.VerticalSplitPane(
            ai,
            editor_and_tabs,
            "ai-and-editor",
        ).addClass("right-panel")

        if state.mobile():
            ltk.find("#main").prepend(
                ltk.VerticalSplitPane(
                    left_panel,
                    right_panel.addClass("right-panel"),
                    "sheet-and-editor",
                ).css("height", "100%")
            )
        else:
            ltk.find("#main").empty().prepend(
                ltk.HorizontalSplitPane(
                    left_panel.css("width", "70%"),
                    right_panel.css("width", "30%"),
                    "sheet-and-editor",
                ).css("height", "calc(100vh - 51px)")
            )
        if not ltk.find("#A1").length:
            raise ValueError("Error: PySheets setup problem, cannot find cell A1")
        ltk.schedule(editor_and_tabs.layout, "layout editor")
        ltk.window.adjustSheetPosition()
        self.create_top()
        ltk.find("body").focus().on("keydown", ltk.proxy(lambda event: self.keydown(event))) # pylint: disable=unnecessary-lambda
        ltk.find(".hidden").removeClass("hidden")
        state.set_title(self.model.name)
        current = self.model.selected or "A1"
        ltk.schedule(lambda: self.select(self.get_cell(current)), "select-later", 0.1)
        ltk.find(".main-editor-container").width(ltk.window.editor_width)
        ltk.find(".sheet").css("cursor", "default")
        self.show_loading()
        preview.load(self)
        ltk.schedule(self.run_ai, "run ai", 3)
        ltk.find("#main").animate(ltk.to_js({ "opacity": 1 }), constants.ANIMATION_DURATION)
        ltk.window.document.title = self.model.name
        ltk.window.makeSheetResizable()
        ltk.window.makeSheetScrollable()
        timeline.setup()
        ltk.find("#title") \
            .on("focus", ltk.proxy(lambda event: self.clear_name())) \
            .on("blur", ltk.proxy(lambda event: self.reset_name())) \
            .on("change", ltk.proxy(lambda event: self.set_name()))

    def load_from_web(self, event=None): # pylint: disable=unused-argument
        """
        Load a sheet from the specified URL by calling `pysheets.load_sheet(url)`.
        """
        self.insert_prompt("Load a sheet from the URL " \
            "https://raw.githubusercontent.com/PySheets/pysheets/main/src/datafiles/forbes-ai-50.csv " \
            "by calling 'pysheets.load_sheet(url)'.".strip()
        )

    def set_cells(self, cells):
        """
        Handle setting of cell values from a user's script.
        """
        for key, value in cells.items():
            self.get_cell(key).set(value)
            print("set", key, value)

    def clear_name(self):
        """
        Clears the title input field if it currently contains the default "Untitled Sheet" value.
        """
        if ltk.find("#title").val() == "Untitled Sheet":
            ltk.find("#title").val("")

    def reset_name(self):
        """
        Resets the title input field to the default "Untitled Sheet" value if the field is currently empty.
        """
        if ltk.find("#title").val() == "":
            ltk.find("#title").val("Untitled Sheet")

    def save_packages(self, event): # pylint: disable=unused-argument
        """
        Saves the specified Python packages and reloads the spreadsheet page with those packages.
        """
        packages = " ".join(ltk.find("#packages").val().replace(",", " ").split())
        history.add(models.PackagesChanged(packages=packages).apply(self.model))
        ltk.schedule(ltk.window.location.reload, "reload with packages", 1)

    def set_name(self):
        """
        Sets the name of the spreadsheet model to the value in the title input field.
        """
        self.model.name = ltk.find("#title").val()

    def create_top(self):
        """
        Creates the top-level UI elements for the spreadsheet, including the menu and attribute editors.
        """
        self.setup_selection()
        ltk.find("#menu").empty().append(menu.create_menu())
        ltk.find("#main").focus()
        self.create_attribute_editors()
        self.setup_window_listeners()

    def create_attribute_editors(self):
        """
        Creates the attribute editors to control font, color, alignment, and other cell formatting options. 
        """
        def set_font(index, option): # pylint: disable=unused-argument
            self.multi_selection.css("font-family", option.text())

        def set_font_size(index, option): # pylint: disable=unused-argument
            self.multi_selection.css("font-size", f"{option.text()}px")

        def set_font_weight(index, option): # pylint: disable=unused-argument
            self.multi_selection.css("font-weight", option.text())

        def set_font_style(index, option): # pylint: disable=unused-argument
            self.multi_selection.css("font-style", option.text())

        def set_color(event):
            color = ltk.find(event.target).val()
            self.multi_selection.css("color", color)
            ltk.find(event.target).css("background-color", color)
            event.preventDefault()

        def set_background(event):
            color = ltk.find(event.target).val()
            self.multi_selection.css("background-color", color)
            ltk.find(event.target).css("background-color", color)
            event.preventDefault()

        def set_vertical_align(index, option): # pylint: disable=unused-argument
            self.multi_selection.css("vertical-align", option.text())

        def set_text_align(index, option): # pylint: disable=unused-argument
            self.multi_selection.css("text-align", option.text())

        def activate_fill_colorpicker(event):
            container = ltk.find(event.target)
            container.parent().find(".cell-fill-colorpicker").click()

        def activate_color_colorpicker(event):
            container = ltk.find(event.target)
            container.parent().find(".cell-color-colorpicker").click()

        ltk.find("#cell-attributes-container").empty().append(

            ltk.Span(
                ltk.ColorPicker()
                    .on("input", ltk.proxy(lambda event:
                            ltk.schedule(lambda: set_background(event), "set color", 0.25)))
                    .val("#ffffff")
                    .attr("id", "cell-fill")
                    .addClass("cell-fill-colorpicker"),
                ltk.jQuery('<img src="/icons/format-color-fill.png">')
                    .on("click", ltk.proxy(activate_fill_colorpicker))
                    .addClass("cell-fill-icon"),
            ).addClass("cell-fill-container"),

            ltk.Span(
                ltk.ColorPicker()
                    .on("input", ltk.proxy(lambda event:
                            ltk.schedule(lambda: set_color(event), "set color", 0.25)))
                    .val("#ffffff")
                    .attr("id", "cell-color")
                    .addClass("cell-color-colorpicker"),
                ltk.jQuery('<img src="/icons/format-color-text.png">')
                    .on("click", ltk.proxy(activate_color_colorpicker))
                    .addClass("cell-color-icon"),
            ).addClass("cell-color-container"),

            ltk.Select(constants.FONT_NAMES, "Arial", set_font).attr(
                "id", "cell-font-family"
            ),
            ltk.Select(map(str, constants.FONT_SIZES), "12", set_font_size).attr(
                "id", "cell-font-size"
            ),
            ltk.Select(["normal", "italic"], "normal", set_font_style).attr(
                "id", "cell-font-style"
            ),
            ltk.Select(["normal", "bold"], "normal", set_font_weight).attr(
                "id", "cell-font-weight"
            ),
            ltk.Select(["top", "middle", "bottom"], "bottom", set_vertical_align).attr(
                "id", "cell-vertical-align"
            ),
            ltk.Select(["left", "center", "right"], "right", set_text_align).attr(
                "id", "cell-text-align"
            ),
        ).css("opacity", 0).animate(ltk.to_js({ "opacity": 1 }), constants.ANIMATION_DURATION)
        state.console.setup()

# pylint: disable=too-many-lines
