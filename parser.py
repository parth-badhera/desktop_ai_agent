import re
import json
import time
import memory
from brain import think
from tools import open_chrome, open_website, click, type_into, chat, ask_user, get_browser_state

def extract_json(text):
    match = re.search(r"\{.*\}", text, re.S)
    if match:
        try:
            return json.loads(match.group())
        except:
            pass
    return None

def execute(command):
    # Every time the user enters a NEW command, we should clear the 'stale' state
    session = memory.load_memory()
    pending_goal = session.get("pending_goal")
    
    # If the current command is very short or a number, it's likely a follow-up answer
    full_goal = command
    if pending_goal and (len(command) < 10 or command.isdigit()):
        full_goal = f"{pending_goal} (User Answer: {command})"
    else:
        # Fresh command: Clear everything to prevent hallucinations leaking
        memory.clear_memory()
        session = {"pending_goal": command}
        memory.save_memory(session)

    print(f"Goal: {full_goal}")
    
    max_steps = 10
    step = 0
    current_state = get_browser_state()
    if current_state is None: current_state = {}
    current_state.update({k: v for k, v in session.items() if k != "pending_goal"})
    
    last_action = None
    last_error = None
    action_failure_count = {}
    thought_history = []

    while step < max_steps:
        step += 1
        
        # Brain now handles its own retries/formatting internally
        decision = think(full_goal, current_state, last_action, pending_goal, last_error)
        
        thought = decision.get("thought", "Thinking...")
        action = decision.get("action")
        params = decision.get("params", {})
        
        # Loop prevention: check if we are repeating thoughts too often
        if thought in thought_history[-2:]:
            print(f"Loop detected: Repeating thought '{thought}'")
            action = "chat"
            params = {"message": "I seem to be repeating myself. I need you to clarify or try a different approach."}
        else:
            thought_history.append(thought)
        
        current_action_key = f"{action}({params})"
        last_action = current_action_key
        print(f"\n[Step {step}] {thought}")
        
        try:
            if action == "done":
                print("AI signed off. Task complete!")
                memory.clear_memory()
                break

            if action == "open_chrome" or action == "switch_profile":
                open_chrome(params.get("profile"))
                # Give internal Chrome sync extra time to stabilize
                time.sleep(2.5) 
                
                # IF this was a simple 'open chrome' goal, we are done!
                # But if the goal also mentions "search", "play", or "youtube", keep going.
                is_only_open = "open chrome" in full_goal.lower() and not any(word in full_goal.lower() for word in ["play", "search", "youtube", "amazon", "google"])
                if is_only_open and step == 1:
                    print("Chrome launched. Efficiency achieved.")
                    memory.clear_memory()
                    break
            
            elif action == "youtube_search":
                from tools import youtube_search
                youtube_search(params.get("query"))
            
            elif action == "google_search":
                from tools import google_search
                google_search(params.get("query"))
                
            elif action == "click_video":
                from tools import click_video
                click_video(params.get("title"))

            elif action == "open_website":
                open_website(params.get("url"))

            elif action == "click":
                click(params.get("target") or params.get("selector"))

            elif action == "type_into":
                type_into(params.get("selector"), params.get("text"))
            
            elif action == "chat":
                chat(params.get("message") or "Ready.")
            
            elif action == "ask_user":
                ask_user(params.get("question"))
                break

            # ... other tools as needed ...
            
            last_error = None
            action_failure_count[current_action_key] = 0

        except Exception as e:
            print(f"Tool execution warning: {e}")
            action_failure_count[current_action_key] = action_failure_count.get(current_action_key, 0) + 1
            if action_failure_count[current_action_key] >= 2:
                last_error = f"CRITICAL: {current_action_key} failed twice. Try a different approach."
            else:
                last_error = str(e)

        # DETERMINISTIC PACING: Wait for browser to settle after any action
        time.sleep(1.5)
        current_state = get_browser_state() or {}
        
    if step >= max_steps:
        print("Reached max steps. Stopping.")
