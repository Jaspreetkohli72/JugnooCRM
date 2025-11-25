import time
from playwright.sync_api import sync_playwright
import os

# CONFIGURATION - LIVE URL
APP_URL = "https://jugnoocrm.streamlit.app/"
USERNAME = "Jaspreet"
PASSWORD = "CRMJugnoo@123"
REPORT_FILE = "test_report.html"

results = []

def log_result(test_name, status, message=""):
    color = "green" if status == "PASS" else "red"
    # Simple HTML table row formatting
    results.append(f"<tr style='color:{color}'><td>{test_name}</td><td><b>{status}</b></td><td>{message}</td></tr>")
    print(f"[{status}] {test_name}: {message}")

def run_tests():
    print(f"🚀 Starting Tests on LIVE URL: {APP_URL}...")
    print("👀 Browser window will open shortly...")
    
    with sync_playwright() as p:
        # --- TEST 1: DESKTOP LOGIN ---
        try:
            # HEADLESS=FALSE makes the browser visible
            # SLOW_MO=1000 adds a 1 second pause between actions so you can see what's happening
            browser = p.chromium.launch(headless=False, slow_mo=1000) 
            page = browser.new_page()
            
            print("⏳ Waiting for app to wake up (this can take up to 90s)...")
            # Increased timeout to 90s for Cloud cold start
            page.goto(APP_URL, timeout=90000)
            
            # Wait for Streamlit to wake up and load inputs
            page.wait_for_selector("input[aria-label='Username']", state="visible", timeout=90000)
            
            # Perform Login
            page.fill("input[aria-label='Username']", USERNAME)
            page.fill("input[aria-label='Password']", PASSWORD)
            
            # Click Login Button
            page.get_by_role("button", name="Login").click()
            
            # Wait for Dashboard to appear (Look for 'Active Projects')
            page.wait_for_selector("text=Active Projects", timeout=60000)
            log_result("Live Login", "PASS", "Successfully logged into Jugnoo CRM Cloud")
            
            # Check PDF Button
            if page.get_by_text("Download PDF").count() > 0:
                log_result("PDF Generation", "PASS", "Button visible on Cloud")
            else:
                log_result("PDF Generation", "WARNING", "Button not found (List might be empty)")

            browser.close()
            
        except Exception as e:
            log_result("Live Login Flow", "FAIL", f"Error: {str(e)}")

        # --- TEST 2: MOBILE VIEW (WHITE BARS CHECK) ---
        try:
            print("📱 Switching to iPhone Emulation...")
            iphone = p.devices['iPhone 12']
            # Headless is False here too so you can verify the bars yourself visually
            browser = p.chromium.launch(headless=False, slow_mo=1000)
            context = browser.new_context(**iphone)
            page = context.new_page()
            
            page.goto(APP_URL, timeout=90000)
            page.wait_for_selector("input[aria-label='Username']", timeout=90000)
            
            # Check Login Screen Background CSS
            bg_color = page.evaluate("window.getComputedStyle(document.querySelector('.stApp')).backgroundColor")
            
            # rgb(14, 17, 23) is the Hex #0E1117 (Dark Theme)
            if "14, 17, 23" in bg_color:
                log_result("Mobile Visuals", "PASS", "Background is Dark (No White Bars)")
            else:
                log_result("Mobile Visuals", "FAIL", f"Background detected as {bg_color} (Expected Dark)")
            
            browser.close()
        except Exception as e:
            log_result("Mobile Simulation", "FAIL", str(e))

    # --- GENERATE REPORT ---
    # encoding="utf-8" FIXES THE WINDOWS CRASH
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(f"""
        <html>
        <body style="font-family: sans-serif; background: #1e1e1e; color: #e0e0e0; padding: 20px;">
            <h1 style="border-bottom: 1px solid #444; padding-bottom: 10px;">🩺 Jugnoo CRM Health Report</h1>
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
    print(f"\n✅ Report generated: {os.path.abspath(REPORT_FILE)}")

if __name__ == "__main__":
    run_tests()
