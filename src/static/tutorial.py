"""
Copyright (c) 2024 laffra - All Rights Reserved. 

This module provides functions for creating and managing the application menu.

"""

import constants
import state
import ltk


green = { "background-color": "lightgreen" }
blue = { "background-color": "lightblue" }
yellow = { "background-color": "lightyellow" }
pink = { "background-color": "pink" }


def basics():
    """
    Render a basic tutorial.
    """
    return [
        {
            "A1": [ "50", yellow ],
            "A2": [ "100", yellow ],
            "A3": [ "=\nimport random\n\nrandom.randint(1, 100)", green ],
            "C5": [ "=A1+A2", pink ],
            "A7": [ "=sum([A1, A2, A3])", pink ],
        },
        lambda: None,
        ltk.Tutorial(
            [(
                "#A1",
                "click",
                ltk.VBox(
                    ltk.Strong("PySheets Tutorial: Welcome"),
                    ltk.Text("Next step: Click inside cell A1 to watch the tutorial."),
                ),
            ),(
                "#A3",
                "click",
                ltk.VBox(
                    ltk.Text("Cells A1 and A2 contain a literal value."),
                    ltk.Text("Cell A3 contains a Python script to return a value."),
                    ltk.Text("Next step: Click inside cell A3 to look at how to write a function."),
                ),
            ),(
                "#A7",
                "click",
                ltk.VBox(
                    ltk.Text("Cell A7 contains a Python script that combines three sheet values."),
                    ltk.Text("Hover over A7 and C5 to see the dependency graph for each cell."),
                    ltk.Text("Click the 'run script' button for cell A3 a few times to see the sheet update."),
                    ltk.Text("Final step: Click inside cell A7 to see the cell function in the editor at the right."),
                ),
            )]
        )
    ]

def charts():
    """
    Render a tutorial that explains how to create charts.
    """
    return [
        {
            "A1": [ "Country", green],    "B1": [ "Export", green],    "C1": [ "Import", green],
            "A2": [ "USA", yellow],       "B2": [ "1000", yellow],     "C2": [ "600", yellow ], 
            "A3": [ "Germany", yellow],   "B3": [ "400", yellow],      "C3": [ "150", yellow ],  
            "A4": [ "France", yellow],    "B4": [ "850", yellow],      "C4": [ "300", yellow ], 
            "B8": [ "=pysheets.get_sheet('A1:C4')", pink],
            "D7": [ "=B8.plot(kind='bar', x='Country', y=['Export', 'Import'])", pink],
        },
        lambda: None,
        ltk.Tutorial(
            [(
                "#C4",
                "click",
                ltk.VBox(
                    ltk.Strong("Tutorial: Charts"),
                    ltk.Text("In this example, the sheet contains sample data."),
                    ltk.Text("Click on C4 to start the tutorial."),
                ),
            ),(
                "#B8",
                "click",
                ltk.VBox(
                    ltk.Text("""
                        Cell B8 turns the sheet data into a Pandas DataFrame.
                        Notice the ⭐A1 button in the top right.
                        If you select an empty cell and press ⭐A1, PySheets
                        will recognize the data in the frame, generate an AI prompt,
                        and auto-generate the needed Python code for you.
                        Click on B8 to see the Python code in the editor.
                    """).width(400)
                )
            ),(
                "#D7",
                "click",
                ltk.VBox(
                    ltk.Text("""
                        Cell D7 turns the DataFrame into a chart.
                        Notice the ⭐B8 button in the top right.
                        If you select an empty cell and press ⭐B8, PySheets
                        will generate an AI prompt, and auto-generate the needed
                        Python code for you.
                        Hover the generated graphs and dataframe previews to
                        see the dependency graphs.
                        Click on D7 to see the Python code in the editor.
                    """).width(300)
                )
            )],
        )
    ]

CHESS = """
=
import ltk
import random
import chess, chess.svg

def create_board():
    board = chess.Board()
    board.selected = None
    board.highlighted = None
    
    def select(event):
        ltk.find(".selection").remove()
        tile = ltk.find(event.target).closest("div")
        if board.selected:
            move_if_legal(board.selected, tile)
            board.selected = None
        else:
            piece = tile.attr("piece")
            if piece != " ":
                board.selected = tile
                highlight(tile)
        
    lines = str(board).replace(" ", "").replace(".", " ")
    for row, pieces in enumerate(lines.split("\\n"), 1):
        ltk.find(f".row-{row}").css("height", 64)
        for col, piece in enumerate(pieces, 1):
            ltk.find(f".col-{col}").css("width", 64).css("padding-right", 0).css("padding-left", 0)
            color = "#f0d9b6" if (row + col) % 2 == 0 else "#b58863"
            ltk.find(f"#{' ABCDEFGH'[col]}{row}") \\
                .attr("position", f"{' abcdefgh'[col]}{9 - row}") \\
                .css("padding", 0) \\
                .attr("piece", piece) \\
                .addClass("tile") \\
                .attr("background", color) \\
                .css("background", color) \\
                .css("color", "transparent") \\
                .html(chess.svg.piece(chess.Piece.from_symbol(piece)) if piece.strip() else "") \\
                .on("mousedown", ltk.proxy(select))
    return board

board = create_board()

def set_piece(cell):
    piece = cell.attr("piece")
    cell.html(chess.svg.piece(chess.Piece.from_symbol(piece)) if piece.strip() else "")

def highlight(cell):
    if board.highlighted:
        board.highlighted.css("background", board.highlighted.attr("background"))
    cell.css("background", "yellow")
    board.highlighted = cell

def respond():
    moves = list(board.legal_moves)
    if not moves:
        return ltk.window.alert("CHESS MATE!")
    response = random.choice(moves)
    uci = str(response)
    start, end = ltk.find(f'[position="{uci[:2]}"]'), ltk.find(
        f'[position="{uci[2:]}"]'
    )
    move_if_legal(start, end)

def move_if_legal(start, end):
    uci = f"{start.attr('position')}{end.attr('position')}"
    move = chess.Move.from_uci(uci)
    if move in board.legal_moves:
        end.attr("piece", start.attr("piece"))
        start.attr("piece", " ")
        highlight(end)
        set_piece(start)
        set_piece(end)
        board.push(move)
        if board.turn == chess.BLACK:
            ltk.schedule(respond, "white moved, black is next", 0.1)
    else:
        print("This is not a legal move")

"Ready to play Chess!" 
""".strip()


def install_chess():
    """
    Install the chess package from PyPI.
    """
    state.UI.select(state.UI.get_cell("I1"))
    packages = ltk.find("#packages")
    if not packages.val():
        packages.val("chess")
        ltk.window.alert("PySheets will now reload and then load a chess board...")
        ltk.find("#reload-button").click()

def chess():
    """
    Create a chess game.
    """
    return [
        {
            "I1": [ CHESS, green],
        },
        install_chess,
        ltk.Tutorial(
            [(
                "#I1",
                "click",
                ltk.VBox(
                    ltk.Strong("Tutorial: Chess"),
                    ltk.Text("A cell function can change the sheet UI."),
                    ltk.Text("Click on a white piece and click where to move it."),
                    ltk.Text("Cell I1 imports 'chess', draws a board, and handles events."),
                ),
            )],
        )
    ]


def clear():
    """
    Clear the current sheet.
    """
    sheet = state.UI
    a1 = sheet.get_cell("A1")
    m10 = sheet.get_cell("M10")
    selection = sheet.multi_selection
    selection.start(a1)
    selection.extend(m10)
    selection.clear()
    ltk.find(".ltk-step, .ltk-step-marker").remove()


def show_tutorial(init_tutorial):
    """
    Show a given tutorial.
    """
    for cell in state.UI.cell_views.values():
        if cell.model.script:
            return ltk.window.alert("Please clear the sheet first, or start with an empty sheet")
    cells, init, tutorial = init_tutorial
    init()
    for key, options in cells.items():
        value, css = options
        cell = state.UI.get_cell(key)
        cell.set(value)
        cell.css(css)

    tutorial.show()


def tutorial_button(title, tutorial):
    """
    Create a tutorial button.
    """
    return (
        ltk.Button(title, lambda event: show_tutorial(tutorial()))
            .css("padding", 5)
            .css("margin", 10)
    )


def show():
    """
    Launch the tutorial selector.
    """
    if not state.UID:
        return ltk.window.alert("Please create an empty sheet and try the tutorial again.")
    ltk.find("#tutorial-dialog").remove()
    (
        ltk.Div(
            ltk.Button("✖ Clear", lambda event: clear())
                .css("padding", 5)
                .css("margin", 10),
            tutorial_button("1️⃣ Basics", basics),
            tutorial_button("2️⃣ Charts", charts),
            tutorial_button("3️⃣ Chess", chess),
        )
        .attr("id", "tutorial-dialog")
        .attr("title", "Choose a Tutorial Below...")
        .css("background", "#c2d6e8")
        .css("min-height", 0)
        .dialog()
    )

if not ltk.window.localStorage[constants.TUTORIAL_SHOWN]:
    ltk.window.localStorage[constants.TUTORIAL_SHOWN] = True
    show()
