cp -r src/static/lib ../pysheets-prod/static
cp -r src/static/ltk ../pysheets-prod/static
cp -r src/static/views ../pysheets-prod/static
cp -r src/static/icons/format* ../pysheets-prod/static/icons
cp src/static/*.py ../pysheets-prod/static
cp src/static/*.png ../pysheets-prod/static
cp src/static/*.ico ../pysheets-prod/static
cp src/static/*.css ../pysheets-prod/static
cp src/static/*.js ../pysheets-prod/static
cp -r src/templates ../pysheets-prod
cp -r src/*.py ../pysheets-prod
cp -r requirements.txt ../pysheets-prod
cp -r LICENSE ../pysheets-prod
cp -r Procfile ../pysheets-prod


rm dist/*.gz dist/*.whl
python3 -m build && twine check dist/* && twine upload dist/*
rm -rf src/pysheets_app.egg-info
rm dist/*.gz dist/*.whl
