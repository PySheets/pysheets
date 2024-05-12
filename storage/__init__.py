import os


if False and os.path.exists("firestore.json"):
    from storage.firestore import *
    version = "Firestore"
else:
    from storage.mongodb import *
    version = "MongoDB"
