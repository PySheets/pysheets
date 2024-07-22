import json
import ltk
import models
import state

database = None


def setup(indexed_db):
    global database
    database = indexed_db


def list_sheets(handler):
    results = []

    def handle_sheet(event):
      cursor = event.target.result
      if cursor:
            results.append(models.convert(json.loads(ltk.window.JSON.stringify(cursor.value))))
            getattr(cursor, "continue")()
      else:
            handler(results)

    transaction = database.transaction("sheets", "readwrite")
    object_store = transaction.objectStore("sheets")
    object_store.openCursor().onsuccess = ltk.proxy(handle_sheet)


def save(sheet: models.Sheet):
    transaction = database.transaction("sheets", "readwrite")
    object_store = transaction.objectStore("sheets")
    data = ltk.window.JSON.parse(models.encode(sheet))
    try:
        object_store.put(data)
    except:
        object_store.add(data)


def load(uid: str, handler):
    transaction = database.transaction("sheets")
    object_store = transaction.objectStore("sheets")
    request = object_store.get(uid)
    def get_sheet():
        try:
            return models.decode(ltk.window.JSON.stringify(request.result))
        except:
            return models.Sheet(uid=uid)
    request.onerror = ltk.proxy(lambda event: ltk.window.alert(f"Error loading sheet {uid}"))
    request.onsuccess = ltk.proxy(lambda event: handler(get_sheet()))

