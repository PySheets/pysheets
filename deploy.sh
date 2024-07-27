rm dist/*.gz dist/*.whl
python3 -m build && twine check dist/* && twine upload dist/*
rm -rf src/pysheets_app.egg-info
rm dist/*.gz dist/*.whl