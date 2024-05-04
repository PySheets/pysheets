echo
echo "----------------------------------------------------------------------------"
echo "Installing Python packages"
echo "----------------------------------------------------------------------------"
pip install -r requirements.txt

echo
echo "----------------------------------------------------------------------------"
echo "Installing Mongo DB"
echo "https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-os-x/"
echo "----------------------------------------------------------------------------"
xcode-select --install
brew tap mongodb/brew
brew update
brew install mongodb-community@7.0

echo
echo "----------------------------------------------------------------------------"
echo "Running Mongo DB"
echo "----------------------------------------------------------------------------"
mkdir ~/pysheets
mongod --port 27017 --dbpath ~/pysheets &
sleep 5
mongosh --port 27017 << EOF
use admin
db.createUser(
  {
    user: "pysheets-admin",
    pwd: "bmlyXWlRYX15",
    roles: [ { role: "userAdminAnyDatabase", db: "admin" }, 
             { role: "dbAdminAnyDatabase", db: "admin" }, 
             { role: "readWriteAnyDatabase", db: "admin" } ]
  }
)
EOF
fg %1