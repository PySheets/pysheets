clear
echo "Running unit tests:"
echo

export version=`grep APP_VERSION app.yaml | sed "s/.* /v/" | sed "s/\\./_/g"`

export PYTHONPATH=./static:./tests
python3 -m unittest discover
if [[ $? -eq 0 ]]; then
    echo "Unit tests succeeded"
else
    echo "Unit tests failed"
    exit 1
fi

echo "Update ltk"
curl "https://raw.githubusercontent.com/pyscript/ltk/main/ltk/ltk.js" > static/ltk/ltk.js
curl "https://raw.githubusercontent.com/pyscript/ltk/main/ltk/ltk.css" > static/ltk/ltk.css

echo "Building production folder in dist"

mkdir dist
mkdir dist/static/
mkdir dist/static/ltk/
mkdir dist/templates/
mkdir dist/storage_$version/

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
cp storage/__init__.py dist/storage_$version
cat storage/firestore.py | \
    sed "s/constants as constants/constants_$version as constants/" | \
    sed "s/constants import/constants_$version import/" \
    > dist/storage_$version/firestore.py
cat main.py | \
    sed "s/8081/8080/" | \
    sed "s/constants import/constants_$version import/" | \
    sed "s/constants as constants/constants_$version as constants/" | \
    sed "s/import storage/import storage_$version as storage/" \
    > dist/main_$version.py

rm -rf dist/storage/__pycache__
rm -rf dist/static/__pycache__

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
echo "After bundling $version:"
wc dist/static/main_min_0_$version.py dist/static/main_min_1_$version.py dist/static/main_$version.py
rm dist/static/main_min_0.py
rm dist/static/main_min_1.py
rm dist/static/main_min_2.py
rm dist/static/main_min_3.py
mv dist/static/pysheets.css dist/static/pysheets_$version.css
mv dist/static/pysheets.js dist/static/pysheets_$version.js

rm -rf ../pysheets-prod/* ../pysheets-prod/.do
mv dist/* dist/.do ../pysheets-prod
rm -rf dist

rm `find . -name "*.pyc" -print`