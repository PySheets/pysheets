# PySheets

[PySheets](https://pysheets.app/about) is a spreadsheet UI for Python, implemented in Python, running logic and saving data in the browser, using PyScript and IndexedDB.

# Licensing

Ahead In The Cloud Computing makes PySheets available under both the GPLv3 and a
[commercial license](https://buy.stripe.com/00g1684SS2BZ9Es7st).

If you want to self-host PySheets for personal projects or evaluation purposes, the GPLv3 licence applies. 
This licence allows free use of the software, but also implies that if you make any modifications or
extensions to PySheets, you need to share those changes yourself, under the same license. 

Self-hosting installations of PySheets that want to use the software but do not want to be subject to the GPL and
do not want to release the source code for their proprietary extensions and addons should purchase a
[commercial license](https://buy.stripe.com/00g1684SS2BZ9Es7st)
from Ahead In The Cloud Computing. Purchasing a commercial license means that the GPL does not apply, and a commercial 
license includes the assurances that distributors typically find in commercial distribution agreements.

When using PySheets for any commercial purpose, we recommend a [commercial license](https://buy.stripe.com/00g1684SS2BZ9Es7st).
Commercial use includes incorporating PySheets into a commercial product, 
using PySheets in any commercial service, 
leveraging PySheets to create algorithms or workflows that aim to produce a profit,
using PySheets in a commercial, financial institution such as a bank or hedge fund,
or using PySheets to produce other artefacts for commercial purposes.



  
# Installation

To install PySheets on your local machine, run:

```
pip install pysheets-app
```

Do not install `pysheets`, this is an unrelated dormant project.

# Using

To run PySheets locally on your own machine, storing all data in the browser, without any server, run:

```
pysheets
```

Then open http://localhost:8081/ in your browser and create a new sheet.

Some basic things to try:
 - Change the sheet name.
 - Add literal values such as 4 in A1 and 5 in A2.
 - Add an expression in cell D3, such as "=A1 + A2", and see it evaluate to 9.

Produce an AI-driven data-science workflow without writing any Pandas or Matplotlib code:
 - At cells A1 through C4 enter a table looking like this:
    ```
    Country	Import	Export
    Canada	  34      10
    USA       54      22
    Germany   11      40
    ```
 - Select an empty cell, such as F5
 - Click the "⭐ A1" button in the AI prompt section to turn the table into a dataframe
 - Select another empty cell, such as E9
 - Click the "⭐ F5" button to visualize the data
 - You now have a Pandas dataframe and matplotlib Figure, with just a few clicks 🤯. 

Import data from the web:
 - Click the "load from web" button in the AI prompt section
 - Turn it into a dataframe using the AI buttons
 - Visualize it. Change the prompt to change colors or image size.


# Find out more

Information sources for PySheets:
 - [pysheets.app/about](https://pysheets.app/about)
 - [Discord server](https://discord.com/invite/4wy23872th)
 - [Feedback form](https://docs.google.com/forms/d/e/1FAIpQLScmeDuDr5fxKYhe04Jo-pNS73P4VF2m-i8X8EC9rfKl-jT84A/viewform)