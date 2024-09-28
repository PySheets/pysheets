# LTK - Copyright 2023 - All Rights Reserved - chrislaffra.com - See LICENSE 

from ltk.jquery import *
from ltk.widgets import *
from ltk.pubsub import *
from ltk.logger import *

(
    ltk.Link("https://github.com/laffra/ltk", "built with LTK")
        .addClass("ltk-built-with")
        .attr("target", "_blank")
        .appendTo(jQuery(window.document.body))
)