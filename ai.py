import json
import openai
import os

MISSING_KEY = "\n".join([
    "# We could not find an OpenAI key. Please create a file containing:",
    "",
    "{",
    "    \"api_key\": \"YOUR_SECRET_KEY\"",
    "}",
    "",
    "# Place the file next to 'main.py' and try an OpenAI completion again.",
])


def load_key():
    try:
        dir = os.path.dirname(__file__)

        openai.api_key = json.loads(open(os.path.join(dir, "openai.json")).read())["api_key"]
    except Exception as e:
        print(e)
        pass

metaprompt = '''

'''


def complete(prompt):
    model="gpt-3.5-turbo-instruct"
    load_key()
    if not openai.api_key:
        return {
            "text": MISSING_KEY,
        }
    return openai.Completion.create(
        model=model,
        prompt=f"{metaprompt}\n{prompt}.",
        temperature=0,
        max_tokens=1000,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        stop=["\"\"\""]
    )["choices"][0]
