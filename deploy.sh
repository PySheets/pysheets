cp -r src/static/lib ../pysheets-prod/static
cp -r src/static/views ../pysheets-prod/static
cp -r src/static/icons ../pysheets-prod/static
cp src/static/*.py ../pysheets-prod/static
cp src/static/*.png ../pysheets-prod/static
cp src/static/*.ico ../pysheets-prod/static
cp src/static/*.css ../pysheets-prod/static
cp -r src/templates ../pysheets-prod
cp -r src/*.py ../pysheets-prod
cp requirements.txt ../pysheets-prod
cp LICENSE ../pysheets-prod
cp Procfile ../pysheets-prod
mkdir -p ../pysheets-prod/static/css


rm dist/*.gz dist/*.whl
python3 -m build && twine check dist/* && twine upload dist/*
rm -rf src/pysheets_app.egg-info
rm dist/*.gz dist/*.whl
