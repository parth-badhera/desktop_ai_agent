import os
import time
from playwright.sync_api import sync_playwright

playwright = None
browser = None
context = None
page = None

def get_profiles():
    chrome_path = os.path.abspath("./chrome_data")
    if not os.path.exists(chrome_path):
        os.makedirs(chrome_path, exist_ok=True)
        return [{"name": "Default", "status": "Available"}]
    
    # In the local agent folder, we don't worry about locks as much
    # but we will still show "Available" for consistency
    profiles = [{"name": "Default", "status": "Available"}]
    for item in sorted(os.listdir(chrome_path)):
        if item.startswith("Profile "):
            profiles.append({"name": item, "status": "Available"})
    return profiles

def get_open_tabs():
    global context
    if not context:
        return []
    tabs = []
    for p in context.pages:
        try:
            tabs.append({"title": p.title(), "url": p.url})
        except:
            continue
    return tabs

def is_browser_running():
    global context
    return context is not None

def start_browser(profile_num=None, auto_open=True):
    global playwright, browser, context, page
    if not playwright:
        playwright = sync_playwright().start()
    
    if not context:
        if not auto_open:
            return None
        
        # USE LOCAL DEDICATED FOLDER
        chrome_data = os.path.abspath("./chrome_data")
        os.makedirs(chrome_data, exist_ok=True)
        
        # Pre-create common profile folders for first run
        for p in ["Default", "Profile 1", "Profile 2"]:
            os.makedirs(os.path.join(chrome_data, p), exist_ok=True)

        all_profiles = get_profiles()
        profile_dir = None
        
        if profile_num:
            p_input = str(profile_num).strip()
            # 1. Check if it's a number (index into our list)
            if p_input.isdigit():
                idx = int(p_input)
                if 1 <= idx <= len(all_profiles):
                    profile_dir = all_profiles[idx - 1]["name"]
            
            # 2. Check for direct name match if not an index
            if not profile_dir:
                for p in all_profiles:
                    if p_input.lower() == p["name"].lower():
                        profile_dir = p["name"]
                        break
        
        # Fallback
        if not profile_dir:
            profile_dir = "Default"
        
        print(f"Launching Agent Chrome Profile: {profile_dir}")
        
        try:
            # Proactively clear profile-level locks if we are starting a profile
            profile_lock = os.path.join(chrome_data, profile_dir, "SingletonLock")
            if os.path.exists(profile_lock):
                try: os.remove(profile_lock)
                except: pass

            context = playwright.chromium.launch_persistent_context(
                user_data_dir=chrome_data,
                channel="chrome",
                headless=False,
                args=[f"--profile-directory={profile_dir}", "--no-sandbox", "--disable-dev-shm-usage"]
            )
            page = context.pages[0] if context.pages else context.new_page()
        except Exception as e:
            msg = str(e).lower()
            if "singletonlock" in msg or "processsingleton" in msg:
                # Root lock
                lock_file = os.path.join(chrome_data, "SingletonLock")
                if os.path.exists(lock_file):
                    try: os.remove(lock_file)
                    except: pass
                # Profile lock
                profile_lock = os.path.join(chrome_data, profile_dir, "SingletonLock")
                if os.path.exists(profile_lock):
                    try: os.remove(profile_lock)
                    except: pass
                
                print("Lock cleared. Retrying launch...")
                time.sleep(1)
                return start_browser(profile_num, auto_open)
            raise e

    return page

def open_new_tab(url):
    global context, page
    if not context:
        start_browser()
    
    # Open new page
    new_page = context.new_page()
    new_page.goto(url, timeout=30000)
    page = new_page # Focus the new tab
    return page


def open_url(url, profile_num=None, retries=2):
    for attempt in range(retries):
        try:
            p = start_browser(profile_num)
            p.goto(url, wait_until="domcontentloaded", timeout=20000)
            return p
        except Exception as e:
            msg = str(e).lower()
            if "target page, context or browser has been closed" in msg and attempt < retries - 1:
                print(f"Browser closed mid-launch. Retrying ({attempt+1}/{retries})...")
                stop_browser() # Reset global state
                time.sleep(2)
                continue
            print(f"Navigation error: {e}")
            return start_browser(profile_num) # Return blank page if all else fails

def search(query, profile_num=None):
    return open_url(f"https://www.google.com/search?q={query}", profile_num)

def wait_for_stable(p, timeout=2000):
    try:
        p.wait_for_load_state("domcontentloaded", timeout=timeout)
        p.wait_for_load_state("networkidle", timeout=timeout)
        time.sleep(0.5) # Final settle
    except:
        pass

def youtube_search(query):
    p = open_url("https://www.youtube.com", retries=2)
    wait_for_stable(p)
    
    selectors = ["input#search", "input[name='search_query']", "ytd-searchbox input"]
    success = False
    for s in selectors:
        try:
            p.wait_for_selector(s, timeout=3000)
            p.fill(s, query)
            p.press(s, "Enter")
            success = True
            break
        except:
            continue
    
    if not success:
        # Final fallback - try ANY visible input
        try:
            p.fill("input", query)
            p.press("input", "Enter")
        except Exception as e:
            print(f"YouTube search failed: {e}")
    
    wait_for_stable(p)

def click_video(title_hint):
    p = start_browser()
    wait_for_stable(p)
    
    # Try multiple ways to find the video
    selectors = [
        f"a#video-title:has-text('{title_hint}')",
        f"ytd-video-renderer:has-text('{title_hint}') a#video-title",
        "a#video-title" # Fallback to first video
    ]
    
    for s in selectors:
        try:
            p.wait_for_selector(s, timeout=3000, state="visible")
            p.click(s, timeout=5000)
            return
        except:
            continue
    
    print(f"Could not find video for: {title_hint}")

def google_search(query):
    p = start_browser()
    p.goto(f"https://www.google.com/search?q={query}", wait_until="domcontentloaded")
    wait_for_stable(p)

def get_page_info():
    try:
        if not is_browser_running():
            return None
        
        p = start_browser(auto_open=False)
        if not p or p.is_closed(): return None
        
        wait_for_stable(p, timeout=1000)
        
        # Check if video is playing
        is_playing = False
        try:
            is_playing = p.evaluate("""() => {
                const v = document.querySelector('video');
                // Consider playing if it's not paused, has started (currentTime > 0), and isn't ended.
                return v && !v.paused && v.currentTime > 0 && !v.ended && v.readyState >= 2;
            }""")
        except:
            pass

        script = """
        () => {
            const elements = document.querySelectorAll('button, input, a, [role="button"]');
            return Array.from(elements).map((el, i) => {
                const rect = el.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    const text = (el.innerText || el.placeholder || el.value || el.getAttribute('aria-label') || "").substring(0, 50).trim();
                    if (!text) return null;
                    return {
                        tag: el.tagName,
                        text: text,
                        id: el.id || `el-${i}`,
                        selector: el.id ? `#${el.id}` : el.tagName.toLowerCase()
                    };
                }
            }).filter(Boolean).slice(0, 40); 
        }
        """
        elements = p.evaluate(script)
        return {
            "url": p.url,
            "title": p.title(),
            "elements": elements,
            "is_video_playing": is_playing
        }
    except Exception as e:
        return {"error": str(e)}

def click_element(text_or_id):
    p = start_browser()
    wait_for_stable(p)
    old_url = p.url
    try:
        # 1. Try by text with strict visibility check
        p.click(f"text={text_or_id}", timeout=5000)
    except Exception as e:
        # Quiet Success: If URL changed, it likely worked!
        if p.url != old_url:
            return

        try:
            # 2. Try by ID/Selector with forced scroll
            p.wait_for_selector(text_or_id, timeout=3000, state="visible")
            el = p.locator(text_or_id).first
            el.scroll_into_view_if_needed()
            el.click(timeout=5000)
        except Exception as e2:
            if p.url != old_url:
                return
            # 3. Final forced attempt
            try:
                p.click(text_or_id, force=True, timeout=5000)
            except Exception as e3:
                if p.url != old_url:
                    return
                print(f"Click failed: {e3}")
    wait_for_stable(p)

def stop_browser():
    global playwright, browser, context, page
    try:
        if context: context.close()
        if playwright: playwright.stop()
    except: pass
    playwright = None
    browser = None
    context = None
    page = None

def type_text(selector, text):
    p = start_browser()
    wait_for_stable(p)
    try:
        # Wait for the specific selector first
        p.wait_for_selector(selector, timeout=5000)
        p.fill(selector, text)
        p.press(selector, "Enter")
    except Exception as e:
        # Fallback: Try to find ANY input if the specific one isn't there
        try:
            print(f"Selector {selector} not found, trying fallback input...")
            p.fill("input", text)
            p.press("input", "Enter")
        except:
            print(f"Type failed: {e}")
    wait_for_stable(p)
