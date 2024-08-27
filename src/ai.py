"""
CopyRight (c) 2024 - Chris Laffra - All Rights Reserved.

Wrapper for OpenAI's GPT API.
"""

import json
import os
import requests

import openai


MISSING_KEY = "\n".join([
    "# We could not find an OpenAI key. Please create a file named '~/openai.json' containing:",
    "",
    "{",
    "    \"api_key\": \"YOUR_SECRET_KEY\"",
    "}",
    "",
    "# Place the file next to 'main.py' and try an OpenAI completion again.",
])


def load_key():
    """
    Loads the OpenAI API key from a JSON file located in the home directory.
    
    If the API key file is not found or there is an error reading it, the function
    will silently fail and the `openai.api_key` will remain unset.
    """
    try:
        folder = os.path.dirname(__file__)
        path = os.path.join(folder, os.path.expanduser("~/openai.json"))
        with open(path, encoding="utf-8") as fd:
            openai.api_key = json.loads(fd.read())["api_key"]
    except Exception as e: # pylint: disable=broad-except
        print(e)


METAPROMPT = '''
You are an expert Python Data Scientist. You know about Pandas, Matplotlib, Numpy, etc.
When your answer is a list of things, return a Python list.
when your answer looks like a table, return a Python dictionary.
Generate python code to be used in a Jupyter Notebook cell.
On the last line, just give the expression, do not call print(expression).
Replace calls to 'figure.show()' with 'figure'.
Do not generate explanations, but just show the Python code.
'''


def complete(prompt):
    """
    Generates a code completion using the currently selected language model.
    
    Args:
        prompt (str): The input prompt to generate the completion from.
    
    Returns:
        dict: A dictionary containing the generated text completion.
    """
    return complete_with_openai(prompt)


def complete_with_ollama(prompt): # pylint: disable=unused-argument
    """
    Generates a code completion using Ollama with the llama3 language model.
    
    Args:
        prompt (str): The input prompt to generate the completion from.
    
    Returns:
        dict: A dictionary containing the generated text completion.
    """
    response = requests.post("http://127.0.0.1:11434/api/generate", json={
        "model": "llama3.1",
        "prompt": "What is the meaning of life?",
    }, timeout=10)
    response.raise_for_status()
    for line in response.iter_lines():
        body = json.loads(line)
        print("########", body)
    return {
        "status": "OK",
        "text": response.text,
    }


def complete_with_openai(prompt):
    """
    Generates a code completion using the OpenAI GPT-3.5 language model.
    
    Args:
        prompt (str): The input prompt to generate the completion from.
    
    Returns:
        dict: A dictionary containing the generated text completion.
    """
    model="gpt-3.5-turbo-instruct"
    load_key()
    if not openai.api_key:
        return {
            "text": MISSING_KEY,
        }
    return openai.Completion.create(
        model=model,
        prompt=f"{METAPROMPT}\n{prompt}.",
        temperature=0,
        max_tokens=1000,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        stop=["\"\"\""]
    )["choices"][0]
