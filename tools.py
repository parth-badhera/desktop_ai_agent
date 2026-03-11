import subprocess
import os
import time
import browser # Access browser functions directly

def select_item(index):
    """High-level tool to select an item from a list (Search results or Interaction Points)."""
    p = browser.start_browser() # Get existing page
    state = browser.get_page_info()
    if not state:
        print("Cannot select item: browser not ready.")
        return False

    # 1. Check Structured Search Results (YouTube/Amazon)
    results = state.get("search_results", [])
    if results and 1 <= index <= len(results):
        if state.get("is_youtube"):
            p = browser.start_browser()
            p.locator("a#video-title").nth(index-1).click()
            return True
        target_text = results[index - 1]
        print(f"Selecting structured item {index}: {target_text}")
        browser.click_element(f"text='{target_text}'")
        return True

    # 2. Check Interaction Points (Ranked items)
    elements = state.get("elements", [])
    if elements and 1 <= index <= len(elements):
        el = elements[index - 1]
        print(f"Selecting ranked item {index}: {el['text']}")
        browser.click_element(el['selector'])
        return True

    print(f"Index {index} out of range.")
    return False

def open_chrome(profile=None):
    if browser.is_browser_running():
        print("Browser already open.")
        return

    num = None
    if profile:
        try: num = int(''.join(filter(str.isdigit, str(profile))))
        except: num = 1
    
    # Open a default page (google) so it's ready
    p = browser.open_url("https://www.google.com", profile_num=num)
    if p:
        print(f"Browser state: {p.url}")
    print(f"Opening browser with Profile {num if num else 'Default'} - READY")

def open_app(name):
    try: subprocess.Popen([name])
    except FileNotFoundError: print(f"Could not open {name}.")

def search_web(query):
    browser.search(query)

def open_website(url):
    if not url.startswith("http"):
        url = "https://" + url
    browser.open_url(url)

def switch_profile(profile):
    open_chrome(profile)

def click(target=None, selector=None):
    final_target = selector or target
    if not final_target:
        print("Click failed: No target specified.")
        return False
    # If target starts with text=, use it directly, otherwise prioritize id or common selectors
    return browser.click_element(final_target)

def youtube_search_tool(query):
    browser.youtube_search(query)
    return "Searching YouTube..."

def google_search_tool(query):
    browser.google_search(query)
    return "Searching Google..."

def amazon_search_tool(query):
    browser.amazon_search(query)
    return "Searching Amazon..."

def add_to_cart_tool():
    success = browser.add_to_cart()
    return "Added to cart" if success else "Failed to add to cart"

def click_video_tool(title):
    browser.click_video(title)
    return f"Clicking video: {title}"

def chat(message):
    print(f"AI: {message}")

def type_into(selector, text):
    browser.type_text(selector, text)

def ask_user(question):
    print(f"QUESTION: {question}")

def list_profiles():
    return browser.get_profiles()

def list_open_tabs():
    return browser.get_open_tabs()

def open_new_tab(url):
    browser.open_new_tab(url)

def skip_ad_tool():
    success = browser.skip_ad()
    return "Skipped ad" if success else "No skip button found"

def get_browser_state():
    return browser.get_page_info()
