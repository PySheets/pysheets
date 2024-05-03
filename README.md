# PySheets

PySheets is a spreadsheet UI for Python, implemented in Python, running in the browser, using PyScript.
 

# Setup VS Code

First install VS Code, Python3, and the Python extension for VS Code.
Follow [this tutorial](https://code.visualstudio.com/docs/python/python-tutorial) for that. As part of the instructions, you will install a Python v3 runtime.

# Setup Venv

To set up local virtual environment for PySheets, open a terminal and run:

```
mkdir pysheets
cd pysheets
python3 -m pip install virtualenv
python3 -m venv env
source env/bin/activate
```

You now have a `pysheets` folder containing a `venv` folder to store all
the Python dependencies and runtimes that PySheets needs.

# Setup PySheets

PySheets is stored in github. To make a local copy, run:

```
git clone https://github.com/ascend-software-company/pysheets-prod.git
git clone https://github.com/ascend-software-company/pysheets-src.git
cd pysheets-src
pip install -r requirements.txt
cd ../..
ls
```

You should now have the following folder structure:
  - `pysheets`
    - `env`
    - `pysheets-prod`
    - `pysheets-src`

# Accessing PySheets from VS Code

To navigate to the source of PySheets, and make changes to it:
  - Launch VS Code
  - Open the `pysheets/pysheets-src` folder
  - Open a terminal inside VS Code

# Running PySheets during development

To run PySheet locally from VS Code, it its terminal run:

```
source ../env/bin/activate; python3 main.py
```

Then open [the local preview](http://127.0.0.1:8081/). Note that in VS Code, you can `Cmd+Click` any URL or file name that is printed in the terminal to open it.

Note that this will use local Python source files and CSS, but all data still comes from production.

# Making changes and committing them

First add PR request support to VS Code:
 - Install the VS Code extension: [Github Pull Requests Extension](https://marketplace.visualstudio.com/items?itemName=GitHub.vscode-pull-request-github)

From now on, do all your work in a new branch:
 - Create a new branch using the "..." menu in the "Source Control" viewlet. Use a short name that is meaningful to the task.
 - Commit your changes (to the new branch).
 - Publish/Synch your changes to the branch, so that others can see it.

Branches are the mechanism used by Git to allow people to work in parallel and merge their work later.

Once you work is ready for a review, create a new PR request:
 - Select the "Github Pull Requests" viewlet and click the "Create Pull Request" button in the hover bar.
 - Change the "MERGE" branch to the branch you did your work in.
 - Choose an assignee and reviewer(s) for the work in the hover bar.
 - Finish the PR description and send it.

Both the assignee and reviewer now see the changes in their Pull Request viewlet.
  

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

Open a new VS Code window and open `pysheets-prod`. You will not make any changes in the code, but 
having a separate VS Code window will be handy to see the output and look at the 
obfuscated source files. Then run the production version of the local PySheets:

```
source ../env/bin/activate
python3 main*.py
```


# Deploy the application to DigitalOcean

After you ran `build.sh` and tested the obfuscated version of PySheets locally, you can 
now release to DigitalOcean. The release process looks like this:

 - Local development and testing (this is always safe):
   - Make changes to source files in `pysheets-src`
   - Test changes to source files in `pysheets-src`
 - Checking the production version locally (this is still safe):
   - Run `build.sh`
   - Test production changes in `pysheets-prod`
 - Run `deploy.sh` (this can and will directly impact production)
    - This increments the version of the source (to clear browser caches)
    - This commits all changes to github
    - A github action triggers DigitalOcean to deploy:
        - Create a new deployment server
        - Clone the `pysheets-prod` repo 
        - Run `pip install -r requirements.txt`
        - Run `procfile` to run `gunicorn`
        - Switch the old server to the new server at [pysheets.app](https://pysheets.app)

The deploy script will print link to DigitalOcean's app dashboard.
Follow that link to see progress of the remote build and deploy status.
If the remote install fails for some reason, production will not be impacted.
