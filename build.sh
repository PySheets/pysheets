clear
echo "BUILD: Running unit tests:"
echo

export version=`grep APP_VERSION app.yaml | sed "s/.* /v/" | sed "s/\\./_/g"`
source ../env/bin/activate; 

./test.sh
if [[ $? -eq 0 ]]; then
    echo "BUILD: Continue building..."
else
    echo "BUILD: Cannot build when tests are failing..."
    exit 1
fi

echo "BUILD: Building production folder in dist"

mkdir dist
mkdir dist/static/
mkdir dist/static/ltk/
mkdir dist/templates/
mkdir dist/storage/

mkdir dist/.do
cp .do/app.yaml dist/.do

cp LICENSE dist
cp app.yaml dist
cp firestore.json dist
cp openai.json dist
cp sourcegraph.json dist
cp requirements.txt dist

cat Procfile | \
    sed "s/main/main_$version/g" \
    > dist/Procfile

cat templates/index.html | \
    sed "s/### //" | \
    sed "s/\\.py/_$version.py/g" | \
    sed "s/window.version_app = ''/window.version_app = '_$version'/g" | \
    sed "s/pysheets.css/pysheets_$version.css/g" | \
    sed "s/pysheets.js/pysheets_$version.js/g" \
    > dist/templates/index.html
cp templates/landing.html dist/templates

cp static/*.js dist/static
cp static/*.css dist/static
cp static/*.png dist/static
cp static/*.ico dist/static
cp static/ltk/* dist/static/ltk

cat static/api.py static/lsp.py static/worker.py | \
    grep -v "import api" | \
    grep -v "from api import PySheets, edit_script" \
    > dist/static/worker_$version.py

cp static/api.py dist/static/api_$version.py
cp static/constants.py dist/static/constants_$version.py
cp static/constants.py dist/static/constants.py
cp storage/__init__.py storage/identity.py storage/settings.py storage/tutorials.py dist/storage
cat storage/firestore.py | \
    sed "s/constants as constants/constants_$version as constants/" \
    > dist/storage/firestore.py
cat storage/mongodb.py | \
    sed "s/constants as constants/constants_$version as constants/" \
    > dist/storage/mongodb.py
echo "copy main.py"
cat main.py | \
    sed "s/8081/8080/" | \
    sed "s/constants import/constants_$version import/" | \
    sed "s/constants as constants/constants_$version as constants/" \
    > dist/main.py
echo "copy ai.py"
cat ai.py | \
    sed "s/constants as constants/constants_$version as constants/" \
    > dist/ai.py

rm -rf dist/storage/__pycache__
rm -rf dist/static/__pycache__
rm -rf dist/__pycache__

cd static
python3 ../bundle.py main.py  &&  mv main_min_*.py ../dist/static
cd ..
cat dist/static/main_min_0.py | \
    sed "s/version_app = 'dev'/version_app = '$version'/g" | \
    sed "s/main_min_0 /main_min_0_$version /g" | \
    sed "s/main_min_1 /main_min_1_$version /g" | \
    sed "s/main_min_2 /main_min_2_$version /g" | \
    sed "s/main_min_3 /main_min_3_$version /g" | \
    sed "s/pysheets.css/pysheets_$version.css/g" \
    > dist/static/main_min_0_$version.py
cat dist/static/main_min_1.py | \
    sed "s/version_app = 'dev'/version_app = '$version'/g" | \
    sed "s/main_min_0 /main_min_0_$version /g" | \
    sed "s/main_min_1 /main_min_1_$version /g" | \
    sed "s/main_min_2 /main_min_2_$version /g" | \
    sed "s/main_min_3 /main_min_3_$version /g" | \
    sed "s/pysheets.css/pysheets_$version.css/g" \
    > dist/static/main_min_1_$version.py
cat dist/static/main_min_2.py | \
    sed "s/version_app = 'dev'/version_app = '$version'/g" | \
    sed "s/main_min_0 /main_min_0_$version /g" | \
    sed "s/main_min_1 /main_min_1_$version /g" | \
    sed "s/main_min_2 /main_min_2_$version /g" | \
    sed "s/main_min_3 /main_min_3_$version /g" | \
    sed "s/pysheets.css/pysheets_$version.css/g" \
    > dist/static/main_min_2_$version.py
cat dist/static/main_min_3.py | \
    sed "s/version_app = 'dev'/version_app = '$version'/g" | \
    sed "s/main_min_0 /main_min_0_$version /g" | \
    sed "s/main_min_1 /main_min_1_$version /g" | \
    sed "s/main_min_2 /main_min_2_$version /g" | \
    sed "s/main_min_3 /main_min_3_$version /g" | \
    sed "s/pysheets.css/pysheets_$version.css/g" \
    > dist/static/main_$version.py
rm dist/static/main_min_0.py
rm dist/static/main_min_1.py
rm dist/static/main_min_2.py
rm dist/static/main_min_3.py
echo "BUILD: After bundling $version:"
wc dist/static/main_*.py
mv dist/static/pysheets.css dist/static/pysheets_$version.css
mv dist/static/pysheets.js dist/static/pysheets_$version.js

rm -rf ../pysheets-prod/* ../pysheets-prod/.do
mv dist/* dist/.do ../pysheets-prod
rm -rf dist

rm `find . -name "*.pyc" -print`

echo "BUILD: All code has been bundled and copied to pysheets-prod."

if [[ "$1" != "norun" ]]; then
    echo "run"
    cd ../pysheets-prod
    python3 main*.py &
    sleep 3
    open http://127.0.0.1:8080
    fg %1
fi