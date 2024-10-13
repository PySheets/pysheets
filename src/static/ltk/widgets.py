# LTK - Copyright 2023 - All Rights Reserved - chrislaffra.com - See LICENSE 

from pyscript import window # type: ignore
from ltk.jquery import *
import itertools
import json
import logging
import math

__all__ = [
    "HBox", "Div", "VBox", "Container", "Card", "Preformatted", "Text", "Input", "Checkbox",
    "Label", "Button", "Link", "Strong", "Important", "Italic", "Paragraph", "Break", "Heading1",
    "Heading2", "Heading3", "Heading4", "OrderedList", "UnorderedList", "ListItem", "Span",
    "Tabs", "File", "DatePicker", "ColorPicker", "RadioGroup", "RadioButton", "Table", "TableRow",
    "TableHeader", "TableData", "HorizontalSplitPane", "VerticalSplitPane", "TextArea", "Code",
    "Image", "MenuBar", "Switch", "MenuLabel", "Menu", "Popup", "MenuPopup", "MenuItem", "Select",
    "Option", "Widget", "Form", "FieldSet", "Legend", "Tutorial", "Step", "Canvas",
]

BROWSER_SHORTCUTS = [ "Cmd+N","Cmd+T","Cmd+W", "Cmd+Q" ]
DEFAULT_CSS = {}
shortcuts = {}
timers = {}

logger = logging.getLogger("root")

class Widget(object):
    """Base class for LTK widgets."""
    classes = []
    instances = {}
    element = None
    tag = "div"

    def __init__(self, *args):
        """
        Initializes a new Widget instance.

        Args:
            *args: The content to add to this widget. Can be other widgets, strings, lists, etc.

        Sets:
            self.element: The jQuery element representing this widget.
        """
        self.element = (
            window.jQuery(f"<{self.tag}>")
                .addClass(" ".join(self.classes))
                .append(*self._flatten(args))
        )
        self._handle_css(args)

    def _handle_css(self, args):
        """Apply CSS styles passed in the args to the widget.

        Iterates through the args and checks for any that are dicts, 
        treating them as CSS style definitions to apply to the widget.
        """
        for arg in filter(lambda arg: isinstance(arg, dict), args):
            for key, value in arg.items():
                self.css(key, value)

    def _flatten(self, children):
        """Flatten a list of child widgets into a flat list.

        Arguments:
            children (list): A list of child widgets.
            Each child can be a Widget, a jQuery element. 
            Also allowed is a list or a generator of widgets.
            Finally, if one of the children is a dict, it is used to set CSS values on the receiver

        Returns:
            list: A flat list containing the child widgets and any
                grandchildren widgets.
        """
        result = []
        for child in children:
            if isinstance(child, dict):
                continue
            elif isinstance(child, Widget):
                result.append(child.element)
            elif type(child).__name__ == "generator":
                result.extend(self._flatten(child))
            elif isinstance(child, list):
                result.extend(self._flatten(child))
            elif isinstance(child, float):
                result.append(str(child))
            else:
                result.append(child)
        return result

    def css(self, property, value=None):
        """
        Get or set a computed style property. 

        Calls jQuery's css method, see https://api.jquery.com/css. If the first argument is a dict,
        it is passed to jQuery to set property values in bulk. If the first argument is a string, 
        jQuery is used to set or get that specific CSS property.

        Args:
            property:(str,dict): The CSS property or map to set/get
            value:Any The CSS value to set. Numeric values auto-convert to "px"
        """
        if isinstance(property, dict):
            property = to_js(property)
        return self.element.css(property, value) if value != None else self.element.css(property)

    def attr(self, name, value=None):
        """
        Get or set a the attribute on the underlying DOM element.

        Calls jQuery's attr method, see https://api.jquery.com/attr. 

        Args:
            name:str: The attribute to set/get on the DOM element
            value:str The value to set. 
                If value is None, this gets the value as a string. 
                Otherwise, it sets the value, which needs to be a string.
        """
        try:
            return self.element.attr(name, value) if value != None else self.element.attr(name)
        except:
            raise ValueError(f"Widget <{self}> does not have attribute {name}")

    def prop(self, name, value=None):
        """
        Get or set a the property on the underlying DOM element.

        Calls jQuery's prop method, see https://api.jquery.com/prop. 
        The difference between "attr" and "prop" becomes more clear when looking at
        a checkbox. Its checked attribute value does not change with the state of 
        the checkbox, while the checked property does. Attributes are concrete values that
        are set on a DOM element, while properties are more dynamic and symbolic.

        Args:
            name:str: The property to set/get on the DOM element
            value:str The value to set. 
                If value is None, this gets the value as a string. 
                Otherwise, it sets the value, which needs to be a string.
        """
        return self.element.prop(name, value) if value != None else self.element.prop(name)

    def val(self, value=None):
        """
        Get or set a the value on the underlying DOM form element, such as input, select, and textarea.

        Calls jQuery's val method, see https://api.jquery.com/val. 

        Args:
            value:str The value to set. 
                If value is None, this gets the value as a string. 
                Otherwise, it sets the value, which needs to be a string.
        """
        return self.element.val(value) if value != None else self.element.val()

    def height(self, value=None):
        """
        Get or set a the height on the underlying DOM element.

        Calls jQuery's height method, see https://api.jquery.com/height. 

        The difference between .css( "height" ) and .height() is that the latter
        returns a unit-less pixel value (for example, 400) while the former returns
        a value with units intact (for example, 400px). The .height() method is recommended
        when an element's height needs to be used in a mathematical calculation.

        Args:
            value:number The value to set. 
                If value is None, this gets the current height of the DOM element as a number. 
                Otherwise, it sets the height.
        """
        return self.element.height(value) if value != None else self.element.height()

    def width(self, value=None):
        """
        Get or set a the width on the underlying DOM element.

        Calls jQuery's width method, see https://api.jquery.com/width. 

        The difference between .css( "width" ) and .width() is that the latter
        returns a unit-less pixel value (for example, 400) while the former returns
        a value with units intact (for example, 400px). The .width() method is recommended
        when an element's width needs to be used in a mathematical calculation.

        Args:
            value:number The value to set. 
                If value is None, this gets the current width of the DOM element as a number. 
                Otherwise, it sets the width.
        """
        return self.element.width(value) if value != None else self.element.width()

    def find(self, selector):
        """
        Search through the DOM tree descendants of this widget and construct a new jQuery object from the
        matching elements. 

        Args:
            selector:str: A string containing a selector expression to match elements against.
        """
        return self.element.find(selector)

    def closest(self, selector):
        """
        Get the first element that matches the selector by testing the element itself and
        traversing up through its ancestors in the DOM tree.

        Args:
            selector:str: A string containing a selector expression to match elements against.
        """
        return self.element.closest(selector)

    def addClass(self, classes):
        """
        Add the specified class(es) to the current widget's DOM element.

        Args:
            classes:(str,list): One or more space-separated classes or a list of classes to be added
        """
        return self.element.addClass(classes)

    def removeClass(self, classes):
        """
        Remove the specified class(es) from the current widget's DOM element.

        Args:
            classes:(str,list): One or more space-separated classes or a list of classes to be removed
        """
        return self.element.removeClass(classes)

    def children(self, selector=None):
        """
        Search through the direct children of this widget's DOM tree and construct a new jQuery object
        from the matching elements. The .children() method differs from .find() in that .children()
        only travels a single level down the DOM tree while .find() can traverse down multiple levels
        to select descendant elements (grandchildren, etc.) as well.

        Args:
            selector:str: A string containing a selector expression to match elements against.
        """
        return self.element.children(selector)

    def text(self, text=None):
        """
        Return a string containing the combined text of the current widget's DOM tree
        or completely replace that DOM tree with a new text value.
        
        Due to variations in the HTML parsers in different browsers, the text returned may vary in newlines
        and other white space.

        Args:
            text:str: A string that to replace the current widget's DOM tree with.
        """
        return self.element.text() if text is None else self.element.text(text)

    def html(self, html=None):
        """
        Return a string containing the combined "innerHTML" of the current widget's DOM tree
        or completely replace that DOM tree with new html.
        
        When .html()) is used to set an element's content, any content that was in that element
        is completely replaced by the new content. Additionally, jQuery removes other constructs
        such as data and event handlers from child elements before replacing those elements with 
        the new content.

        Args:
            text:str: A string that to replace the current widget's DOM tree with.
        """
        return self.element.html() if html is None else self.element.html(html)

    def append(self, *children):
        """
        Append children to the current widget. Each child can be a Widget, a jQuery element, or a 
        nested list of the same.

        Args:
            selector:str: A string containing a selector expression to match elements against.
        """
        return self.element.append(*self._flatten(children))

    def appendTo(self, target):
        """
        Append the current widget at the end of the children list in target.

        Args:
            target:(Widget,Element): An LTK widget or a jQuery element
        """
        target = target.element if isinstance(target, Widget) else target
        return self.element.appendTo(target)

    def empty(self):
        """
        Remove all DOM elements and event handlers in the current widget's DOM tree. 
        """
        return self.element.empty()

    def on(self, events, selector=None, data=None, handler=None):
        """
        Register an event handler for DOM or application-level events.

        Args:
            events:str: A string containing one or more space-separated event types and
                optional namespaces, such as "click" or "keydown.myPlugin".
            selector:str A selector string to filter the descendants of the selected elements
                that trigger the event. If the selector is None or omitted, the event
                is always triggered when it reaches the selected element.
            handler:function A Python function that is called when the event happens.
        """
        if handler is None:
            if data is None:
                handler = selector
                selector = None
            else:
                handler = data
                data = None
        assert handler is not None, "The handler argument should be a valid Python function"
        return self.element.on(events, selector, data, proxy(handler))

    def animate(self, properties, duration=None, easing=None, complete=None):
        """
        Perform a custom animation of a set of CSS properties.

        See https://api.jquery.com/animate/#animate-properties-options.

        Args:
            events:dict: An map of CSS properties and values that the animation will move toward.
            duration:number The amount of milliseconds this animation should take.
            easing:string A string indicating which easing function to use for the transition.
            complete:function A Python function that is called when the animation is done.
        """
        if isinstance(properties, dict):
            properties = to_js(properties)
        return self.element.animate(properties, duration, easing, proxy(complete))

    def __getattr__(self, name):
        try:
            return getattr(self.element, name)
        except:
            raise AttributeError(f"LTK widget {self} does not have attribute {name}")

    def toJSON(self, *args):
        return f"[{self.__class__.__name__}|{','.join(args)}]"



class HBox(Widget):
    """ Lays out its child widgets horizontally """
    classes = [ "ltk-hbox" ]


class Div(Widget):
    """ Wraps an HTML element of type <div> """
    classes = [ "ltk-div" ]



class VBox(Widget):
    """ Lays out its child widgets vertically """
    classes = [ "ltk-vbox" ]


class Container(Widget):
    """ Wraps an HTML element of type <div> """
    classes = [ "ltk-container" ]


class Card(Container):
    """ A container with special styling looking like a card """
    classes = [ "ltk-card" ]


class Preformatted(Widget):
    """ Wraps an HTML element of type <pre> """
    classes = [ "ltk-pre" ]
    tag = "pre"


class Text(Widget):
    """ A <div> to hold text """
    classes = [ "ltk-text" ]

    def __init__(self, *args, style=DEFAULT_CSS):
        Widget.__init__(self, *args, style)


class Input(Widget):
    """ Wraps an HTML element of type <input> """
    classes = [ "ltk-input" ]
    tag = "input"

    def __init__(self, value, style=DEFAULT_CSS):
        Widget.__init__(self, style)
        self.element.val(value)
        self.on("wheel", ltk.proxy(lambda event: None)) # ensure Chrome handles wheel events


class Checkbox(Widget):
    """ Wraps an HTML element of type <input type="checkbox"> """
    classes = [ "ltk-checkbox" ]
    tag = "input"

    def __init__(self, checked, style=DEFAULT_CSS):
        Widget.__init__(self, style)
        self.element.prop("type", "checkbox")
        self.check(checked)

    def check(self, checked):
        self.element.prop("checked", "checked" if checked else None)

    def checked(self):
        return self.element.prop("checked") == "checked"


class Span(Widget):
    """ Wraps an HTML element of type <span> """
    classes = [ "ltk-span" ]
    tag = "span"


class Switch(HBox):
    """ A checkbox with special styling to resemble a switch/toggle """
    classes = [ "ltk-switch-container ltk-hbox" ]

    def __init__(self, label, checked, style=DEFAULT_CSS):
        """
        Create a new switch

        Args:
            label:str: The label for the switch
            checked:bool Whether the switch is checked or not
        """
        def toggle_edit(event):
            checked = self.element.find(".ltk-checkbox").prop("checked")
            self.element.prop("checked", checked)
        id = f"edit-switch-{get_time()}"
        HBox.__init__(self, 
            Div(label).addClass("ltk-switch-label"),
            Checkbox(checked).attr("id", id).addClass("ltk-switch-checkbox").on("change", proxy(toggle_edit)),
            Label("").attr("value", "edit:").attr("for", id).addClass("ltk-switch"),
        )

        self.check(checked)

    def check(self, checked):
        self.element.find(".ltk-checkbox").prop("checked", "checked" if checked else None)

    def checked(self):
        return self.element.find(".ltk-checkbox").prop("checked") == "checked"

class Label(Widget):
    """ Wraps an HTML element of type <label> browser DOM element """
    classes = [ "ltk-label" ]
    tag = "label"

    def __init__(self, label, input=None, style=DEFAULT_CSS):
        Widget.__init__(self, style)
        if input:
            self.element.append(input)
        self.element.append(label)


class Button(Widget):
    """ Wraps an HTML element of type <button> element """
    classes = [ "ltk-button" ]
    tag = "button"

    def __init__(self, label:str, click, style=DEFAULT_CSS):
        """
        Initializes a new Button instance.

        Args:
            label:str: The label for the button
            click:function(event): The event handler for this button
            style:dict [optional] CSS values to set on the element
        """
        Widget.__init__(self, style)
        self.element.text(label).on("click", proxy(click))


class Link(Text):
    """ Wraps an HTML element of type <a> """
    classes = [ "ltk-a" ]
    tag = "a" 

    def __init__(self, href, *items):
        Widget.__init__(self, *items)
        self.attr("href", href)
        self.attr("target", "_blank")


class Strong(Text):
    """ Wraps an HTML element of type <strong> """
    classes = [ "ltk-strong" ]
    tag = "strong"


class Important(Text):
    """ Wraps an HTML element of type <b> """
    classes = [ "ltk-b" ]
    tag = "b"


class Italic(Text):
    """ Wraps an HTML element of type <i> """
    classes = [ "ltk-i" ]
    tag = "i" 


class Paragraph(Text):
    """ Wraps an HTML element of type <p> """
    classes = [ "ltk-p" ]
    tag = "p"


class Break(Text):
    """ Wraps an HTML element of type <br> """
    classes = [ "ltk-br" ]
    tag = "br"


class Heading1(Text):
    """ Wraps an HTML element of type <h1> """
    classes = [ "ltk-h1" ]
    tag = "h1"


class Heading2(Text):
    """ Wraps an HTML element of type <h2> """
    classes = [ "ltk-h2" ]
    tag = "h2"


class Heading3(Text):
    """ Wraps an HTML element of type <h3> """
    classes = [ "ltk-h3" ]
    tag = "h3"


class Heading4(Text):
    """ Wraps an HTML element of type <h4> """
    classes = [ "ltk-h4" ]
    tag = "h4"


class OrderedList(Container):
    """ Wraps an HTML element of type <ol> """
    classes = [ "ltk-ol" ]
    tag = "ol"


class UnorderedList(Container):
    """ Wraps an HTML element of type <ul> """
    classes = [ "ltk-ul" ]
    tag = "ul"


class ListItem(Container):
    """ Wraps an HTML element of type <li> """
    classes = [ "ltk-li" ]
    tag = "li"


class Tabs(Widget):
    """ Wraps an HTML element of type jQueryUI tabs """
    classes = [ "ltk-tabs" ]
    tag = "div"
    count = 0

    def __init__(self, *tabs):
        self.name = f"ltk-tabs-{Tabs.count}"
        Tabs.count += 1
        self.labels = UnorderedList()
        Widget.__init__(self, self.labels)
        self.attr("id", self.name)
        for tab in self._flatten(tabs):
            self.add_tab(tab)
        self._handle_css(tabs)
        self.tabs()
        self.on("tabsactivate", proxy(lambda *args: self.find(".ltk-split-pane").trigger("layout")))

    def add_tab(self, tab):
        tab_id = f"{self.name}-{self.labels.children().length}"
        self.labels.append(
            ListItem().append(Link(f"#{tab_id}").text(tab.attr("name")))
        )
        self.append(Div(tab).attr("id", tab_id))

    def active(self):
        return self.element.tabs("option", "active")

    def activate(self, index):
        self.element.tabs("option", "active", index)

    def get_tab(self, index):
        return self.element.find(f"li:nth-child({index + 1})")

    def get_panel(self, index):
        return self.element.children().eq(index + 1)


class File(Widget):
    """ Wraps an HTML element of type <input type=file> """
    classes = [ "ltk-file" ]
    tag = "input"

    def __init__(self, style=DEFAULT_CSS):
        Widget.__init__(self, style)
        self.element.attr("type", "file")


class DatePicker(Widget):
    """ Wraps an HTML element of type <input type=date> """
    classes = [ "ltk-datepicker" ]
    tag = "input"

    def __init__(self, style=DEFAULT_CSS):
        Widget.__init__(self, style)
        self.element.attr("type", "date")


class ColorPicker(Widget):
    """ Wraps an HTML element of type <input type=color> """
    classes = [ "ltk-colorpicker" ]
    tag = "input"

    def __init__(self, style=DEFAULT_CSS):
        Widget.__init__(self, style)
        self.element.attr("type", "color")


class RadioGroup(VBox):
    """ Wraps an HTML element of type collection of Radio buttons """
    classes = [ "ltk-vbox ltk-radiogroup" ]

    def __init__(self, *buttons, style=DEFAULT_CSS):
        name = f"ltk-radiogroup-{window.get_time()}"
        for button in buttons:
            button.find("input").attr("name", name)
        VBox.__init__(self, *buttons, style)


class RadioButton(Widget):
    """ Wraps an HTML element of type <input type="radio"> """
    classes = [ "ltk-radiobutton" ]
    tag = "input"

    def __init__(self, checked, style=DEFAULT_CSS):
        Widget.__init__(self, style)
        self.element.prop("type", "radio")
        self.element.attr("checked", "checked" if checked else None)


class Table(Widget):
    """ Wraps an HTML element of type <table> """
    classes = [ "ltk-table" ]
    tag = "table"

    def __init__(self, *rows):
        self.element = (
            window.table()
                .addClass(" ".join(self.classes))
                .append(*self._flatten(rows))
        )

    def title(self, column, title):
        window.tableTitle(self.element, column, title)

    def get(self, column, row):
        return window.tableGet(self.element, column, row)

    def set(self, column, row, value):
        window.tableSet(self.element, column, row, str(value))


class TableRow(Widget):
    """ Wraps an HTML element of type <tr> """
    classes = [ "ltk-tr" ]
    tag = "tr"


class TableHeader(Text):
    """ Wraps an HTML element of type <th> """
    classes = [ "ltk-th" ]
    tag = "th"


class TableData(Text):
    """ Wraps an HTML element of type <td> """
    classes = [ "ltk-td" ]
    tag = "td"


class SplitPane(Div):
    """ Lays out its child widgets horizontally or vertically with a resize handle in the center """

    def resize(self):
        position = self.get_position(self.middle) - self.get_position(self)
        self.ratio = position / self.get_size(self)
        self.layout()

    def restore(self):
        try:
            self.ratio = float(window.localStorage.getItem(self.key))
        except:
            self.ratio = 0.5
        self.layout()

    def layout(self):
        size = self.get_size(self)
        middle = self.get_size(self.middle)
        self.set_size(self.first, f"{self.ratio * size + middle}")
        self.set_size(self.last, f"{(1.0 - self.ratio) * size - middle}")
        self.set_position(self.middle, 0)
        self.first.trigger("layout")
        self.last.trigger("layout")
        window.localStorage.setItem(self.key, f"{self.ratio}")

    def __init__(self, first, last, key):
        """
        Places <code>first</code> and <code>last</code> next to each other.
        """
        self.first = first
        self.middle = Div()
        self.last = last
        self.key = f"split-{key}"
        Div.__init__(
             self,
             self.first
                .addClass(f"ltk-{self.direction}-split-pane-first"),
             self.middle
                .addClass(f"ltk-{self.direction}-split-pane-middle")
                .draggable()
                .draggable("option", "axis", self.axis)
                .draggable("option", "stop", proxy(lambda *args: self.resize())),
             self.last
                .addClass(f"ltk-{self.direction}-split-pane-last")
        )
        self.attr("id", self.key)
        self.addClass(f"ltk-split-pane")
        self.restore()
        self.layout()
        self.on("layout", proxy(lambda event: self.layout() if event.target.id == self.key else None))
        schedule(self.layout, f"layout-{self.key}")
        window.addEventListener("resize", proxy(lambda *args: self.layout()))


class HorizontalSplitPane(SplitPane):
    """ Lays out its child widgets horizontally with a resize handle in the center """
    classes = [ "ltk-horizontal-split-pane", "ltk-hbox" ]

    def __init__(self, first, last, key):
        self.first = "left"
        self.last = "right"
        self.direction = "horizontal"
        self.axis = "x"
        SplitPane.__init__(self, first, last, key)

    def get_position(self, x):
        return x.position().left

    def set_position(self, x, value):
        x.css("left", value)

    def get_size(self, x):
        return max(1, x.width())

    def set_size(self, x, value):
        x.width(value)


class VerticalSplitPane(SplitPane):
    """ Lays out its child widgets vertically with a resize handle in the center """
    classes = [ "ltk-vertical-split-pane", "ltk-vbox" ]

    def __init__(self, first, last, key):
        self.first = "top"
        self.last = "bottom"
        self.direction = "vertical"
        self.axis = "y"
        SplitPane.__init__(self, first, last, key)

    def get_position(self, x):
        return x.position().top

    def set_position(self, x, value):
        x.css("top", value)

    def get_size(self, x):
        return max(1, x.height())

    def set_size(self, x, value):
        x.height(value)


class TextArea(Text):
    """ Wraps an HTML element of type <textarea> """
    classes = [ "ltk-textarea" ]
    tag = "textarea"

    def __init__(self, text="", style=DEFAULT_CSS):
        Widget.__init__(self, style)
        self.element.text(text)


class Code(Widget):
    """ Wraps an HTML element of type block of code """
    classes = [ "ltk-code" ]
    tag = "code"
    highlighted = False

    def __init__(self, language, code, style=DEFAULT_CSS):
        Widget.__init__(self, style)
        if not hasattr(window, "hljs"):
            inject_css("https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/default.min.css")
            inject_script("https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js")
            inject_script(f"https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/{language}.min.js")
        self.element.text(code).css("opacity", 0)
        schedule(self.highlight, f"{self}.highlight")

    def highlight(self):
        if self.highlighted:
            return
        if hasattr(window, "hljs"):
            window.hljs.highlightElement(self.element[0])
            self.element.animate(to_js({ "opacity": 1}))
            self.highlighted = True
        else:
            schedule(self.highlight, f"{self}.highlight", 0.1)


class Image(Widget):
    """ Wraps an HTML element of type <img> """
    classes = [ "ltk-image" ]
    tag = "img"

    def __init__(self, src, onerror=None, style=DEFAULT_CSS):
        Widget.__init__(self, style)
        self.element.referrerPolicy = "referrer"
        self.element.attr("src", src)
        if onerror:
            self.element.attr("onerror", f'this.src = "{onerror}"')


class MenuBar(HBox):
    """ Creates a horizontal menubar """
    classes = ["ltk-menubar"]


class MenuLabel(Widget):
    """ Creates a label used in menus """
    classes = ["ltk-menulabel"]

    def __init__(self, label, style=DEFAULT_CSS):
        Widget.__init__(self, style)
        self.element.text(label)


class Menu(Widget):
    """ Creates a menu """
    classes = ["ltk-menu"]

    def __init__(self, label, *items, style=DEFAULT_CSS):
        self.label = MenuLabel(label)
        self.popup = MenuPopup(*items)
        Widget.__init__(self, self.label, self.popup, style)
        self.label.on("click", proxy(lambda event: self.show(event)))
        self.on("mouseenter", proxy(lambda event: self.replace_other(event)))

    def replace_other(self, event):
        if find(".ltk-menupopup-open").length:
            _close_all_menus()
            self.show(event)

    def show(self, event):
        """ Render the menu visible """
        _close_all_menus()
        self.popup.show(self.element)
        event.preventDefault()
        return self


class Popup(Widget):
    """ Wraps an HTML element of type div that is positioned on top of all other widgets """
    classes = [ "ltk-popup" ]

    def show(self, element):
        _close_all_menus()
        (self
            .appendTo(window.jQuery(window.document.body))
            .css("top", element.offset().top + 28)
            .css("left", min(element.offset().left + 2, window.jQuery(window.document.body).width() - self.width() - 12))
        )
        ltk.schedule(proxy(lambda: self.css("display", "block")), "ltk-menupopup")
        return self

    def close(self):
        self.css("display", "none")


class MenuPopup(Popup):
    """ Creates a menu that is a popup """
    classes = [ "ltk-menupopup" ]


class MenuItem(Widget):
    """ Creates a menuitem used inside a menu """
    classes = [ "ltk-menuitem" ]

    def __init__(self, icon, label, shortcut, selected, style=DEFAULT_CSS):
        items = [
            Text(icon).addClass("ltk-menuitem-icon"),
            Text(label).addClass("ltk-menuitem-label"),
        ] + ([
            Text(shortcut).addClass("ltk-menuitem-shortcut"),
        ] if shortcut else [])
        Widget.__init__(self, items, style)
        self.on("click", proxy(lambda event: self.select(event)))
        self.on("select", proxy(lambda event: self.select(event)))
        if shortcut in BROWSER_SHORTCUTS:
            raise ValueError(f"Cannot capture shortcut {shortcut} as the browser won't allow that")
        if shortcut:
            shortcuts[shortcut] = self
        self.label = label
        self.selected = selected

    def select(self, event):
        _close_all_menus()
        self.selected(self)
        event.preventDefault()


class Select(Widget):
    """ Wraps an HTML element of type <select> """
    classes = [ "ltk-select" ]
    tag = "select"

    def __init__(self, options, selected, handler, style=DEFAULT_CSS):
        Widget.__init__(self, 
            [
                Option(text).prop("selected", "selected" if text == selected else "")
                for text in options
            ],
            style
        )
        self.handler = handler
        self.element.on("change", proxy(lambda event: schedule(self.changed, f"{self}.changed")))

    def get_selected_index(self):
        return self.element.prop("selectedIndex")

    def get_selected_option(self):
        return self.element.find("option").eq(self.get_selected_index())

    def changed(self):
        self.handler(self.get_selected_index(), self.get_selected_option())


class Form(Widget):
    """ Wraps an HTML element of type <form> """
    classes = [ "ltk-form" ]
    tag = "form"


class FieldSet(Widget):
    """ Wraps an HTML element of type <fieldset> """
    classes = [ "ltk-fieldset" ]
    tag = "fieldset"


class Legend(Text):
    """ Wraps an HTML element of type <legend> """
    classes = [ "ltk-legend" ]
    tag = "legend"


class Option(Text):
    """ Wraps an HTML element of type <option> """
    classes = [ "ltk-option" ]
    tag = "option"


class Step(Div):
    classes = [ "ltk-step" ]

    def __init__(self, widget, buttons, content):
        Div.__init__(self, buttons, content)
        self.content = content
        self.widget = widget
        self.appendTo(ltk.find("body"))
        self.width = self.width()
        self.height = self.height()
        self.last_dimensions = self.get_widget_dimensions()

    def get_widget_dimensions(self):
        return (
            self.widget.offset().left,
            self.widget.offset().top,
            self.widget.width(),
            self.widget.height(),
        )

    def show(self):
        self.content.css("visibility", "hidden")
        self.render()
        repeat(lambda: self.fix(), f"render widget {id(self)}", 0.1)

    def render(self):
        if not getattr(self.widget, "is")(":visible"):
            return
        self.css("visibility", "visible")
        left = self.widget.offset().left + self.widget.outerWidth() + 28
        top = self.widget.offset().top
        self.css("width", 0)
        self.css("height", 0)
        self.css("left", f"{left + self.width / 2}px")
        self.css("top", f"{top + self.height / 2}px")
        self.animate(ltk.to_js({
            "opacity": 1,
            "left": left,
            "top": top,
            "width": self.width + 5,
            "height": self.height,
        }), 250, ltk.proxy(lambda: self.add_markers()))

    def fix(self):
        dimensions = self.get_widget_dimensions()
        if dimensions != self.last_dimensions:
            self.content.css("visibility", "hidden")
            self.css("visibility", "hidden")
            find(".ltk-step-marker").remove()
            schedule(self.show, f"fix {id(self)}", 1)
            self.last_dimensions = dimensions

    def add_markers(self):
        self.content.css("visibility", "visible")
        # the top part
        ltk.find("body").append(ltk.Div()
            .addClass("ltk-step-marker")
            .css("left", self.widget.offset().left)
            .css("top", self.widget.offset().top)
            .css("width", self.widget.outerWidth() + 1)
        )
        # the bottom part
        ltk.find("body").append(ltk.Div()
            .addClass("ltk-step-marker")
            .css("left", self.widget.offset().left)
            .css("top", self.widget.offset().top + self.widget.outerHeight() - 2)
            .css("width", self.widget.outerWidth() + 1)
        )
        # the left part
        ltk.find("body").append(ltk.Div()
            .addClass("ltk-step-marker")
            .css("left", self.widget.offset().left)
            .css("top", self.widget.offset().top)
            .css("height", self.widget.outerHeight())
        )
        # the right part
        ltk.find("body").append(ltk.Div()
            .addClass("ltk-step-marker")
            .css("left", self.widget.offset().left + self.widget.outerWidth() - 1)
            .css("top", self.widget.offset().top)
            .css("height", self.widget.outerHeight())
        )
        # the connector
        ltk.find("body").append(ltk.Div()
            .addClass("ltk-step-marker")
            .css("left", self.widget.offset().left + self.widget.outerWidth() - 1)
            .css("top", self.widget.offset().top + 12)
            .css("width", 32)
            .css("height", 3)
        )

    def hide(self):
        ltk.find(".ltk-step-marker").remove()
        left = self.widget.offset().left + self.widget.outerWidth() + self.width / 2 + 28
        top = self.widget.offset().top + self.height / 2
        self.content.css("visibility", "hidden")
        self.animate(ltk.to_js({
            "opacity": 0,
            "left": left,
            "top": top,
            "width": 0,
            "height": 0,
        }), 250, ltk.proxy(lambda: self.remove()))
        cancel(f"render widget {id(self)}")


class Tutorial():
    tag = None

    def __init__(self, steps):
        self.steps = steps
        self.index = 0
        self.current = None
        self.steps = steps

    def run(self):
        self.index = 0
        self.show()
        
    def close(self):
        ltk.find(".ltk-step").remove()
        ltk.find(".ltk-step-marker").remove()

    def previous(self):
        if self.current:
            self.current.hide()
        if self.index > 0:
            self.index -= 1
            self.show() 

    def next(self):
        if self.current:
            self.current.hide()
        self.index += 1
        if self.index < len(self.steps):
            self.show()

    def event(self, index):
        if index == self.index:
            self.next()

    def show(self):
        logger.info(f"[Tutorial] Run step {self.index + 1} of {len(self.steps)}")
        if self.index >= len(self.steps):
            print("Cannot run tutorial step", self.index, ". Tutorial has", len(self.steps), "steps.")
            return
        selector, event, content = self.steps[self.index]
        buttons = ltk.HBox(
            ltk.Text("⟸").on("click", ltk.proxy(lambda *args: self.previous())),
            ltk.Text("⟹").on("click", ltk.proxy(lambda *args: self.next())),
            ltk.Text("x").on("click", ltk.proxy(lambda *args: self.close())),
        ).addClass("ltk-step-buttons")
        widget = ltk.find(selector)
        self.current = Step(widget, buttons, content)
        self.current.show()
        index = self.index
        widget.on(event, ltk.proxy(lambda *args: self.event(index)))


class Canvas(Widget):
    classes = [ "ltk-canvas" ]
    tag = "canvas"

    def __init__(self, style=DEFAULT_CSS) -> None:
        self._context = None
        self._font = None
        self._fill_style = None
        self._stroke_style = None
        Widget.__init__(self, style)

    def __getattr__(self, name):
        try:
            return getattr(self.element, name)
        except:
            try:
                return getattr(self.context, name)
            except:
                raise AttributeError(f"LTK widget {self} does not have attribute {name}")
 
    def __setattr__(self, name, value):
        if name != "_context" and self._context and hasattr(self._context, name):
            setattr(self._context, name, value)
        elif name != "_context" and hasattr(self.element, name):
            setattr(self.element, name, value)
        else:
            super().__setattr__(name, value)
 
    @property
    def context(self):
        if self._context == None:
            self._context = self.element[0].getContext("2d")
        return self._context

    @property
    def stroke_style(self):
        return self._stroke_style
            
    @stroke_style.setter
    def stroke_style(self, value):
        if self._stroke_style != value:
            self._stroke_style = value
            self.context.strokeStyle = value
    
    @property
    def fill_style(self):
        return self._fill_style
            
    @fill_style.setter
    def fill_style(self, value):
        if self._fill_style != value:
            self._fill_style = value
            self.context.fillStyle = value
    
    @property
    def font(self):
        return self._font
            
    @font.setter
    def font(self, value):
        if self._font != value:
            self._font = value
            self.context.font = value
    
    def line(self, x1, y1, x2, y2):
        window.canvas.line(self.context, x1, y1, x2, y2)

    def text(self, x, y, text):
        window.canvas.text(self.context, x, y, text)

    def fill_text(self, x, y, text):
        self.context.fillText(x, y, text)

    def rect(self, x, y, w, h):
        window.canvas.rect(self.context, x, y, w, h)

    def fill_rect(self, x, y, w, h):
        self.context.fillRect(x, y, w, h)

    def circle(self, x, y, radius):
        window.canvas.circle(self.context, x, y, radius)

    def fill_circle(self, x, y, radius):
        window.canvas.fillCircle(self.context, x, y, radius)


def _close_all_menus(event=None):
    if event and window.jQuery(event.target).hasClass("ltk-menulabel"):
        return
    find(".ltk-menupopup-open").removeClass("ltk-menupopup-open")
    find(".ltk-menupopup, .ltk-popup").css("display", "none")

window.jQuery(window.document.body).on("click", proxy(_close_all_menus))

def _handle_shortcuts():
    def handle_keydown(event):
        try:
            shortcut = f"{'Cmd+' if event.metaKey else ''}{event.key.upper()}"
        except:
            shortcut = ""
        if shortcut in shortcuts:
            event.preventDefault()
            shortcuts[shortcut].select(event)
    window.jQuery(window.document).on("keydown", proxy(handle_keydown))


_handle_shortcuts()

import ltk

ltk.find('.btn').on(
    "click",
    ltk.proxy(lambda event: ltk.find(event.target).attr("id"))
)