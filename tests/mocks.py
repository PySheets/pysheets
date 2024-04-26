import sys
import traceback
import os

sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "static"))

import ltk
import time

ltk.get_time = lambda: time.time()
ltk.post = lambda url, data, done: "OK"

import pyscript

pyscript.window.parseFloat = lambda s: 0

import state
state.mobile = lambda: True
state.show_worker_status = lambda: True

def schedule(function, key, duration=None):
    try:
        function()
    except Exception as e:
        print("Mocks: ignore")
        traceback.print_exc()
ltk.schedule = schedule