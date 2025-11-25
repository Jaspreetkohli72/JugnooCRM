import time
from playwright.sync_api import sync_playwright
import os

# CONFIGURATION
APP_URL = "https://jugnoocrm.streamlit.app/"
USERNAME = "Jaspreet"
PASSWORD = "CRMJugnoo@123"
REPORT_FILE = "test_report.html"

results = []

def log_result(test_name, status, message=""):
    color = "green" if status == "PASS" else "red"
    results.append(f"<tr style='color:{color}'><td>{test_name}</td><td><b>{status}</b></td><td>{message}</td></tr>")
    print(f"[{status}] {test_name}: {message}")

def run_tests():
    print(f"🚀 STARTING Tests on: {APP_URL}")
    print("👀 Browser opening...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=2000)
        
        # --- TEST 1: DESKTOP LOGIN ---
        try:
            page = browser.new_page()
            print("⏳ Loading App (Wait up to 3 mins for wake-up)...")
            page.goto(APP_URL, timeout=180000)
            
            # 1. Check for "Wake Up" button common on Streamlit Cloud
            try:
                wake_btn = page.get_by_text("Yes, get this app back up!")
                if wake_btn.is_visible(timeout=10000):
                    print("💤 App is sleeping. Waking it up...")
                    wake_btn.click()
                    print("... giving app 20 seconds to restart...")
                    time.sleep(20) # Wait for restart
            except:
                print("... app is already awake.")

            # 2. Locate the Streamlit iframe
            print("🔍 Looking for Streamlit iframe...")
            iframe = page.frame_locator('iframe[title="streamlitApp"]')
            
            # 3. Wait for and fill inputs within the iframe
            print("🔍 Looking for Login Form within iframe...")
            iframe.get_by_label("Username").wait_for(timeout=120000)
            
            print("✍️ Filling Credentials...")
            iframe.get_by_label("Username").fill(USERNAME)
            iframe.get_by_label("Password").fill(PASSWORD)
            
            # 4. Click Login within the iframe
            print("🖱️ Clicking Login...")
            iframe.get_by_role("button", name="Login").click()
            
            # 5. Validate Dashboard within the iframe
            print("⏳ Waiting for Dashboard...")
            iframe.get_by_text("Active Projects").wait_for(timeout=60000)
            log_result("Login Flow", "PASS", "Logged in and saw 'Active Projects'")

            page.close()

        except Exception as e:
            print(f"❌ Error: {e}")
            log_result("Login Flow", "FAIL", str(e))
            try: page.screenshot(path="error_login.png"); print("📸 Screenshot saved to error_login.png")
            except: pass

        # --- TEST 2: MOBILE VISUALS ---
        try:
            print("\n📱 Testing Mobile View...")
            iphone = p.devices['iPhone 12']
            context = browser.new_context(**iphone)
            page = context.new_page()
            
            print("... loading app on mobile (3 min timeout)...")
            page.goto(APP_URL, timeout=180000)
            
            print("... looking for iframe on mobile...")
            iframe = page.frame_locator('iframe[title="streamlitApp"]')

            print("... waiting for app to render (2 min timeout)...")
            iframe.get_by_label("Username").wait_for(timeout=120000)
            time.sleep(5) 
            
            # Check CSS
            bg_color = iframe.locator(".stApp").evaluate("node => window.getComputedStyle(node).backgroundColor")
            # Dark mode is rgb(14, 17, 23)
            if "14, 17, 23" in bg_color:
                log_result("Mobile UI", "PASS", "Background is Dark #0E1117")
            else:
                log_result("Mobile UI", "FAIL", f"Background is {bg_color}")
                
            page.close()
            
        except Exception as e:
            log_result("Mobile UI", "FAIL", str(e))
            try: page.screenshot(path="error_mobile.png"); print("📸 Screenshot saved to error_mobile.png")
            except: pass

        browser.close()

    # --- GENERATE REPORT ---
    try:
        with open(REPORT_FILE, "w", encoding="utf-8") as f:
            f.write(f"""
            <html>
            <body style="font-family: sans-serif; background: #1e1e1e; color: #e0e0e0; padding: 20px;">
                <h1>🩺 Jugnoo CRM Report</h1>
                <table border="1" cellpadding="10" style="border-collapse: collapse; width: 100%;">
                    <tr style="background: #333;"><th>Test</th><th>Status</th><th>Details</th></tr>
                    {''.join(results)}
                </table>
            </body>
            </html>
            """)
        print(f"\n✅ Report generated: {os.path.abspath(REPORT_FILE)}")
    except:
        print("Error saving report.")

if __name__ == "__main__":
    run_tests()
