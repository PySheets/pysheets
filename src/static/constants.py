"""
Copyright (c) 2024 laffra - All Rights Reserved. 

Global constants used by the UI, worker, and models.
"""

DEFAULT_COLUMN_COUNT = 26
DEFAULT_ROW_COUNT = 65
BIG_SHEET_SIZE = 2000
LARGE_PREVIEW_SIZE = 3 * 1024 * 1024

DEFAULT_COLUMN_WIDTH = 72
DEFAULT_ROW_HEIGHT = 16
DEFAULT_FONT_FAMILY = "Arial"
DEFAULT_FONT_SIZE = "12px"
DEFAULT_COLOR = "rgb(0, 0, 0)"
DEFAULT_FILL = "rgb(255, 255, 255)"
DEFAULT_STYLE = "normal"
DEFAULT_TEXT_ALIGN = "left"
DEFAULT_VERTICAL_ALIGN = "bottom"
DEFAULT_FONT_STYLE = "normal"
DEFAULT_FONT_WEIGHT = "normal"

DEFAULT_STYLE = {
    "font-family": DEFAULT_FONT_FAMILY,
    "font-size": DEFAULT_FONT_SIZE,
    "font-style": DEFAULT_FONT_STYLE,
    "color": DEFAULT_COLOR,
    "background-color": DEFAULT_FILL,
    "vertical-align": DEFAULT_VERTICAL_ALIGN,
    "font-weight": DEFAULT_FONT_WEIGHT,
    "text-align": DEFAULT_TEXT_ALIGN,
}

ANIMATION_DURATION_FAST = 150
ANIMATION_DURATION_MEDIUM = 500
ANIMATION_DURATION_SLOW = 1000
ANIMATION_DURATION_VERY_SLOW = 3000
ANIMATION_DURATION = ANIMATION_DURATION_FAST
MAX_EDITS_PER_SYNC = 500

ICON_HOUR_GLASS = "⏳"
ICON_DATAFRAME = "🐼"
ICON_STAR = "⭐"
ICON_JSON = "🔲"
ICON_PLOT = "📊"
ICON_LIST = "↕"

TILE_SIZE = 10

OTHER_EDITOR_TIMEOUT = 60

MODE_PRODUCTION = "prod"
MODE_DEVELOPMENT = "dev"
WORKER_LOADING = "Loading..."

PREVIEW_HEADER_WIDTH = 56
PREVIEW_HEADER_HEIGHT = 32

IMAGE_COLORS = [ "#3B71CA", "#9FA6B2", "#14A44D", "#DC4C64", "#E4A11B", "#54B4D3", "#FBFBFB", "#332D2D" ]

FONT_NAMES = [ "Arial", "Courier", "Roboto" ]
FONT_SIZES = list(range(6, 21)) + list(range(24, 73, 4))

TOPIC_WORKER_PRINT = "worker.print"
TOPIC_WORKER_COMPLETION = "worker.completion"
TOPIC_WORKER_COMPLETE = "worker.complete"
TOPIC_WORKER_CODE_COMPLETE = "worker.code.complete"
TOPIC_WORKER_CODE_COMPLETION = "worker.code.completion"
TOPIC_WORKER_FIND_INPUTS = "worker.find.inputs"
TOPIC_WORKER_INPUTS = "worker.inputs"
TOPIC_API_SET_CELLS = "api.set_cells"

TOPIC_WORKER_PREVIEW_IMPORT_WEB = "worker.preview.import.web"
TOPIC_WORKER_PREVIEW_IMPORTED_WEB = "worker.preview.imported.web"
TOPIC_WORKER_IMPORT_WEB = "worker.import.web"
TOPIC_WORKER_IMPORTED_WEB = "worker.imported.web"
TOPIC_WORKER_UPLOAD = "worker.import.upload"
TOPIC_WORKER_UPLOADED = "worker.imported.uploaded"

URL = "url"
PROMPT = "prompt"
PYTHON_RUNTIME = "runtime"
STATUS = "status"
SHEET_ID = "id"
ERROR = "error"

PUBSUB_STATE_ID = "State"
PUBSUB_SHEET_ID = "Application"
