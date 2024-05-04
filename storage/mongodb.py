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


if __name__ == "__main__":
    result =db.user.insert_one({
        "name": "Chris",
        "email": "laffra@gmail.com",
    })
    if not result.inserted_id:
        print("Failed to insert")
    print("Users:", list(db.user.find({})))
    print("DB:", db.user)
    for user in db.user.find({}):
        db.user.delete_one({"_id": user["_id"] })
    print("Users:", list(db.user.find({})))