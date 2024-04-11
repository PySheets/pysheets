# PySheets

PySheets is a spreadsheet UI for Python, implemented in Python, running in the browser, using PyScript.
 

# Setup

In a terminal, run:

```
git clone https://github.com/ascend-software-company/pysheets-prod.git
git clone https://github.com/ascend-software-company/pysheets-src.git
cd pysheets-src
python3 -m pip install
```

Install VS Code, launch it, open the `pysheets-src` folder, and open a terminal.

# Running PySheets during development

To run PySheet locally and see your changes during development, run:

```
python3 main.py
```

Then open [the local preview](http://127.0.0.1:8081/). 

Note that this will use local Python source files and CSS, but all data still comes from production.

# Source folders and their meaning

Folders:

 - `static/`: Contains all the UI resources. 
 - `storage/`: Used by the server to store and load documents, uses `firestore` at the moment. 
 - `tests/`: Unit tests. See `build.sh` that runs them.
 - `node_modules/`: Used for SourceGraph completions (not used).
- `templates/`: Used to hold Jinja templates, used by `main.py`. Contains `index.html`.

Files:
 - `build.sh`, `deploy.sh`: Used to deploy to DigitalOcean.
 - `bundle.py`, `bundle.txt`: Obfuscator for Python source sent to production.
 - `main.py`, `gunicorn.py`, `procfile`: Webserver for local and production.

Configuration files:
 - `firestore.json`: Firestore key.
 - `openai.json`: OpenAI key.
 - `package.json`, `package-lock.json`: Node.js packages (not used).
 
All of the PySheet UI is written in Python, with some JS. CSS is used for styling.

# Creating a build for DigitalOcean

Run the following in a terminal:

```
. build.sh
```

This runs the unit tests, bundles (obfuscates) the source code, and copies it all to `pysheets-prod` repo

# Test the build

Stop the existin `main.py` run. Then run:

```
cd ../pysheets-prod
python3 main*.py
```

# Deploy the application to DigitalOcean

Increment the version in `app.yaml` and then run the following:

```
. deploy.sh
```

This builds and then commits the contents of `pysheets-prod` to github. 
DigitalOcean is set up to watch that repo and reloads the app.
Click on the link that is printed to see progress of the remote build and deploy.
