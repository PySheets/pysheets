clear
echo "TEST: Running unit tests:"
echo

export version=`grep APP_VERSION app.yaml | sed "s/.* /v/" | sed "s/\\./_/g"`
pip install pandas
export PYTHONPATH=./static:./tests
python3 -m unittest discover
if [[ $? -eq 0 ]]; then
    echo "TEST: Unit tests succeeded"
else
    echo "TEST: Unit tests failed"
    exit 1
fi