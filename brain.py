import ollama
import json

def think(command, current_state=None, last_action=None, pending_goal=None, last_error=None):

    state_desc = "BROWSER IS CLOSED."
    if current_state:
        state_desc = ""
        if "url" in current_state:
            state_desc += f"BROWSER IS OPEN.\nURL: {current_state.get('url')}\nTitle: {current_state.get('title')}\n"
            if current_state.get('elements'):
                state_desc += "Elements on page:\n"
                for el in current_state.get('elements', []):
                    state_desc += f"- {el['tag']} '{el['text']}' (Selector: {el['selector']})\n"
        
        if current_state.get("profiles"):
            state_desc += "\nAvailable Chrome Profiles:\n"
            for p in current_state["profiles"]:
                state_desc += f"- {p['name']} (Status: {p['status']})\n"
        
        if current_state.get("open_tabs"):
            state_desc += "\nCurrently Open Tabs:\n"
            for tab in current_state["open_tabs"]:
                state_desc += f"- {tab['title']} ({tab['url']})\n"
    
    if not state_desc: state_desc = "BROWSER IS CLOSED."

    if current_state and current_state.get("is_video_playing"):
        state_desc += "ACTIVE VIDEO: A video is currently playing.\n"

    last_act_desc = f"Last Action Taken: {last_action}" if last_action else ""
    pending_goal_desc = f"PAST GOAL (In Progress): {pending_goal}" if pending_goal else ""
    error_feedback = f"\n### PREVIOUS ERROR ###\n{last_error}\nPlease fix this in your next action." if last_error else ""

    # INTENT-BASED TOOL GATING: Stop the AI from guessing selectors.
    is_complex = any(word in command.lower() for word in ["play", "search", "find", "click", "type", "buy", "login", "select", "profile"])
    
    available_tools = [
        "- youtube_search(query=\"...\")",
        "- click_video(title=\"...\")",
        "- google_search(query=\"...\")",
        "- open_chrome(profile=\"1\")",
        "- open_website(url=\"...\")",
        "- click(target=\"...\")",
        "- type_into(selector=\"...\", text=\"...\")",
        "- done()"
    ]
    
    minimalism_rule = "1. MINIMALISM: This is a SIMPLE task. If BROWSER IS CLOSED, call `open_chrome()`. Only call `done()` once a real page is visible."
    
    if is_complex:
        minimalism_rule = "1. INTENT MODE: Use high-level tools. For YouTube, use `youtube_search` then `click_video`. Do NOT guess selectors if an intent tool exists."

    tools_str = "\n".join(available_tools)

    prompt = f"""
### SYSTEM ###
You are a technical Desktop Automation Engine.
Goal: {command}
Efficiency: Solve in 1-4 steps.

### MANDATORY TOOLS ###
{tools_str}

### RULES ###
{minimalism_rule}
2. NO SELECTOR GUESSING: If you are on YouTube, use `youtube_search` and `click_video`. Do NOT use `type_into` or `click` with raw selectors for these sites unless necessary.
3. SUCCESS: If 'is_video_playing' is True, call `done()` IMMEDIATELY.
4. NEXT STEP ONLY: Output EXACTLY ONE JSON object. No conversational text.

### CONTEXT ###
{pending_goal_desc}
{last_act_desc}
{state_desc}

### EXAMPLES ###
- State: BROWSER IS CLOSED | Goal: "play alone song" -> {{"thought": "Opening browser to play song.", "action": "open_chrome", "params": {{"profile": "1"}}}}
- State: URL: youtube.com | Goal: "play alone song" -> {{"thought": "Searching YouTube.", "action": "youtube_search", "params": {{"query": "alone song"}}}}
- State: Search Results | Goal: "play alone song" -> {{"thought": "Clicking video.", "action": "click_video", "params": {{"title": "alone"}}}}

### RESPONSE FORMAT (STRICT JSON) ###
{{"thought": "...", "action": "...", "params": {{...}}}}
"""

    def extract_json(text):
        # Character-by-character scan for balanced brackets
        start = text.find("{")
        if start == -1:
            raise ValueError("No JSON found (missing '{')")
        
        count = 0
        for i in range(start, len(text)):
            if text[i] == '{': count += 1
            elif text[i] == '}': count -= 1
            
            if count == 0:
                json_str = text[start:i+1]
                return json.loads(json_str)
        
        raise ValueError("Incomplete JSON (missing closing '}')")

    retries = 3
    current_prompt = prompt
    
    for attempt in range(retries):
        try:
            response = ollama.chat(
                model="llama3",
                messages=[{"role":"user","content":current_prompt}]
            )

            text = response["message"]["content"]
            try:
                decision = extract_json(text)
                if isinstance(decision, dict) and "action" in decision:
                    return decision
            except Exception as e:
                print(f"JSON Parse Attempt {attempt+1} failed: {e}")
                # Provide a clearer hint for retry
                retry_hint = "\n\n### ERROR: Your previous output was not valid JSON. ###\nPlease output ONLY the JSON object, starting with '{' and ending with '}'. No other text."
                current_prompt = prompt + retry_hint
        except Exception as e:
            print(f"Ollama Attempt {attempt+1} failed: {e}")
        
    return {"action":"chat", "params": {"message": "I'm having trouble formatting my thoughts as JSON. Please try again."}}
