clear
echo "Running unit tests:"
echo

export version=`grep APP_VERSION app.yaml | sed "s/.* /v/" | sed "s/\\./_/g"`

export PYTHONPATH=./static:./tests
python3 -m unittest tests/test_lsp.py