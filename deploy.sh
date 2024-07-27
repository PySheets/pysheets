rm dist/*.gz dist/*.whl
python3 -m build && twine check dist/* && twine upload dist/*
rm -rf pysheets_app.egg-info