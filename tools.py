import subprocess
import os
from browser import open_url, search, click_element, type_text, get_page_info, get_profiles, get_open_tabs, open_new_tab, youtube_search as br_yt_search, google_search as br_g_search, click_video as br_clk_video


def open_chrome(profile=None):
    # Unify with Playwright so the AI can 'see' the browser it opens
    num = None
    if profile:
        try:
            num = int(''.join(filter(str.isdigit, str(profile))))
        except:
            num = 1 # Default
            
    # Open a default page (google) so it's ready
    open_url("https://www.google.com", profile_num=num)
    print(f"Opening browser with Profile {num if num else 'Default'}")


def open_app(name):
    try:
        subprocess.Popen([name])
    except FileNotFoundError:
        print(f"Could not open {name}. Make sure it is in your PATH.")


def search_web(query):
    search(query)


def open_website(url):
    if not url.startswith("http"):
        url = "https://" + url
    open_url(url)

def switch_profile(profile):
    open_chrome(profile)

def click(target):
    click_element(target)

def youtube_search(query):
    br_yt_search(query)

def google_search(query):
    br_g_search(query)

def click_video(title):
    br_clk_video(title)

def chat(message):
    print(f"AI: {message}")

def type_into(selector, text):
    type_text(selector, text)

def ask_user(question):
    # This is handled specially by the parser to pause execution
    print(f"QUESTION: {question}")

def list_profiles():
    return get_profiles()

def list_open_tabs():
    return get_open_tabs()

def open_new_tab(url):
    from browser import open_new_tab as b_ont
    b_ont(url)

def get_browser_state():
    return get_page_info()
