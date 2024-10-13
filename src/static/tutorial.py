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
    reset_board(board)
    
    return board
        
def reset_board(board):
    board.clear()
    board.set_fen(chess.STARTING_FEN)
    
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
    
board = create_board()

castling_moves = {
    "e1g1": "h1f1",
    "e1c1": "a1d1",
    "e8g8": "h8f8",
    "e8c8": "a8d8",
}

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
        return ltk.window.alert("CHECKMATE!")
    response = random.choice(moves)
    uci = str(response)
    start, end = ltk.find(f'[position="{uci[:2]}"]'), ltk.find(
        f'[position="{uci[2:]}"]'
    )
    move_if_legal(start, end)

def castle(move):
    uci = castling_moves[move.uci()]    
    start, end = ltk.find(f'[position="{uci[:2]}"]'), ltk.find(
        f'[position="{uci[2:]}"]'
    )
    end.find(".piece").remove()
    end.attr("piece", start.attr("piece"))
    start.attr("piece", " ")
    set_piece(start)
    set_piece(end)

def reset_game():
    reset_board(board) 
    
def move_if_legal(start, end):
    uci = f"{start.attr('position')}{end.attr('position')}"
    move = chess.Move.from_uci(uci)
    if move in board.legal_moves:
        end.attr("piece", start.attr("piece"))
        start.attr("piece", " ")
        highlight(end)
        set_piece(start)
        set_piece(end)
        if board.is_castling(move):
            castle(move)
        board.push(move)
        
        if board.is_checkmate():
            winner = f"{'White' if board.turn == chess.BLACK else 'Black'}"
            ltk.schedule(reset_game, "checkmate - {winner} wins", 5)
            ltk.window.alert(f"Checkmate! {winner} wins!") 
        elif board.is_stalemate():
            print("Stalemate! The game is a draw.")
            ltk.schedule(reset_game, "stalemate - draw", 5)
            ltk.window.alert(f"Stalemate! draw") 
        else:
            if board.turn == chess.BLACK:
                ltk.schedule(respond, "white moved, black is next", 0.1)
    else:
        print("This is not a legal move")
   
"Ready to play Chess!" 
""".strip()


def chess():
    """
    Create a chess game.
    """
    return [
        {
            "I1": [ CHESS, green],
        },
        lambda: install_package("chess"),
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


AIRPORTS_LOAD = """
=
pysheets.load_sheet("https://query.data.world/s/7igxggw6iudndynzusfisrfcclo6rs")
""".strip()

AIRPORTS_SCATTER = """
=
A1.plot(kind='scatter', x='longitude', y='latitude')
""".strip()

AIRPORTS_MAP = """
=
import folium
map = folium.Map(location=[A1['latitude'].mean(), A1['longitude'].mean()], zoom_start=4)
for index, row in A1.iterrows():
    folium.Marker([row['latitude'], row['longitude']]).add_to(map)
map
""".strip()


def airports():
    """
    Create a US map with airport locations.
    """
    return [
        {
            "A1": [ AIRPORTS_LOAD, green],
            "F4": [ AIRPORTS_SCATTER, green],
            "B29": [ AIRPORTS_MAP, green],
        },
        lambda: install_package("folium"),
        ltk.Tutorial(
            [(
                "#A1",
                "click",
                ltk.VBox(
                    ltk.Strong("Tutorial: Airports"),
                    ltk.Text("In cell A1, we load a dataset from a URL."),
                    ltk.Text("Click inside cell A1 to see the Python code."),
                ),
            ),(
                "#F4",
                "click",
                ltk.VBox(
                    ltk.Text("In cell F4, we visualize the dataset as a scatter plot."),
                    ltk.Text("This already look surpringly like a map."),
                    ltk.Text("Click inside F4 to see the Python code."),
                ),
            ),(
                "#B29",
                "click",
                ltk.VBox(
                    ltk.Text("In cell B29, we load folium, create a map, and add markers."),
                    ltk.Text("The preview shows the map, you can resize it."),
                    ltk.Text("A folium map can be panned and you can zoom in and out."),
                    ltk.Text("Click inside B29 to see the Python code."),
                ),
            )],
        )
    ]


def install_package(name):
    """
    Install a package from PyPI.
    """
    state.UI.select(state.UI.get_cell("I1"))
    packages = ltk.find("#packages")
    if not name in packages.val():
        packages.val(name)
        ltk.window.alert(f"PySheets will now reload to install package '{name}' and then continue the tutorial...")
        ltk.find("#reload-button").click()


def clear():
    """
    Clear the current sheet.
    """
    sheet = state.UI
    start = sheet.get_cell("A1")
    end = sheet.get_cell("M30")
    selection = sheet.multi_selection
    selection.start(start)
    selection.extend(end)
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
            tutorial_button("4️⃣ Airports", airports),
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
