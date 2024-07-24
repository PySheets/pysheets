import json
import ltk
import models
    

database = None


class Database():
    def __init__(self, name="PySheets", version=2, db_loaded=None):
        self.db = None
        idb = ltk.window.indexedDB.open(name, version)
        idb.onerror = ltk.proxy(lambda event: ltk.window.alert(f"Cannot connect to storage: {event}"))
        idb.onsuccess = ltk.proxy(lambda event: self.init(event.target.result, db_loaded))
        idb.onupgradeneeded = ltk.proxy(lambda event: self.upgrade(event.target.result))

    def init(self, db, db_loaded):
        self.db = db
        db_loaded()

    def open(self, name):
        return self.db.transaction(name, "readwrite").objectStore(name)
        
    def upgrade(self, db):
        self.db = db
        if not self.db.objectStoreNames.contains('sheets'):
            self.db.createObjectStore('sheets', { "keyPath": 'uid' })
    
    def get_all(self, store, found_all):
        results = []
        
        def extract_all_from_cursor(event):
            cursor = event.target.result
            if cursor:
                results.append(models.convert(json.loads(ltk.window.JSON.stringify(cursor.value))))
                getattr(cursor, "continue")()
            else:
                found_all(results)

        self.open(store).openCursor().onsuccess = ltk.proxy(extract_all_from_cursor)
    
    def save(self, store, object, mode="readwrite"):
        try:
            self.open(store).put(object)
        except:
            self.open(store).add(object)
    
    def load(self, store, uid, onerror, onsuccess):
        request = self.open(store).get(uid)
        def handler(event):
            if ltk.window.isUndefined(request.result):
                onerror(event)
            else:
                onsuccess(models.decode(ltk.window.JSON.stringify(request.result)))
        request.onerror = ltk.proxy(onerror)
        request.onsuccess = ltk.proxy(handler)


def setup(db_loaded):
    global database
    database = Database(db_loaded=db_loaded)



def list_sheets(found_all_sheets):
    database.get_all("sheets", found_all_sheets)


def save(sheet: models.Sheet):
    database.save("sheets", ltk.window.JSON.parse(models.encode(sheet))) # need jsProxy for storage


def load(sheet_id: str, onsuccess):
    def found_sheet(sheet):
        onsuccess(sheet)
    def new_sheet(event):
        onsuccess(models.Sheet(uid=sheet_id))
    database.load("sheets", sheet_id, new_sheet, found_sheet)


