import json
import openai
import os
import subprocess
import time

from storage.settings import admins

from storage import get_email
from storage import get_completion_budget
from storage import increment_budget
from storage import get_cached_completion
from storage import set_cached_completion


openai.api_key = json.loads(open("openai.json").read())["api_key"]
sourcegraph = json.loads(open("sourcegraph.json").read())


class CompletionBudgetException(Exception): pass

def check_completion_budget(email):
    budget = get_completion_budget(email)
    if email in admins:
        return budget
    if budget["total"] > 1000:
        raise CompletionBudgetException("You reached the lifetime maximum of 1,000 free completions.")
    seconds = time.time() - budget["last"]
    if seconds < 10:
        raise CompletionBudgetException(f"""

Too many AI completions.  You can ask for a completion again in {round(10 - seconds)}s.

You have {100 - budget["total"]} lifetime completions left.
""")
    else:
        increment_budget(email, budget)
    return budget


def complete(prompt, token):
    email = get_email(token)
    if not email:
        raise ValueError("login")
    budget = check_completion_budget(email)

    completion = get_cached_completion(prompt)
    if completion:
        completion["cached"] = True
    else:
        completion = openai_complete(prompt)
        completion["cached"] = False
        set_cached_completion(prompt, completion)
    completion["budget"] = budget
    return completion
    

def openai_complete(prompt):
    model = "davinci-002"
    model = "babbage-002"
    model="gpt-3.5-turbo-instruct"
    return openai.Completion.create(
        model=model,
        prompt=prompt,
        temperature=0,
        max_tokens=1000,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        stop=["\"\"\""]
    )["choices"][0]

class SourceGraphError(TypeError): pass

def sourcegraph_complete(prompt):
    os.putenv("SRC_ENDPOINT", "https://sourcegraph.com")
    os.putenv("SRC_ACCESS_TOKEN", sourcegraph["token"])
    command = [
        "node_modules/.bin/cody-agent",
        "experimental-cli",
        "chat",
        "-m",
        prompt,
    ]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = process.communicate()
    text = f'{out.decode("utf-8")}{err.decode("utf-8")}'
    if not "```" in text:
        raise SourceGraphError(text)
    text = re.sub(".*```", "", text)
    text = re.sub("```.*", "", text)
    return {
        "text": text
    }
