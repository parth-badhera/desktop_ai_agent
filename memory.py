import json
import os

MEMORY_PATH = os.path.join(os.path.dirname(__file__), "session_memory.json")

def save_memory(data):
    with open(MEMORY_PATH, "w") as f:
        json.dump(data, f)

def load_memory():
    if not os.path.exists(MEMORY_PATH):
        return {}
    try:
        with open(MEMORY_PATH, "r") as f:
            return json.load(f)
    except:
        return {}

def clear_memory():
    if os.path.exists(MEMORY_PATH):
        os.remove(MEMORY_PATH)
