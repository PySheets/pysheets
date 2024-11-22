"""
Copyright 2024 - All Rights Reserved - chrislaffra.com - See LICENSE

LTK (Little Toolkit) is a library for building client-side web applications using Python and CSS.
"""

from ltk.jquery import *
from ltk.widgets import *
from ltk.pubsub import *
from ltk.logger import *

(
    ltk.Link("https://github.com/pyscript/ltk", "built with LTK")
        .addClass("ltk-built-with")
        .attr("target", "_blank")
        .appendTo(window.jQuery(window.document.body))
)
