import re
import ollama
import json

def think(command, current_state=None, last_action=None, pending_goal=None, last_error=None, history=None):

    # ROBOTIC STATE GATING
    state_desc = "### BROWSER: CLOSED ###"
    if current_state:
        status = current_state.get("status", "CLOSED")
        url = current_state.get("url", "about:blank")
        
        if status != "CLOSED":
            summary = current_state.get('summary', 'No summary available.')
            state_desc = f"### BROWSER: OPEN ###\nURL: {url}\nTitle: {current_state.get('title', '')}\nSummary: {summary}\n"
            if current_state.get('elements'):
                state_desc += "Interaction Points:\n"
                for el in current_state.get('elements', []):
                    state_desc += f"- {el['tag']} '{el['text']}' (Use `click('{el['selector']}')`)\n"
            if current_state.get("is_video_playing"):
                state_desc += "!! STATUS: Video is playing !!\n"
    # GROUNDED SEARCH RESULTS
    results_str = ""
    if current_state and current_state.get("search_results"):
        results_str = "\nSTRUCTURED SEARCH RESULTS:\n"
        for i, res in enumerate(current_state["search_results"], 1):
            results_str += f"{i}. {res}\n"
    
    state_desc += results_str

    last_act_desc = f"\n### LAST ACTION ###\n{last_action}" if last_action else ""
    history_desc = f"\n### ACTION HISTORY (Last 5) ###\n" + "\n".join(history[-5:]) if history else ""
    pending_goal_desc = f"\n### FULL GOAL (MEMO) ###\n{pending_goal}" if pending_goal else ""
    error_feedback = f"\n### PREVIOUS ERROR ###\n{last_error}\nPlease fix this in your next action." if last_error else ""

    available_tools = [
        "- youtube_search(query=\"...\")",
        "- click_video(title=\"...\")",
        "- skip_ad()",
        "- amazon_search(query=\"...\")",
        "- google_search(query=\"...\")",
        "- open_website(url=\"...\")",
        "- click(selector=\"...\")",
        "- type_into(selector=\"...\", text=\"...\")",
        "- select_item(index=1)",
        "- done()"
    ]
    tools_str = "\n".join(available_tools)

    prompt = f"""
### SYSTEM: ROBOTIC BROWSER CONTROLLER (VERIFICATION MODE) ###
Your task is to VERIFY if the current step is complete and take corrective action if not.

Goal: {command}
Target Step: {pending_goal}

### PROTOCOL ###
1. **SATISFACTION CHECK**: If the browser state shows the goal is met (e.g. video playing, correct page open), immediately call `done()`.
2. **CORRECTIVE ACTION**: If the previous tool failed or we are on the wrong page, use the Interaction Points to fix it.
3. **JSON ONLY**: Output ONLY valid JSON.
4. **YouTube Handling**: If an ad is visible, call `skip_ad()`.

### BROWSER STATE ###
{state_desc}
{history_desc}
{last_act_desc}
{error_feedback}

### AVAILABLE TOOLS ###
{tools_str}

### RESPONSE SCHEMA ###
{{"thought": "[Reasoning about current state vs goal]", "action": "[Tool]", "params": {{...}}}}
"""

    def extract_json(text):
        # 1. Clean up potential LLM noise
        text = text.strip()
        start = text.find("{")
        if start == -1:
            raise ValueError("No JSON found (missing '{')")
        
        # 2. Extract balanced object
        count = 0
        json_str = ""
        for i in range(start, len(text)):
            if text[i] == '{': count += 1
            elif text[i] == '}': count -= 1
            if count == 0:
                json_str = text[start:i+1]
                break
        
        if not json_str:
            raise ValueError("Incomplete JSON")

        # 3. Try standard JSON first
        try:
            return json.loads(json_str)
        except:
            # 4. Fallback: Fix single quotes and trailing commas
            # (Crude but effective for Llama 3)
            fixed = json_str.replace("'", '"')
            fixed = re.sub(r",\s*([\]}])", r"\1", fixed)
            try:
                return json.loads(fixed)
            except Exception as e:
                raise ValueError(f"JSON Fixer failed: {e}")

    retries = 3
    current_prompt = prompt
    
    for attempt in range(retries):
        try:
            response = ollama.chat(
                model="qwen2.5-coder:7b",
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

def plan_goal(command):
    prompt = f"""
### SYSTEM: BROWSER AI PLANNER ###
You are a task planner for an autonomous desktop AI agent.
Your job is to convert a user goal into a sequence of executable tool calls.

### IMPORTANT RULES ###
1. Every step must correspond to an available tool.
2. Do NOT invent websites or actions (e.g., no 'chrome.com').
3. Prefer direct navigation (`open_website`) instead of search when possible.
4. When a tool requires a query parameter (e.g., `youtube_search`, `google_search`), YOU MUST extract the specific search terms from the user goal. 
   - CRITICAL: Never use placeholders like "default", "search", "query", or "...".
   - Example:
    Goal: play bairan song
Tool: youtube_search
Query: bairan song
5. The final step must ALWAYS be "done".
6. Output ONLY valid JSON.
7. If the goal contains words like "play", "watch", or "listen":
   - First use youtube_search(query)
   - Then use select_item(index=1)
   - Then done

### AVAILABLE TOOLS ###
- open_chrome
- open_website(url)
- youtube_search(query)
- google_search(query)
- amazon_search(query)
- select_item(index)
- click(selector)
- type_into(selector, text)
- add_to_cart
- done

### RESPONSE SCHEMA ###
{{
  "goal": "{command}",
  "steps": [
    {{"tool": "tool_name", "params": {{...}}}},
    ...
  ]
}}

Goal: {command}
"""
    try:
        response = ollama.chat(
            model="qwen2.5-coder:7b",
            messages=[{"role":"user","content":prompt}]
        )
        text = response["message"]["content"]
        
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            plan_json = json.loads(text[start:end+1])
            return plan_json.get("steps", [])
    except Exception as e:
        print(f"Planning failed: {e}")
    
    # Fallback plan: single step
    return [{"tool": "open_website", "params": {"url": "https://www.google.com"}}, {"tool": "done", "params": {}}]
