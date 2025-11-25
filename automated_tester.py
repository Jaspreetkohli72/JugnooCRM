import time
from playwright.sync_api import sync_playwright
import os

# CONFIGURATION - LIVE URL
APP_URL = "https://jugnoocrm.streamlit.app/"
USERNAME = "Jaspreet"
PASSWORD = "CRMJugnoo@123"
REPORT_FILE = "test_report.html"

# EXACT XPATHS PROVIDED BY USER
XPATH_USER = '/html/body/div/div[1]/div[1]/div/div/div/section/div[1]/div/div[5]/div/div[2]/div/div/div/div/div[2]/div/div/div/input'
XPATH_PASS = '/html/body/div/div[1]/div[1]/div/div/div/section/div[1]/div/div[5]/div/div[2]/div/div/div/div/div[3]/div/div/div/input'

results = []

def log_result(test_name, status, message=""):
    color = "green" if status == "PASS" else "red"
    results.append(f"<tr style='color:{color}'><td>{test_name}</td><td><b>{status}</b></td><td>{message}</td></tr>")
    print(f"[{status}] {test_name}: {message}")

def run_tests():
    print(f"STARTING Tests on LIVE URL: {APP_URL}")
    print("Browser window will open shortly...")
    
    with sync_playwright() as p:
        # --- TEST 1: DESKTOP LOGIN ---
        try:
            browser = p.chromium.launch(headless=False, slow_mo=1000) 
            page = browser.new_page()
            
            print("⏳ Loading App URL (Timeout 3 mins)...")
            page.goto(APP_URL, timeout=180000)
            
            print("⏳ Manual Wait: 15 seconds for Streamlit to initialize...")
            time.sleep(15)
            
            print("Looking for Username field via Full XPath...")
            # Wait for the specific element to exist
            page.locator(XPATH_USER).wait_for(state="visible", timeout=120000)
            
            print("Entering Credentials...")
            page.locator(XPATH_USER).fill(USERNAME)
            page.locator(XPATH_PASS).fill(PASSWORD)
            
            # Click Login Button
            page.get_by_role("button", name="Login").click()
            
            # Wait for Dashboard
            print("Waiting for Dashboard to render...")
            page.get_by_text("Active Projects").wait_for(timeout=60000)
            
            log_result("Live Login", "PASS", "Successfully logged into Jugnoo CRM")
            
            browser.close()
            
        except Exception as e:
            log_result("Live Login Flow", "FAIL", f"Error: {str(e)}")

        # --- TEST 2: MOBILE VISUALS ---
        try:
            print("Switching to iPhone Mode...")
            iphone = p.devices['iPhone 12']
            browser = p.chromium.launch(headless=False, slow_mo=1000)
            context = browser.new_context(**iphone)
            page = context.new_page()
            
            page.goto(APP_URL, timeout=180000)
            
            print("⏳ Manual Wait: 15 seconds for Mobile View...")
            time.sleep(15)
            
            # Wait for content using the Full XPath
            page.locator(XPATH_USER).wait_for(timeout=120000)
            
            # Check Background Color
            bg_color = page.evaluate("window.getComputedStyle(document.querySelector('.stApp')).backgroundColor")
            
            # rgb(14, 17, 23) is the Hex #0E1117 (Dark Theme)
            if "14, 17, 23" in bg_color:
                log_result("Mobile Visuals", "PASS", "Background is Dark (No White Bars)")
            else:
                log_result("Mobile Visuals", "FAIL", f"Background detected as {bg_color}")
            
            browser.close()
        except Exception as e:
            log_result("Mobile Simulation", "FAIL", str(e))

    # --- GENERATE REPORT ---
    try:
        with open(REPORT_FILE, "w", encoding="utf-8") as f:
            f.write(f"""
            <html>
            <body style="font-family: sans-serif; background: #1e1e1e; color: #e0e0e0; padding: 20px;">
                <h1 style="border-bottom: 1px solid #444; padding-bottom: 10px;">Jugnoo CRM Health Report</h1>
                <p><b>Target:</b> <a href="{APP_URL}" style="color: #4da6ff;">{APP_URL}</a></p>
                <p><b>Date:</b> {time.ctime()}</p>
                <br>
                <table border="1" cellpadding="12" style="border-collapse: collapse; width: 100%; border-color: #444;">
                    <tr style="background: #333;"><th>Test Case</th><th>Status</th><th>Details</th></tr>
                    {''.join(results)}
                </table>
            </body>
            </html>
            """)
        print(f"\nREPORT GENERATED: {os.path.abspath(REPORT_FILE)}")
    except Exception as e:
        print(f"Error saving report: {e}")

if __name__ == "__main__":
    run_tests()