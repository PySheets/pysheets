"""
CopyRight (c) 2024 - Chris Laffra - All Rights Reserved.

This module provides an interface for interacting with an IndexedDB database
to store and retrieve data related to sheets.
"""

import json
import ltk
import models


class Database():
    """
    Provides an implementation of an IndexedDB database interface for
    storing and retrieving data related to sheets.
    """

    def __init__(self, name, version, db_loaded):
        self.db = None

        def init(db):
            self.db = db
            db_loaded()

        idb = ltk.window.indexedDB.open(name, version)
        idb.onerror = ltk.proxy(lambda event: ltk.window.alert(f"Cannot connect to storage: {event}"))
        idb.onsuccess = ltk.proxy(lambda event: init(event.target.result))
        idb.onupgradeneeded = ltk.proxy(lambda event: self.upgrade(event.target.result))

    def open(self, name):
        """
        Opens a transaction on the specified object store in the IndexedDB database.
        
        Args:
            name (str): The name of the object store to open.
        
        Returns:
            object: The object store transaction.
        """
        return self.db.transaction(name, "readwrite").objectStore(name)

    def upgrade(self, db):
        """
        Upgrades the IndexedDB database by creating an object store.
        
        This method is called during the initialization of the Database class
        to ensure the necessary object store exists in the database. It checks
        if the 'sheets' object store already exists, and if not, it creates
        it with the specified key path.
        """
        self.db = db
        if not self.db.objectStoreNames.contains('sheets'):
            self.db.createObjectStore('sheets', { "keyPath": 'uid' })

    def get_all(self, store, found_all):
        """
        Retrieves all objects from the specified object store in the IndexedDB database
        and calls the provided `found_all` callback with the results.
        
        Args:
            store (str): The name of the object store to retrieve objects from.
            found_all (callable): A callback function that will be called with retrieved objects.
        """
        results = []

        def extract_all_from_cursor(event):
            cursor = event.target.result
            if cursor:
                results.append(models.convert(json.loads(ltk.window.JSON.stringify(cursor.value))))
                getattr(cursor, "continue")()
            else:
                found_all(results)

        self.open(store).openCursor().onsuccess = ltk.proxy(extract_all_from_cursor)

    def save(self, store, document):
        """
        Saves a document to the specified object store in the IndexedDB database.
        
        Args:
            store (str): The name of the object store to save the document to.
            document (object): The document to be saved.
        
        Raises:
            Any exceptions that may occur during the save operation.
        """
        self.open(store).put(document)

    def load(self, store, uid, onerror, onsuccess):
        """
        Loads an object from the specified object store in the IndexedDB database.
        
        Args:
            store (str): The name of the object store to load the object from.
            uid (str): The unique identifier of the object to load.
            onerror (callable): A callback function that will be called if an error occurs during the load operation.
            onsuccess (callable): A callback function that will be called with the loaded object.
        """
        request = self.open(store).get(uid)
        def handler(event):
            if ltk.window.isUndefined(request.result):
                onerror(event)
            else:
                onsuccess(models.decode(ltk.window.JSON.stringify(request.result)))
        request.onerror = ltk.proxy(onerror)
        request.onsuccess = ltk.proxy(handler)

    def delete(self, store, uid, onsuccess, onerror):
        """
        Deletes an object from the specified object store in the IndexedDB database.
        
        Args:
            store (str): The name of the object store to delete the object from.
            uid (str): The unique identifier of the object to delete.
            onsuccess (callable): A callback function that will be called when the delete operation is successful.
            onerror (callable): A callback function that will be called when the delete operation failed.
        """
        request = self.open(store).delete(uid)
        request.onsuccess = ltk.proxy(onsuccess)
        request.onerror = ltk.proxy(onerror)


class Sheets():
    """
    Manages all sheets stored in the IndexedDB database.
    """

    def __init__(self, db_loaded):
        self.db = Database("PySheets", 3, db_loaded)
        self.deleted = []

    def list_sheets(self, found_all_sheets):
        """
        Lists all sheets stored in the IndexedDB database.
        
        Args:
            found_all_sheets (callable): A callback function that will be called with a
            list of all the sheets stored in the database.
        """
        self.db.get_all("sheets", found_all_sheets)


    def save(self, sheet: models.Sheet):
        """
        Saves the provided Sheet object to the "sheets" object store in the IndexedDB database.
        
        Args:
            sheet (models.Sheet): The Sheet object to save.
        """
        if sheet.uid in self.deleted:
            return
        self.db.save("sheets", ltk.window.JSON.parse(models.encode(sheet))) # need jsProxy for storage


    def load_sheet(self, sheet_id: str, onsuccess):
        """
        Loads a sheet from the IndexedDB database, or creates a new sheet if it doesn't exist.
        
        Args:
            sheet_id (str): The unique identifier of the sheet to load.
            onsuccess (callable): A callback function that will be called with the loaded sheet.
                If the sheet doesn't exist, a new sheet with the given `sheet_id`
                will be passed to the callback.
        """
        def found_sheet(sheet):
            onsuccess(sheet)

        def new_sheet(event): # pylint: disable=unused-argument
            onsuccess(models.Sheet(uid=sheet_id))

        self.db.load("sheets", sheet_id, new_sheet, found_sheet)


    def delete(self, sheet_id: str, oncomplete, onerror):
        """
        Deletes the sheet with the given `sheet_id` from the "sheets" object store
        in the IndexedDB database.
        
        Args:
            sheet_id (str): The unique identifier of the sheet to delete.
            oncomplete (callable): A callback function that will be called
                when the delete operation is complete.
            onerror (callable): A callback function that will be called
                when the delete operation failed.
        """
        self.db.delete("sheets", sheet_id, oncomplete, onerror)
        self.deleted.append(sheet_id)



sheets = None # pylint: disable=invalid-name


def setup(db_loaded):
    """
    Sets up storage.
    
    Args:
        db_loaded (callable): A callback function that will be called when the IndexedDB
            database has been loaded and is ready for use.
    """
    global sheets # pylint: disable=global-statement
    sheets = Sheets(db_loaded)


def load_sheet(sheet_id: str, onsuccess):
    """
    Loads a sheet from the IndexedDB database, or creates a new sheet if it doesn't exist.
    
    Args:
        sheet_id (str): The unique identifier of the sheet to load.
        onsuccess (callable): A callback function that will be called with the loaded sheet.
            If the sheet doesn't exist, a new sheet with the given `sheet_id`
            will be passed to the callback.
    """
    return sheets.load_sheet(sheet_id, onsuccess)


def save(sheet: models.Sheet):
    """
    Saves the given sheet to the IndexedDB database.
    
    Args:
        sheet (models.Sheet): The sheet to save.
    """
    sheets.save(sheet)


def delete(sheet_id, onsuccess, onerror):
    """
    Deletes the sheet with the given `sheet_id` from the "sheets" object store
    in the IndexedDB database.
    
    Args:
        sheet_id (str): The unique identifier of the sheet to delete.
        onsuccess (callable): A callback function that will be called
            when the delete operation is complete.
        onerror (callable): A callback function that will be called
            when the delete operation failed.
    """
    sheets.delete(sheet_id, onsuccess, onerror)


def list_sheets(found_all_sheets):
    """
    Lists all sheets stored in the IndexedDB database.
    
    Args:
        found_all_sheets (callable): A callback function that will be called with a list of all
            the sheet IDs that are currently stored in the IndexedDB database.
    """
    sheets.list_sheets(found_all_sheets)
