version = "Sqlite"

if version == "MongoDB":
    from storage.mongodb import *
elif version == "Firestore":
    from storage.firestore import *
elif version == "Sqlite":
    from storage.sqlite import *
else:
    from storage.filesystem import *