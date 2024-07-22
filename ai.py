import json
import openai
import os
import subprocess



openai.api_key = json.loads(open(os.path.expanduser("~/openai.json")).read())["api_key"]
sourcegraph = json.loads(open(os.path.expanduser("~/sourcegraph.json")).read())


def complete(prompt):
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
