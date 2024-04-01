visualize = """
Given the following dataframe, how do I create a matplolib figure from it. 
I want you to return the figure, not call plt.show()

     Category Revenue Profit
0 Bikes 300 130
1 Air 50 25
2 Clothing 150 160
3 Bikes 300 100
4 Clothing 200 120
"""

sheet = {
    "A1": "Category", "B1": "Revenue", "C1": "Profit",
    "A2": "Bikes", "B2": 300, "C2": 130,
    "A3": "Air", "B3": 50, "C3": 25,
    "A4": "Clothing", "B4": 150, "C4": 160,
    "A5": "Bikes", "B5": 300, "C5": 100,
    "A6": "Clothing", "B6": 200, "C6": 120,
}

import json

analyze = f"""
Given the following spreadsheet, how do I analyze it with pandas?
{json.dumps(sheet, indent=4)}
"""


print(analyze)