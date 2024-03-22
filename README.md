# PySheets

This is a spreadsheet, implemented in Python, completely running in the browser, using PyScript.

This project uses PyScript to display its UI in a browser.  


# Running PySheets during development

To test changes during development, run:

```
python3 main.py
```

Then open [the local preview](http://127.0.0.1:8081/).


# Deploy a new version to AppEngine

Run the following in a terminal:

```
source deploy.sh
```

To test the build before doing the actual deploy, run the following:

```
cd dist
python3 main.py
```
