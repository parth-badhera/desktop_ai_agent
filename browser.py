import os
import time
from playwright.sync_api import sync_playwright

playwright = None
browser = None
context = None
page = None

# Use a separate profile folder for automation to avoid lock conflicts
chrome_data = os.path.abspath("./agent_browser_profile")

def get_profiles():
    if not os.path.exists(chrome_data):
        os.makedirs(chrome_data, exist_ok=True)
        return [{"name": "Default", "status": "Available"}]
    
    profiles = [{"name": "Default", "status": "Available"}]
    try:
        for item in sorted(os.listdir(chrome_data)):
            if item.startswith("Profile "):
                profiles.append({"name": item, "status": "Available"})
    except:
        pass
    return profiles

def is_browser_running():
    global context, page
    if context is None or page is None:
        return False
    try:
        # Ping the page to confirm it is alive
        page.title()
        return True
    except:
        return False

def get_open_tabs():
    global context
    if not is_browser_running():
        return []
    tabs = []
    for p in context.pages:
        try:
            tabs.append({"title": p.title(), "url": p.url})
        except:
            continue
    return tabs

def open_new_tab(url):
    global context, page
    if not is_browser_running():
        start_browser()
    new_page = context.new_page()
    new_page.goto(url, timeout=30000)
    page = new_page
    return page

def take_screenshot():
    global page
    if not page:
        return None
    path = "/tmp/agent_screenshot.png"
    try:
        page.screenshot(path=path)
        return path
    except:
        return None

def start_browser(profile_num=None, auto_open=True, _retry_count=0):
    global playwright, browser, context, page
    
    if is_browser_running():
        return page

    if not playwright:
        playwright = sync_playwright().start()
    
    # Close old context if it exists but is dead
    if context:
        try: context.close()
        except: pass
        context = None

    os.makedirs(chrome_data, exist_ok=True)
    for p_name in ["Default", "Profile 1", "Profile 2"]:
        os.makedirs(os.path.join(chrome_data, p_name), exist_ok=True)

    all_profiles = get_profiles()
    profile_dir = "Default"
    if profile_num:
        p_input = str(profile_num).strip()
        if p_input.isdigit():
            idx = int(p_input)
            if 1 <= idx <= len(all_profiles):
                profile_dir = all_profiles[idx - 1]["name"]
        else:
            for p in all_profiles:
                if p_input.lower() == p["name"].lower():
                    profile_dir = p["name"]
                    break
    
    print(f"Launching Agent Chrome Profile: {profile_dir}")
    locks = [
        os.path.join(chrome_data, "SingletonLock"),
        os.path.join(chrome_data, profile_dir, "SingletonLock"),
        os.path.join(chrome_data, profile_dir, "lockfile")
    ]
    for lock in locks:
        if os.path.exists(lock):
            try: os.remove(lock)
            except: pass

    try:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=chrome_data,
            channel="chrome",
            headless=False,
            args=[
                f"--profile-directory={profile_dir}", 
                "--no-sandbox", 
                "--disable-dev-shm-usage",
                "--disable-extensions",
                "--no-first-run"
            ]
        )
        page = context.pages[0] if context.pages else context.new_page()
    except Exception as e:
        msg = str(e).lower()
        if "singletonlock" in msg or "processsingleton" in msg or "used by another" in msg:
            print(f"Lock detected ({profile_dir}). Clearing and retrying...")
            for lock in locks:
                if os.path.exists(lock):
                    try: os.remove(lock)
                    except: pass
            time.sleep(2)
            return start_browser(profile_num, auto_open, _retry_count + 1)
        raise e

    return page

def ensure_browser():
    """Ensure the browser is running and the page is active."""
    if is_browser_running():
        return True
    print("[Session Manager] Browser lost or closed. Re-launching...")
    return start_browser() is not None

def open_url(url, profile_num=1):
    p = start_browser(profile_num)
    if not p:
        raise RuntimeError("Browser failed to start (likely a profile lock issue)")
    try:
        p.goto(url, wait_until="domcontentloaded", timeout=30000)
        return p
    except Exception as e:
        print(f"Navigation error: {e}")
        return p

def skip_ad():
    global page
    if not is_browser_running():
        return False
    try:
        # Check for various skip ad buttons
        skip_button = page.query_selector(".ytp-ad-skip-button, .ytp-skip-ad-button, [class*='skip-ad']")
        if skip_button and skip_button.is_visible():
            skip_button.click()
            print("Action: Skipped YouTube Ad")
            return True
    except:
        pass
    return False

def search(query, profile_num=None):
    return open_url(f"https://www.google.com/search?q={query}", profile_num)

def wait_for_stable(p, timeout=2000):
    try:
        p.wait_for_load_state("domcontentloaded", timeout=timeout)
        p.wait_for_load_state("networkidle", timeout=timeout)
        time.sleep(0.2)
    except:
        pass

def youtube_search(query):
    encoded = query.replace(" ", "+")
    p = open_url(f"https://www.youtube.com/results?search_query={encoded}")
    wait_for_stable(p)

def click_video(title_hint):
    p = start_browser()
    wait_for_stable(p)
    try:
        p.wait_for_selector("a#video-title", timeout=5000)
        p.locator("a#video-title").first.click()
    except Exception as e:
        print(f"Click video failed: {e}")

def google_search(query):
    p = start_browser()
    p.goto(f"https://www.google.com/search?q={query}", wait_until="domcontentloaded")
    wait_for_stable(p)

def amazon_search(query):
    p = open_url("https://www.amazon.in")
    wait_for_stable(p)
    selectors = ["input#twotabsearchtextbox", "input[name='field-keywords']", "input.nav-input[type='text']"]
    for s in selectors:
        try:
            p.wait_for_selector(s, timeout=4000, state="visible")
            p.fill(s, query)
            p.press(s, "Enter")
            break
        except:
            continue
    wait_for_stable(p)

def add_to_cart():
    p = start_browser()
    wait_for_stable(p)
    selectors = ["input#add-to-cart-button", "button#add-to-cart-button", "#add-to-cart-button"]
    for s in selectors:
        try:
            p.wait_for_selector(s, timeout=4000, state="visible")
            p.click(s, timeout=5000)
            time.sleep(2)
            return True
        except:
            continue
    return False

def get_page_info():
    try:
        if not is_browser_running():
            return None
        global page
        p = page
        url = p.url
        title = p.title()
        is_playing = False
        ad_skip_available = False
        if "youtube.com" in url:
            try:
                is_playing = p.evaluate("() => { const v = document.querySelector('video'); return v && !v.paused && !v.ended; }")
                ad_skip_available = p.locator(".ytp-ad-skip-button, .ytp-skip-ad-button").is_visible(timeout=500)
                if ad_skip_available:
                    skip_ad()
            except: pass
        elif "amazon.in" in url:
            try: is_playing = p.evaluate("() => { const v = document.querySelector('video'); return v && !v.paused && !v.ended; }")
            except: pass
        
        script = """
        () => {
            const elements = document.querySelectorAll('button, input, a, [role="button"], h2, h3');
            let scraped = Array.from(elements).map((el, i) => {
                const rect = el.getBoundingClientRect();
                if (rect.width <= 0 || rect.height <= 0) return null;
                let text = (el.innerText || el.placeholder || el.value || el.getAttribute('aria-label') || "").trim();
                if (!text || text.length < 2) return null;
                text = text.substring(0, 100).replace(/\\s+/g, " ").trim();
                
                // Deterministic Selectors
                let selector;
                if (el.id) selector = `#${el.id}`;
                else if (el.tagName === 'A' && el.id === 'video-title') selector = 'a#video-title';
                else if (el.tagName === 'A' && el.innerText) selector = `a:has-text("${el.innerText.substring(0,20).replace(/"/g, '')}")`;
                else selector = el.tagName.toLowerCase();
                
                let score = 0;
                const lowerText = text.toLowerCase();
                if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') score += 10;
                if (lowerText.includes('search') || el.name === 'q' || el.id === 'search') score += 15;
                if (lowerText.includes('cart') || lowerText.includes('buy')) score += 8;
                if (lowerText.includes('play') || el.id === 'video-title') score += 7;
                if (el.tagName.startsWith('H')) score += 3;
                return { tag: el.tagName, text: text, selector: selector, score: score };
            }).filter(Boolean);
            return scraped.sort((a, b) => b.score - a.score).slice(0, 15);
        }
        """
        elements = p.evaluate(script)
        
        # Enhanced Page Summary
        summary = f"Page Title: {title}\nURL: {url}"
        
        search_results = []
        if "youtube.com/results" in url:
            try: search_results = p.evaluate("() => Array.from(document.querySelectorAll('a#video-title')).slice(0, 5).map(el => el.innerText.trim())")
            except: pass
        
        return { 
            "url": url, 
            "title": title, 
            "summary": summary,
            "elements": elements, 
            "search_results": search_results, 
            "is_video_playing": is_playing,
            "is_youtube": "youtube.com" in url,
            "ad_skip_available": ad_skip_available,
            "status": "BROWSER_OPEN" if url != "about:blank" else "BROWSER_READY" 
        }
    except Exception as e:
        print(f"Error getting page info: {e}")
        return None

def click_element(selector):
    p = start_browser()
    wait_for_stable(p)
    try:
        p.wait_for_selector(selector, timeout=5000, state="visible")
        el = p.locator(selector).first
        el.scroll_into_view_if_needed()
        el.click(timeout=5000)
    except Exception as e:
        try: p.click(selector, force=True, timeout=5000)
        except: print(f"Click failed: {e}")
    wait_for_stable(p)

def stop_browser():
    global playwright, browser, context, page
    try:
        if context: context.close()
        if playwright: playwright.stop()
    except: pass
    playwright = browser = context = page = None

def type_text(selector, text):
    p = start_browser()
    wait_for_stable(p)
    try:
        p.wait_for_selector(selector, timeout=5000)
        p.fill(selector, text)
        p.press(selector, "Enter")
    except Exception as e:
        try:
            p.fill("input", text)
            p.press("input", "Enter")
        except:
            print(f"Type failed: {e}")
    wait_for_stable(p)
