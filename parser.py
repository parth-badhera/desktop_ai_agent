import json
import time
import memory

from brain import think, plan_goal
from tools import (
    open_chrome, open_website, click, type_into,
    chat, ask_user, get_browser_state,
    youtube_search_tool, google_search_tool,
    click_video_tool, amazon_search_tool,
    add_to_cart_tool, select_item
)


# -----------------------------
# Goal Preparation
# -----------------------------

def prepare_goal(command):
    session = memory.load_memory()
    pending_goal = session.get("pending_goal")

    if pending_goal and (len(command) < 15 or command.isdigit()):
        full_goal = f"GOAL: {pending_goal} | USER SELECTION: {command}"
    else:
        memory.clear_memory()
        memory.save_memory({"pending_goal": command})
        full_goal = command

    return full_goal


# -----------------------------
# Tool Execution Layer
# -----------------------------

def execute_tool(action, params):
    try:
        if action in ["open_chrome", "switch_profile"]:
            open_chrome(params.get("profile"))
            return "done"

        elif action == "youtube_search":
            youtube_search_tool(params.get("query"))
            return "done"

        elif action == "google_search":
            google_search_tool(params.get("query"))
            return "done"

        elif action == "amazon_search":
            amazon_search_tool(params.get("query"))
            return "done"

        elif action == "add_to_cart":
            add_to_cart_tool()
            return "done"

        elif action == "click_video":
            click_video_tool(params.get("title") or params.get("query"))
            return "done"

        elif action == "open_website":
            open_website(params.get("url"))
            return "done"

        elif action == "click":
            click(selector=params.get("selector"))
            return "done"

        elif action == "type_into":
            type_into(params.get("selector"), params.get("text"))
            return "done"

        elif action == "select_item":
            select_item(params.get("index", 1))
            return "done"

        elif action == "skip_ad":
            from tools import skip_ad_tool
            skip_ad_tool()
            return "done"

        elif action == "ask_user":
            ask_user(params.get("question"))
            return "break"

        elif action == "chat":
            chat(params.get("message"))
            return "break"

        elif action == "done":
            return "done"

        return None

    except Exception as e:
        print(f"[Tool Error] {e}")
        raise e


# -----------------------------
# ReAct Execution Loop
# -----------------------------

def execute_with_react(planned_tool, planned_params, max_turns=3):
    last_action = None
    last_error = None
    
    # 1. State-Aware Loop Detection
    state_history = [] 

    print(f"\n[Executing Step] {planned_tool}({planned_params})")

    for turn in range(max_turns):
        # 2. Get browser state & Goal Completion Guard
        current_state = get_browser_state()
        
        if not current_state:
            from browser import ensure_browser
            ensure_browser()
            current_state = get_browser_state() or {"status": "OPEN"}

        # Goal Completion Detection
        url = current_state.get("url", "")
        if planned_tool == "open_website" and planned_params.get("url") in url:
            print("    [Guard] Website already open.")
            return "done"
        if planned_tool == "click_video" and current_state.get("is_video_playing"):
            print("    [Guard] Video already playing.")
            return "done"
        if planned_tool == "youtube_search" and "results" in url:
             print("    [Guard] Search results already visible.")
             return "done"

        # Loop Detection (URL + Title)
        current_loc = (url, current_state.get("title", ""))
        if state_history.count(current_loc) >= 2:
            print("    [LOOP DETECTED] Interaction loop.")
            return "timeout"
        state_history.append(current_loc)

        # 3. Deterministic First Turn: Execute Planned Tool
        if turn == 0:
            print(f"    [Turn 1] Direct Execution: {planned_tool}")
            try:
                execute_tool(planned_tool, planned_params)
                last_action = f"{planned_tool}({planned_params})"
                memory.add_action_to_history(last_action)
                time.sleep(1) # Let page load
                continue # Verify in next turn
            except Exception as e:
                last_error = str(e)
                print(f"    [Direct Execution Failed] {e}")

        # 4. Verification & Correction Turn
        history = memory.get_action_history()
        decision = think(
            command=f"Verify and complete step: {planned_tool}({planned_params})",
            current_state=current_state,
            last_action=last_action,
            pending_goal=planned_tool,
            last_error=last_error,
            history=history
        )

        action = decision.get("action")
        params = decision.get("params", {})
        thought = decision.get("thought", "Verifying...")

        print(f"    [Turn {turn+1}] {thought}")
        print(f"    [Action] {action}({params})")

        if not action or action == "done":
            return "done"

        try:
            signal = execute_tool(action, params)
            last_action = f"{action}({params})"
            memory.add_action_to_history(last_action)
            last_error = None

            if signal == "done" and action == planned_tool:
                 return "done"
            if signal == "break":
                return "break"

        except Exception as e:
            last_error = str(e)
            print(f"    [Execution Error] {e}")

        time.sleep(0.5)

    return "done"


# -----------------------------
# Main Agent Execution
# -----------------------------

def execute(command):
    full_goal = prepare_goal(command)
    print(f"\n[GOAL] {full_goal}")

    # Planning
    steps = plan_goal(command)
    memory.save_plan(steps)

    print("\n[PLAN]")
    for i, step in enumerate(steps, 1):
        print(f"{i}. {step['tool']}({step.get('params', {})})")

    # Execution
    for i, step in enumerate(steps):
        tool = step["tool"]
        params = step.get("params", {})

        if tool == "done":
            print("\n[FINISH] Task completed.")
            break

        memory.set_current_step(i)
        result = execute_with_react(tool, params)

        if result == "timeout":
            print(f"[ERROR] Step {i+1} failed.")
            break

    print("\nAI signed off. Execution complete.")