import constants
import ltk
import state
import menu


def list_sheets():
    state.clear()
    ltk.find("#main").append(
        ltk.Button("New Sheet", ltk.proxy(lambda event: None)).addClass("new-button temporary"),
        ltk.Card(ltk.Div().css("width", 204).css("height", 188)).addClass("document-card temporary"),
        ltk.Card(ltk.Div().css("width", 204).css("height", 188)).addClass("document-card temporary"),
        ltk.Card(ltk.Div().css("width", 204).css("height", 188)).addClass("document-card temporary"),
        ltk.Card(ltk.Div().css("width", 204).css("height", 188)).addClass("document-card temporary"),
        ltk.Card(ltk.Div().css("width", 204).css("height", 188)).addClass("document-card temporary"),
    )
    ltk.find(".temporary").css("opacity", 0).animate(ltk.to_js({ "opacity": 1 }), 2000)
    ltk.get("/list", ltk.proxy(show_document_list))


def show_document_list(documents):
    state.clear()
    ltk.find("#main").empty()
    if "error" in documents:
        return print(f"Error: Cannot list documents: {documents['error']}")

    def create_card(uid, index, runtime, packages, *items):
        def select_doc(event):
            if event.keyCode == 13:
                load_doc_with_packages(event, uid, packages)

        return (
            ltk.Card(*items)
                .on("click", ltk.proxy(lambda event=None: load_doc_with_packages(event, uid, runtime, packages)))
                .on("keydown", ltk.proxy(select_doc))
                .attr("tabindex", 1000 + index)
                .addClass("document-card")
        )

    sorted_documents = sorted(documents[constants.DATA_KEY_IDS], key=lambda doc: doc[1])
    
    for index, (uid, name, screenshot, runtime, packages) in enumerate(sorted_documents):
        ltk.window.console.orig_log(index, uid, name)

    ltk.find("#main").append(
        ltk.Container(
            *[
                create_card(
                    uid,
                    index,
                    runtime,
                    packages,
                    ltk.VBox(
                        ltk.Image(screenshot, "/screenshot.png"),
                        ltk.Text(name),
                    ),
                )
                for index, (uid, name, screenshot, runtime, packages) in enumerate(
                    sorted_documents
                )
            ]
        ).prepend(
            ltk.Button("New Sheet", ltk.proxy(lambda event: menu.new_sheet())).addClass(
                "new-button"
            )
        ).css("overflow", "auto").css("height", "100%")
    )
    ltk.find(".document-card").eq(0).focus()
    ltk.find("#menu").empty()
    state.show_message("Select a sheet below or create a new one...")


def load_doc_with_packages(event, uid, runtime, packages):
    url = f"/?{constants.DATA_KEY_UID}={uid}&{constants.DATA_KEY_RUNTIME}={runtime}"
    if packages:
        url += f"&{constants.DATA_KEY_PACKAGES}={packages}"
    ltk.window.location = url