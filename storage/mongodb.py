from pymongo import MongoClient


MONGO_HOST = "localhost",
MONGO_PORT = 27017


mongo_config = {
    "host": MONGO_HOST,
    "port": MONGO_PORT,
    "username": "pysheets-admin",
    "password": "bmlyXWlRYX15",
}
db = MongoClient(**mongo_config)["pysheets"]
