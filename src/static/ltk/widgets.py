# pylint: disable=too-many-lines

"""
LTK - Copyright 2024 - All Rights Reserved - chrislaffra.com - See LICENSE
"""

import json
import logging
import math

from ltk.jquery import find
from ltk.jquery import get_time
from ltk.jquery import inject_css
from ltk.jquery import inject_script
from ltk.jquery import proxy
from ltk.jquery import schedule
from ltk.jquery import to_js
from ltk.jquery import window

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

    DEBUG = True

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
        args = self._flatten(args)

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

    def debug(self, *args):
        """ log a message to the console """
        if self.DEBUG:
            print(self.__class__.__name__, *args)

    def _bind(self, attribute):
        """ Establish a binding between this Widget and a model """
        def set_model_value(_=None):
            attribute.set_value(self.get_value())

        def set_widget_value(_=None):
            self.set_value(attribute.get_value())

        set_widget_value()
        attribute.listeners.append(set_widget_value)
        self.on("change", proxy(lambda event: schedule(set_model_value, f"set model {self}")))

    def set_value(self, value):
        """ Set the value of the widget. """
        if isinstance(value, ModelAttribute):
            self._bind(value)
        else:
            self._set_value(value)

    def _set_value(self, value):
        """ To be overridden by subclasses. """
        self.element.text(value)

    def get_value(self):
        """ Get the value of the widget. """
        return self._get_value()
    
    def _get_value(self):
        """ To be overridden by subclasses. """
        return self.element.text()

    def css(self, prop, value=None):
        """
        Get or set a computed style property. 

        Calls jQuery's css method, see https://api.jquery.com/css. If the first argument is a dict,
        it is passed to jQuery to set property values in bulk. If the first argument is a string, 
        jQuery is used to set or get that specific CSS property.

        Args:
            prop:(str,dict): The CSS property or map to set/get
            value:Any The CSS value to set. Numeric values auto-convert to "px"
        """
        if isinstance(prop, dict):
            prop = to_js(prop)
        return self.element.css(prop, value) if value is not None else self.element.css(prop)

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
            return self.element.attr(name, value) if value is not None else self.element.attr(name)
        except Exception as e:
            raise ValueError(f"ltk.{self.__class__.__name__} does not have attribute {name}") from e

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
        return self.element.prop(name, value) if value is not None else self.element.prop(name)

    def val(self, value=None):
        """
        Get or set a the value on the underlying DOM form element, such as input,
        select, and textarea.

        Calls jQuery's val method, see https://api.jquery.com/val. 

        Args:
            value:str The value to set. 
                If value is None, this gets the value as a string. 
                Otherwise, it sets the value, which needs to be a string.
        """
        return self.element.val(value) if value is not None else self.element.val()

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
        return self.element.height(value) if value is not None else self.element.height()

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
        return self.element.width(value) if value is not None else self.element.width()

    def find(self, selector):
        """
        Search through the DOM tree descendants of this widget and construct a new jQuery
        object from the matching elements. 

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

    def addClass(self, classes): # pylint: disable=invalid-name
        """
        Add the specified class(es) to the current widget's DOM element.

        Args:
            classes:(str,list): One or more space-separated classes or a list of classes to be added
        """
        return self.element.addClass(classes)

    def removeClass(self, classes): # pylint: disable=invalid-name
        """
        Remove the specified class(es) from the current widget's DOM element.

        Args:
            classes:(str,list): One or more space-separated classes or a list of classes to remove
        """
        return self.element.removeClass(classes)

    def children(self, selector=None):
        """
        Search through the direct children of this widget's DOM tree and construct a new jQuery
        object from the matching elements. The .children() method differs from .find() in that
        .children() only travels a single level down the DOM tree while .find() can traverse down
        multiple levels to select descendant elements (grandchildren, etc.) as well.

        Args:
            selector:str: A string containing a selector expression to match elements against.
        """
        return self.element.children(selector)

    def text(self, text=None):
        """
        Return a string containing the combined text of the current widget's DOM tree
        or completely replace that DOM tree with a new text value.
        
        Due to variations in the HTML parsers in different browsers, the text returned may vary
        in newlines and other white space.

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

    def appendTo(self, target): # pylint: disable=invalid-name
        """
        Append the current widget at the end of the children list in target.

        Args:
            target:(Widget,Element): An LTK widget or a jQuery element
        """
        element = target.element if isinstance(target, Widget) else target
        return self.element.appendTo(element)

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
        return self.element.on(events, selector, data, handler)

    def animate(self, properties, duration=400, easing="swing", complete=None):
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
        return self.element.animate(properties, duration, easing, complete and proxy(complete))

    def __getattr__(self, name):
        try:
            return getattr(self.element, name)
        except Exception as e:
            raise AttributeError(f"Widget {self.__class__.__name__} does not have attribute {name}") from e

    def toJSON(self, *args): # pylint: disable=invalid-name
        """ Return a JSON representation of the widget """
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

    def __init__(self, value="", style=None):
        Widget.__init__(self, style or DEFAULT_CSS)
        self.set_value(value)

    def _get_value(self):
        return self.element.text()

    def _set_value(self, value):
        return self.element.text(value)


class Model():
    """ A model that can be bound to a widget """

    def __init__(self):
        for name, value in self.__class__.__dict__.items():
            if not name.startswith("__") and not callable(value):
                object.__setattr__(self, name,
                    ModelAttribute(self, name, getattr(self.__class__, name))
                )

    def __setattr__(self, name: str, value):
        if hasattr(self, name) and isinstance(getattr(self, name), ModelAttribute):
            attribute = getattr(self, name)
            attribute.set_value(value)
            try:
                self.changed(name, value)
            except Exception as e: #  pylint: disable=broad-except
                print(e)
        else:
            object.__setattr__(self, name, value)

    def decode(self, json_encoding: str):
        """ Decode the JSON encoding of the model """
        try:
            for name, value in json.loads(json_encoding).items():
                setattr(self, name, value)
        except Exception as e: # pylint: disable=broad-except
            print("Decode error: ", e)

    def encode(self):
        """ Encode the model as JSON """
        return json.dumps({
            name: value.get()
            for name, value in self.__dict__.items()
            if isinstance(value, ModelAttribute)
        })

    def changed(self, name, value):
        """ Called when an attribute of the model has changed """


class LocalStorageModel(Model):
    """ A model that is stored in the browser's local storage """

    __store = window.localStorage

    def __init__(self, key=None):
        Model.__init__(self)
        key = key or f"{self.__class__.__name__}-{get_time()}"
        self.decode(self.__store.getItem(key))
        self.key = key

    def changed(self, name, value):
        """ Called when an attribute of the model has changed """
        if hasattr(self, "key"):
            self.__store.setItem(self.key, self.encode())

    @classmethod
    def load(cls):
        """ Load all models of this type from local storage """
        return [ cls(key) for key in window.Object.keys(cls.__store)]


class ModelAttribute():
    """ A specific attribute of a Model """
    def __init__(self, model: Model, name: str, value):
        self.model = model
        self.name = name
        self.value = value
        self.listeners = []

    def get_value(self):
        """ Get the value of the attribute """
        return self.value

    def set_value(self, value):
        """ Set the value of the attribute """
        typed_value = type(self.value)(value)
        if typed_value == self.value:
            return
        self.value = typed_value
        self.model.changed(self.name, self.value)
        for listener in self.listeners:
            listener(self)

    def __int__(self): return int(self.value)         # pylint: disable=multiple-statements
    def __bool__(self): return bool(self.value)        # pylint: disable=multiple-statements
    def __float__(self): return float(self.value)       # pylint: disable=multiple-statements
    def __str__(self): return str(self.value)    # pylint: disable=multiple-statements

    def __neg__(self): return -self.value        # pylint: disable=multiple-statements
    def __pos__(self): return +self.value        # pylint: disable=multiple-statements
    def __invert__(self): return ~self.value     # pylint: disable=multiple-statements

    def __add__(self, value):       return self.value + value        # pylint: disable=multiple-statements
    def __sub__(self, value):       return self.value - value        # pylint: disable=multiple-statements
    def __mul__(self, value):       return self.value * value        # pylint: disable=multiple-statements
    def __truediv__(self, value):   return self.value / value        # pylint: disable=multiple-statements
    def __mod__(self, value):       return self.value % value        # pylint: disable=multiple-statements
    def __floordiv__(self, value):  return self.value // value       # pylint: disable=multiple-statements
    def __pow__(self, value):       return self.value ** value       # pylint: disable=multiple-statements
    def __matmul__(self, value):    return self.value @ value        # pylint: disable=multiple-statements

    def __radd__(self, value):       return value + self.value       # pylint: disable=multiple-statements
    def __rsub__(self, value):       return value - self.value       # pylint: disable=multiple-statements
    def __rmul__(self, value):       return value * self.value       # pylint: disable=multiple-statements
    def __rtruediv__(self, value):   return value / self.value       # pylint: disable=multiple-statements
    def __rmod__(self, value):       return value % self.value       # pylint: disable=multiple-statements
    def __rfloordiv__(self, value):  return value // self.value      # pylint: disable=multiple-statements
    def __rpow__(self, value):       return value ** self.value      # pylint: disable=multiple-statements
    def __rmatmul__(self, value):    return value @ self.value       # pylint: disable=multiple-statements

    def __and__(self, value):       return self.value & value        # pylint: disable=multiple-statements
    def __or__(self, value):        return self.value | value        # pylint: disable=multiple-statements
    def __xor__(self, value):       return self.value ^ value        # pylint: disable=multiple-statements
    def __rshift__(self, value):    return self.value >> value       # pylint: disable=multiple-statements
    def __lshift__(self, value):    return self.value << value       # pylint: disable=multiple-statements

    def __rand__(self, value):       return value & self.value       # pylint: disable=multiple-statements
    def __ror__(self, value):        return value | self.value       # pylint: disable=multiple-statements
    def __rxor__(self, value):       return value ^ self.value       # pylint: disable=multiple-statements
    def __rrshift__(self, value):    return value >> self.value      # pylint: disable=multiple-statements
    def __rlshift__(self, value):    return value << self.value      # pylint: disable=multiple-statements

    def __iadd__(self, value):       self.value += value        # pylint: disable=multiple-statements
    def __isub__(self, value):       self.value -= value        # pylint: disable=multiple-statements
    def __imul__(self, value):       self.value *= value        # pylint: disable=multiple-statements
    def __itruediv__(self, value):   self.value /= value        # pylint: disable=multiple-statements
    def __imod__(self, value):       self.value %= value        # pylint: disable=multiple-statements
    def __ifloordiv__(self, value):  self.value //= value       # pylint: disable=multiple-statements
    def __ipow__(self, value):       self.value **= value       # pylint: disable=multiple-statements
    def __imatmul__(self, value):    self.value @= value        # pylint: disable=multiple-statements
    def __iand__(self, value):       self.value &= value        # pylint: disable=multiple-statements
    def __ior__(self, value):        self.value |= value        # pylint: disable=multiple-statements
    def __ixor__(self, value):       self.value ^= value        # pylint: disable=multiple-statements
    def __irshift__(self, value):    self.value >>= value       # pylint: disable=multiple-statements
    def __ilshift__(self, value):    self.value <<= value       # pylint: disable=multiple-statements

    def __divmod__(self, value):    return divmod(self.value, value)    # pylint: disable=multiple-statements
    def __rdivmod__(self, value):   return divmod(value, self.value)    # pylint: disable=multiple-statements
    def __abs__(self):              return abs(self.value)              # pylint: disable=multiple-statements
    def __index__(self):            return self.value                   # pylint: disable=multiple-statements
    def __round__(self ):           return round(self.value)            # pylint: disable=multiple-statements
    def __trunc__(self):            return math.trunc(self.value)       # pylint: disable=multiple-statements
    def __floor__(self):            return math.floor(self.value)       # pylint: disable=multiple-statements
    def __ceil__(self):             return math.ceil(self.value)        # pylint: disable=multiple-statements

    def __repr__(self):
        return f'"{self.value}"' if isinstance(self.value, str) else repr(self.value)


class Input(Widget):
    """ Wraps an HTML element of type <input> """
    classes = [ "ltk-input" ]
    tag = "input"

    def __init__(self, value, style=None):
        Widget.__init__(self, style or DEFAULT_CSS)
        self.set_value(value)
        self.on("wheel", proxy(lambda event: None)) # ensure Chrome handles wheel events

    def _set_value(self, value):
        self.element.val(str(value))

    def _get_value(self):
        return self.element.val()


class Checkbox(Widget):
    """ Wraps an HTML element of type <input type="checkbox"> """
    classes = [ "ltk-checkbox" ]
    tag = "input"

    def __init__(self, checked, style=None):
        Widget.__init__(self, style or DEFAULT_CSS)
        self.element.prop("type", "checkbox")
        self.set_value(checked)

    def check(self, checked):
        """ Check or uncheck the checkbox """
        self.element.prop("checked", "checked" if checked else "")

    def checked(self):
        """ Return whether the checkbox is checked or not """
        return self.element.prop("checked")

    def _set_value(self, value):
        if value != self._get_value():
            self.check(value)

    def _get_value(self):
        return self.checked()


class Span(Widget):
    """ Wraps an HTML element of type <span> """
    classes = [ "ltk-span" ]
    tag = "span"


class Slider(Widget):
    """ Wraps a jQuery slider widget """
    classes = [ "ltk-slider" ]

    def __init__(self, value, min_value=0, max_value=10, horizontal=True, style=None):
        Widget.__init__(self, style or DEFAULT_CSS)
        self.element.slider(to_js({
            "min": min_value,
            "max": max_value,
            "value": value,
            "orientation": "horizontal" if horizontal else "vertical",
            "range": "min",
        }))
        self.set_value(value)
        self.on("slidechange", proxy(lambda *args: self.trigger("change")))

    def _set_value(self, value):
        if value != self._get_value():
            self.element.slider("value", value)

    def _get_value(self):
        return self.element.slider("value")


class Switch(HBox):
    """ A checkbox with special styling to resemble a switch/toggle """
    classes = [ "ltk-switch-container ltk-hbox" ]

    def __init__(self, label, checked, style=None):
        """
        Create a new switch

        Args:
            label:str: The label for the switch
            checked:bool Whether the switch is checked or not
        """
        def toggle_edit(event): # pylint: disable=unused-argument
            checked = self.element.find(".ltk-checkbox").prop("checked")
            self.element.prop("checked", checked)

        self.checkbox = Checkbox(checked)
        element_id = f"edit-switch-{get_time()}"
        HBox.__init__(self,
            Div(label)
                .addClass("ltk-switch-label"),
            self.checkbox
                .attr("id", element_id)
                .addClass("ltk-switch-checkbox")
                .on("change", proxy(toggle_edit)),
            Label("")
                .attr("value", "edit:")
                .attr("for", element_id)
                .addClass("ltk-switch"),
            style or DEFAULT_CSS
        )
        self.checkbox.set_value(checked)

    def check(self, checked):
        """ Check or uncheck the switch """
        self.checkbox.check(checked)

    def checked(self):
        """ Return whether the switch is checked or not """
        return self.checkbox.checked()

    def _set_value(self, value):
        self.checkbox._set_value(value) # pylint: disable=protected-access

    def _get_value(self):
        return self.checkbox._get_value() # pylint: disable=protected-access


class Label(Widget):
    """ Wraps an HTML element of type <label> browser DOM element """
    classes = [ "ltk-label" ]
    tag = "label"

    def __init__(self, label, input_widget=None, style=None):
        Widget.__init__(self, style or DEFAULT_CSS)
        self.input_widget = input_widget
        self.set_value(label)

    def _get_value(self):
        return self.element.text()

    def _set_value(self, value):
        if self.input_widget:
            element = self.input_widget.element if isinstance(self.input_widget, Widget) else self.input_widget
            self.element.empty().append(element, value)
        else:
            self.element.text(value)


class Button(Widget):
    """ Wraps an HTML element of type <button> element """
    classes = [ "ltk-button" ]
    tag = "button"

    def __init__(self, label:str, click, style=None):
        """
        Initializes a new Button instance.

        Args:
            label:str: The label for the button
            click:function(event): The event handler for this button
            style:dict [optional] CSS values to set on the element
        """
        Widget.__init__(self, style or DEFAULT_CSS)
        self.element.text(label)
        self.on("click", proxy(click))


class Link(Text):
    """ Wraps an HTML element of type <a> """
    classes = [ "ltk-a" ]
    tag = "a"

    def __init__(self, href, *items):
        Text.__init__(self)
        self.append(*items)
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
        """ Adds a new tab """
        tab_id = f"{self.name}-{self.labels.children().length}"
        self.labels.append(
            ListItem().append(Link(f"#{tab_id}").text(tab.attr("name")))
        )
        self.append(Div(tab).attr("id", tab_id))

    def active(self):
        """ Returns the index of the active tab """
        return self.element.tabs("option", "active")

    def activate(self, index):
        """ Activates a tab """
        self.element.tabs("option", "active", index)

    def get_tab(self, index):
        """ Returns the tab at the given index """
        return self.element.find(f"li:nth-child({index + 1})")

    def get_panel(self, index):
        """ Returns the panel at the given index """
        return self.element.children().eq(index + 1)


class File(Widget):
    """ Wraps an HTML element of type <input type=file> """
    classes = [ "ltk-file" ]
    tag = "input"

    def __init__(self, style=None):
        Widget.__init__(self, style or DEFAULT_CSS)
        self.element.attr("type", "file")


class DatePicker(Widget):
    """ Wraps an HTML element of type <input type=date> """
    classes = [ "ltk-datepicker" ]
    tag = "input"

    def __init__(self, style=None):
        Widget.__init__(self, style or DEFAULT_CSS)
        self.element.attr("type", "date")


class ColorPicker(Widget):
    """ Wraps an HTML element of type <input type=color> """
    classes = [ "ltk-colorpicker" ]
    tag = "input"

    def __init__(self, style=None):
        Widget.__init__(self, style or DEFAULT_CSS)
        self.element.attr("type", "color")


class RadioGroup(VBox):
    """ Wraps an HTML element of type collection of Radio buttons """
    classes = [ "ltk-vbox ltk-radiogroup" ]

    def __init__(self, *buttons, style=None):
        name = f"ltk-radiogroup-{window.get_time()}"
        for button in buttons:
            button.find("input").attr("name", name)
        VBox.__init__(self, *buttons, style or DEFAULT_CSS)


class RadioButton(Widget):
    """ Wraps an HTML element of type <input type="radio"> """
    classes = [ "ltk-radiobutton" ]
    tag = "input"

    def __init__(self, checked, style=None):
        Widget.__init__(self, style or DEFAULT_CSS)
        self.element.prop("type", "radio")
        self.element.attr("checked", "checked" if checked else None)


class Table(Widget):
    """ Wraps an HTML element of type <table> """
    classes = [ "ltk-table" ]
    tag = "table"

    def __init__(self, *rows):
        Widget.__init__(self)
        self.element = (
            window.table()
                .addClass(" ".join(self.classes))
                .append(*self._flatten(rows))
        )

    def title(self, column, title):
        """ Sets the title of a column """
        window.tableTitle(self.element, column, title)

    def get(self, column, row):
        """ Returns the value of a cell """
        return window.tableGet(self.element, column, row)

    def set(self, column, row, value):
        """ Sets the value of a cell """
        window.tableSet(self.element, column, row, str(value))


class TableRow(Widget):
    """ Wraps an HTML element of type <tr> """
    classes = [ "ltk-tr" ]
    tag = "tr"


class TableHeader(Widget):
    """ Wraps an HTML element of type <th> """
    classes = [ "ltk-th" ]
    tag = "th"


class TableData(Widget):
    """ Wraps an HTML element of type <td> """
    classes = [ "ltk-td" ]
    tag = "td"


class SplitPane(Div):
    """ Lays out its child widgets horizontally or vertically with a resize handle in the center """

    def resize(self):
        """ Resizes the split pane """
        position = self.get_position(self.middle) - self.get_position(self)
        self.ratio = position / self.get_size(self)
        self.layout()

    def restore(self):
        """ Restores the split pane to its original size """
        try:
            self.ratio = float(window.localStorage.getItem(self.key))
        except: # pylint: disable=bare-except
            self.ratio = 0.5
        self.layout()

    def layout(self):
        """ Lays out the split pane """
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
        self.addClass("ltk-split-pane")
        self.restore()
        self.layout()
        self.on("layout", proxy(
            lambda event: self.layout() if event.target.id == self.key else None
        ))
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
        """ Returns the position of the handle """
        return x.position().left

    def set_position(self, x, value):
        """ Sets the position of the handle """
        x.css("left", value)

    def get_size(self, x):
        """ Returns the size of the handle """
        return max(1, x.width())

    def set_size(self, x, value):
        """ Sets the size of the handle """
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
        """ Returns the position of the handle """
        return x.position().top

    def set_position(self, x, value):
        """ Sets the position of the handle """
        x.css("top", value)

    def get_size(self, x):
        """ Returns the size of the handle """
        return max(1, x.height())

    def set_size(self, x, value):
        """" Sets the size of the handle """
        x.height(value)


class TextArea(Widget):
    """ Wraps an HTML element of type <textarea> """
    classes = [ "ltk-textarea" ]
    tag = "textarea"

    def __init__(self, text="", style=None):
        Widget.__init__(self, style or DEFAULT_CSS)
        self.element.text(text)


class Code(Widget):
    """ Wraps an HTML element of type block of code """
    classes = [ "ltk-code" ]
    tag = "code"
    highlighted = False

    def __init__(self, language, code, style=None):
        Widget.__init__(self, style or DEFAULT_CSS)
        if not hasattr(window, "hljs"):
            inject_css("https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/default.min.css") # pylint: disable=line-too-long
            inject_script("https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js") # pylint: disable=line-too-long
            inject_script(f"https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/{language}.min.js") # pylint: disable=line-too-long
        self.element.text(code).css("opacity", 0)
        schedule(self.highlight, f"{self}.highlight")

    def highlight(self):
        """ Highlights the code using the provided language """
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

    def __init__(self, src, onerror=None, style=None):
        Widget.__init__(self, style or DEFAULT_CSS)
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

    def __init__(self, label, style=None):
        Widget.__init__(self, style or DEFAULT_CSS)
        self.element.text(label)


class Menu(Widget):
    """ Creates a menu """
    classes = ["ltk-menu"]

    def __init__(self, label, *items, style=None):
        self.label = MenuLabel(label)
        self.popup = MenuPopup(*items)
        Widget.__init__(self, self.label, self.popup, style or DEFAULT_CSS)
        self.label.on("click", None, None, proxy(lambda event: self.show(event))) # pylint: disable=unnecessary-lambda
        self.label.on("click", None, None, proxy(lambda event: self.show(event))) # pylint: disable=unnecessary-lambda

    def replace_other(self, event):
        """ Replaces the menu with the other menu """
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
        """ Closes all existing popups and shows the popup """
        _close_all_menus()
        body_width = window.jQuery(window.document.body).width()
        (self
            .appendTo(window.jQuery(window.document.body))
            .css("top", element.offset().top + 28)
            .css("left", min(element.offset().left + 2, body_width - self.width() - 12))
        )
        schedule(proxy(lambda: self.css("display", "block")), "ltk-menupopup")
        return self

    def close(self):
        """ Closes the popup """
        self.css("display", "none")


class MenuPopup(Popup):
    """ Creates a menu that is a popup """
    classes = [ "ltk-menupopup" ]


class MenuItem(Widget):
    """ Creates a menuitem used inside a menu """
    classes = [ "ltk-menuitem" ]

    def __init__(self, icon, label, shortcut, selected, style=None):
        items = [
            Text(icon).addClass("ltk-menuitem-icon"),
            Text(label).addClass("ltk-menuitem-label"),
        ] + ([
            Text(shortcut).addClass("ltk-menuitem-shortcut"),
        ] if shortcut else [])
        Widget.__init__(self, items, style or DEFAULT_CSS)
        self.on("click", proxy(lambda event: self.select(event))) # pylint: disable=unnecessary-lambda
        self.on("select", proxy(lambda event: self.select(event))) # pylint: disable=unnecessary-lambda
        if shortcut in BROWSER_SHORTCUTS:
            raise ValueError(f"Cannot capture shortcut {shortcut} as the browser won't allow that")
        if shortcut:
            shortcuts[shortcut] = self
        self.label = label
        self.selected = selected

    def select(self, event):
        """ Selects the menu item """
        _close_all_menus()
        self.selected(self)
        event.preventDefault()


class Select(Widget):
    """ Wraps an HTML element of type <select> """
    classes = [ "ltk-select" ]
    tag = "select"

    def __init__(self, options, selected, handler=None, style=None):
        Widget.__init__(self, [Option(text) for text in options], style)
        assert isinstance(options, list), f"Select: Expected options to be a list, not {type(options)}"
        self.options = options
        self.handler = handler
        self.set_value(selected)
        self.on("change", proxy(lambda event: schedule(self.changed, f"{self}.changed")))

    def get_selected_index(self):
        """  Returns the index of the selected option """
        return self.element.prop("selectedIndex")

    def set_selected_index(self, index):
        """  Returns the index of the selected option """
        return self.element.prop("selectedIndex", index)

    def get_selected_option(self):
        """ Returns the selected option """
        return self.element.find("option").eq(self.get_selected_index())

    def changed(self):
        """ Called when the selected option changes """
        if not self.handler:
            return
        self.handler(self.get_selected_index(), self.get_selected_option())
    
    def _set_value(self, value):
        if isinstance(value, int):
            value = self.options[value]
        try:
            self.set_selected_index(self.options.index(value))
        except ValueError as e:
            raise ValueError(f"Invalid value {value} for options {self.options}") from e
    def _get_value(self):
        return self.get_selected_index()



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
    """ Represents a step in a tutorial """
    classes = [ "ltk-step" ]

    def __init__(self, widget, buttons, content):
        Div.__init__(self, buttons, content)
        self.content = content
        self.widget = widget
        self.draggable({
            "drag": proxy(lambda *args: (
                find(".leader-line").remove(),
                schedule(self.show_arrow, "ltk-step-draw-arrow", 0.1)
            )),
        })

        self.on("mouseenter", proxy(lambda event: self.show_arrow()))

    def show(self):
        """ Shows the tutorial step """
        if not getattr(self.widget, "is")(":visible"):
            return
        find(".ltk-step").remove()
        self.appendTo(find("body"))
        self.css(to_js({
            "visibility": "visible",
            "opacity": 1,
            "left": self.widget.offset().left + self.widget.outerWidth() + 100,
            "top": self.widget.offset().top,
            "width": "fit-content",
        }))
        self.show_arrow()

    def show_arrow(self):
        """ Shows the arrow to indicate which widget the step is for """
        find(".leader-line").remove()
        source = self.element
        target = self.widget.element if hasattr(self.widget, "element") else self.widget
        schedule(proxy(lambda: window.addArrow(source, target)), "ltk-step-show-arrow")

    def hide(self):
        """ Hides the tutorial step """
        self.remove()


class Tutorial():
    """ Creates a tutorial """
    tag = None

    def __init__(self, steps):
        self.steps = steps
        self.index = 0
        self.steps = steps

    def run(self):
        """ Runs the tutorial """
        self.index = 0
        self.show()

    def close(self):
        """ Closes the tutorial """
        find(".leader-line, .ltk-step").remove()

    def previous(self):
        """ Goes to the previous step """
        self.close()
        if self.index > 0:
            self.index -= 1
            self.show()

    def next(self):
        """ Goes to the next step """
        self.close()
        if self.index < len(self.steps):
            self.index += 1
            self.show()

    def event(self, index):
        """ Handles the event for the current step """
        if index == self.index:
            self.next()

    def show(self):
        """ Shows the current step """
        if self.index < 0 or self.index >= len(self.steps):
            return
        selector, event, content = self.steps[self.index]
        buttons = HBox(
            Text("⟸").on("click", proxy(lambda *args: self.previous())),
            Text("⟹").on("click", proxy(lambda *args: self.next())),
            Text("x").on("click", proxy(lambda *args: self.close())),
        ).addClass("ltk-step-buttons")
        widget = find(selector)
        Step(widget, buttons, content).show()
        index = self.index
        widget.on(event, proxy(lambda *args: self.event(index)))


class Canvas(Widget):
    """  Wraps an HTML element of type <canvas> """
    classes = [ "ltk-canvas" ]
    tag = "canvas"

    def __init__(self, style=None) -> None:
        self._context = None
        self._font = None
        self._fill_style = None
        self._stroke_style = None
        Widget.__init__(self, style or DEFAULT_CSS)

    def __getattr__(self, name):
        try:
            return getattr(self.element, name)
        except: # pylint: disable=bare-except
            try:
                return getattr(self.context, name)
            except: # pylint: disable=bare-except
                error = f"Widget {self} does not have attribute {name}"
                raise AttributeError(error) # pylint: disable=raise-missing-from

    def __setattr__(self, name, value):
        if name != "_context" and self._context and hasattr(self._context, name):
            setattr(self._context, name, value)
        elif name != "_context" and hasattr(self.element, name):
            setattr(self.element, name, value)
        else:
            super().__setattr__(name, value)

    @property
    def context(self):
        """ The context for the canvas """
        if self._context is None:
            self._context = self.element[0].getContext("2d")
        return self._context

    @property
    def stroke_style(self):
        """ The stroke style for the canvas """
        return self._stroke_style

    @stroke_style.setter
    def stroke_style(self, value):
        if self._stroke_style != value:
            self._stroke_style = value
            self.context.strokeStyle = value

    @property
    def fill_style(self):
        """ The fill style for the canvas """
        return self._fill_style

    @fill_style.setter
    def fill_style(self, value):
        if self._fill_style != value:
            self._fill_style = value
            self.context.fillStyle = value

    @property
    def font(self):
        """ The font for the canvas """
        return self._font

    @font.setter
    def font(self, value):
        if self._font != value:
            self._font = value
            self.context.font = value

    def line(self, x1, y1, x2, y2):
        """ Draws a line on the canvas """
        window.canvas.line(self.context, x1, y1, x2, y2)

    def text(self, x, y, text): # pylint: disable=arguments-differ
        """ Draws the outline of a text on the canvas """
        window.canvas.text(self.context, x, y, text)

    def fill_text(self, x, y, text):
        """ Fills a text on the canvas """
        self.context.fillText(x, y, text)

    def rect(self, x, y, w, h):
        """ Draws a rectangle on the canvas """
        window.canvas.rect(self.context, x, y, w, h)

    def fill_rect(self, x, y, w, h):
        """ Fills a rectangle on the canvas """
        self.context.fillRect(x, y, w, h)

    def circle(self, x, y, radius):
        """ Draws a circle on the canvas """
        window.canvas.circle(self.context, x, y, radius)

    def fill_circle(self, x, y, radius):
        """ Fills a circle on the canvas """
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
        except: # pylint: disable=bare-except
            shortcut = ""
        if shortcut in shortcuts:
            event.preventDefault()
            shortcuts[shortcut].select(event)
    window.jQuery(window.document).on("keydown", proxy(handle_keydown))


_handle_shortcuts()
