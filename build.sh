clear
echo "Building production folder in dist:"
echo

export version=`grep APP_VERSION app.yaml | sed "s/.* /v/" | sed "s/\\./_/g"`

mkdir dist
mkdir dist/static/
mkdir dist/templates/
mkdir dist/storage_$version/

mkdir dist/.do
cp .do/app.yaml dist/.do

cp LICENSE dist
cp app.yaml dist
cp config.json dist
cp requirements.txt dist

cat Procfile | \
    sed "s/main/main_$version/g" \
    > dist/Procfile

cat templates/index.html | \
    sed "s/### //" | \
    sed "s/\\.py/_$version.py/g" | \
    sed "s/window.app_version = ''/window.app_version = '_$version'/g" | \
    sed "s/pysheets.css/pysheets_$version.css/g" | \
    sed "s/pysheets.js/pysheets_$version.js/g" \
    > dist/templates/index.html

cp static/*.js dist/static
cp static/*.css dist/static
cp static/*.png dist/static
cp static/*.ico dist/static
cp static/worker.py dist/static/worker_$version.py

cp static/constants.py dist/static/constants_$version.py
cp storage/__init__.py dist/storage_$version
cat storage/firestore.py | \
    sed "s/constants as constants/constants_$version as constants/" | \
    sed "s/constants import/constants_$version import/" | \
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
    sed "s/main_min_0 /main_min_0_$version /g" | \
    sed "s/main_min_1 /main_min_1_$version /g" | \
    sed "s/main_min_2 /main_min_2_$version /g" | \
    sed "s/pysheets.css/pysheets_$version.css/g" | \
    > dist/static/main_min_0_$version.py
cat dist/static/main_min_1.py | \
    sed "s/main_min_0 /main_min_0_$version /g" | \
    sed "s/main_min_1 /main_min_1_$version /g" | \
    sed "s/main_min_2 /main_min_2_$version /g" | \
    sed "s/pysheets.css/pysheets_$version.css/g" | \
    > dist/static/main_min_1_$version.py
cat dist/static/main_min_2.py | \
    sed "s/main_min_0 /main_min_0_$version /g" | \
    sed "s/main_min_1 /main_min_1_$version /g" | \
    sed "s/main_min_2 /main_min_2_$version /g" | \
    sed "s/pysheets.css/pysheets_$version.css/g" | \
    > dist/static/main_$version.py
rm dist/static/main_min_0.py
rm dist/static/main_min_1.py
rm dist/static/main_min_2.py
mv dist/static/pysheets.css dist/static/pysheets_$version.css
mv dist/static/pysheets.js dist/static/pysheets_$version.js

echo "Original size:"
wc static/constants.py static/pysheets.py static/dag.py static/editor.py static/main.py static/menu.py static/state.py 

echo "Compressed size for $version:"
wc dist/static/main*.py

rm -rf ../pysheets-prod/* ../pysheets-prod/.do
mv dist/* dist/.do ../pysheets-prod
rm -rf dist