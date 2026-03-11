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

def add_action_to_history(action):
    session = load_memory()
    history = session.get("action_history", [])
    history.append(action)
    session["action_history"] = history[-10:]
    save_memory(session)

def get_action_history():
    session = load_memory()
    return session.get("action_history", [])

def save_plan(plan):
    session = load_memory()
    session["plan"] = plan
    session["current_step_index"] = 0
    save_memory(session)

def get_plan():
    session = load_memory()
    return session.get("plan", []), session.get("current_step_index", 0)

def update_step_status(index, status):
    session = load_memory()
    plan = session.get("plan", [])
    if 0 <= index < len(plan):
        plan[index]["status"] = status
        session["plan"] = plan
        save_memory(session)

def set_current_step(index):
    session = load_memory()
    session["current_step_index"] = index
    save_memory(session)
