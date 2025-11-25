import time
from playwright.sync_api import sync_playwright
import os

# CONFIGURATION
APP_URL = "https://jugnoocrm.streamlit.app/"
USERNAME = "Jaspreet"
PASSWORD = "CRMJugnoo@123"
REPORT_FILE = "full_test_report.html"

results = []

def log_result(test_name, status, message=""):
    color = "#4ade80" if status == "PASS" else "#f87171"
    results.append(f"<tr style='color:{color}; border-bottom: 1px solid #333;'><td>{test_name}</td><td><b>{status}</b></td><td>{message}</td></tr>")
    print(f"[{status}] {test_name}: {message}")

def run_tests():
    print(f"🚀 STARTING COMPREHENSIVE TEST SUITE ON: {APP_URL}")
    
    with sync_playwright() as p:
        # Grant geolocation permissions for the GPS test
        browser = p.chromium.launch(headless=False, slow_mo=1500)
        context = browser.new_context(permissions=['geolocation'], geolocation={'latitude': 28.6139, 'longitude': 77.2090})
        page = context.new_page()
        
        try:
            # ---------------------------------------------------------
            # PHASE 1: LOAD & LOGIN
            # ---------------------------------------------------------
            print("Phase 1: Initialization & Login...")
            page.goto(APP_URL, timeout=180000)
            
            # Wake up handling
            try:
                wake_btn = page.get_by_text("Yes, get this app back up!")
                if wake_btn.is_visible(timeout=5000):
                    print("💤 Waking up app...")
                    wake_btn.click()
                    time.sleep(30)
            except: pass

            # Locate Iframe
            iframe = page.frame_locator('iframe[title="streamlitApp"]')
            iframe.get_by_role("textbox", name="Username").wait_for(timeout=120000)
            
            # Login
            iframe.get_by_role("textbox", name="Username").fill(USERNAME)
            iframe.get_by_role("textbox", name="Password").fill(PASSWORD)
            iframe.get_by_role("button", name="Login").click()
            
            # Verify Dashboard Load
            iframe.get_by_text("Active Projects").wait_for(timeout=60000)
            log_result("Authentication", "PASS", "Login successful & Dashboard loaded")

            # ---------------------------------------------------------
            # PHASE 2: SETTINGS & INVENTORY (Add Item)
            # ---------------------------------------------------------
            print("Phase 2: Settings & Inventory...")
            # Switch Tab
            iframe.get_by_role("tab", name="Settings").click()
            time.sleep(2)
            
            # Verify Sliders Exist
            if iframe.locator("div[data-testid='stSlider']").count() >= 3:
                log_result("Settings UI", "PASS", "Profit Margin Sliders detected")
            else:
                log_result("Settings UI", "FAIL", "Profit Sliders missing")

            # Add Inventory Item
            test_item_name = f"Test_Item_{int(time.time())}"
            iframe.get_by_label("Item Name").fill(test_item_name)
            iframe.get_by_label("Rate").fill("500")
            iframe.get_by_role("button", name="Add Item").click()
            
            # Verify Table Update (Look for the text in the dataframe)
            time.sleep(3) # Wait for reload
            if iframe.get_by_text(test_item_name).count() > 0:
                log_result("Inventory CRUD", "PASS", f"Added item '{test_item_name}'")
            else:
                log_result("Inventory CRUD", "FAIL", "Item not found in table after add")

            # ---------------------------------------------------------
            # PHASE 3: NEW CLIENT (Create & GPS)
            # ---------------------------------------------------------
            print("Phase 3: Create Client...")
            iframe.get_by_role("tab", name="New Client").click()
            time.sleep(2)
            
            # Test GPS Button
            # Note: We look for the toggle/button text specifically
            if iframe.get_by_text("Get Current Location").is_visible():
                iframe.get_by_text("Get Current Location").click()
                time.sleep(3) # Wait for JS eval
                # Check if success message appears
                if iframe.get_by_text("Location Captured").count() > 0:
                    log_result("GPS Function", "PASS", "Geolocation captured successfully")
                else:
                    log_result("GPS Function", "WARNING", "GPS button clicked but no confirmation (might need permission)")
            
            # Create Client
            client_name = "TEST_BOT_CLIENT"
            iframe.get_by_label("Client Name").fill(client_name)
            iframe.get_by_label("Phone Number").fill("9999999999")
            iframe.get_by_label("Address").fill("123 Automated Test Lane")
            iframe.get_by_role("button", name="Create Client").click()
            
            # Wait for success message
            iframe.get_by_text(f"Client {client_name} Added!").wait_for()
            log_result("Client CRUD", "PASS", "Client created successfully")

            # ---------------------------------------------------------
            # PHASE 4: ESTIMATOR (Generate Quote)
            # ---------------------------------------------------------
            print("Phase 4: Estimator Engine...")
            iframe.get_by_role("tab", name="Estimator").click()
            
            # Wait for the "Select Client" label to be visible before interacting
            iframe.get_by_text("Select Client", exact=True).wait_for()
            
            # Select Client (Streamlit Selectbox is tricky, we click it then type)
            # Find the Selectbox for "Select Client"
            print("Selecting client...")
            # Click the first dropdown (Client Select)
            iframe.locator("div[data-testid='stSelectbox']").first.click() 
            time.sleep(1)
            # Click the client name in the dropdown list
            iframe.get_by_text(client_name).first.click()
            time.sleep(3) # Wait for load
            
            # Enable Custom Margins
            if iframe.get_by_text("Use Custom Margins").count() > 0:
                iframe.get_by_text("Use Custom Margins").click()
                log_result("Estimator UI", "PASS", "Custom Margins toggle works")
            
            # Add Item to Estimate
            # Select the Item dropdown (Usually the second one now)
            print("Adding item...")
            iframe.locator("div[data-testid='stSelectbox']").nth(1).click()
            time.sleep(1)
            iframe.get_by_text(test_item_name).first.click() # Select the item we made earlier
            
            iframe.get_by_label("Quantity").fill("2")
            iframe.get_by_role("button", name="Add to List").click() # Assuming button is 'Add to List' or 'Add'
            time.sleep(3)
            
            # Verify Math (500 rate * 2 qty = 1000 base + margins)
            # We just check if the metric cards appear
            if iframe.get_by_text("Grand Total").count() > 0:
                log_result("Calculation", "PASS", "Metrics calculated and displayed")
            else:
                log_result("Calculation", "FAIL", "Metrics not visible")

            # Save Estimate
            iframe.get_by_role("button", name="Save Estimate").click()
            iframe.get_by_text("Saved!").wait_for()
            log_result("Database Write", "PASS", "Estimate saved to database")

            # ---------------------------------------------------------
            # PHASE 5: DASHBOARD (Verification & PDF)
            # ---------------------------------------------------------
            print("Phase 5: Dashboard Verification...")
            iframe.get_by_role("tab", name="Dashboard").click()
            time.sleep(3)
            
            # Select the client in Dashboard
            iframe.locator("div[data-testid='stSelectbox']").first.click()
            iframe.get_by_text(client_name).first.click()
            time.sleep(3)
            
            # Verify Data loaded
            if iframe.get_by_text("123 Automated Test Lane").count() > 0:
                log_result("Dashboard Read", "PASS", "Client details loaded correctly")
            else:
                log_result("Dashboard Read", "FAIL", "Client details missing")
                
            # Verify PDF Button Exists
            if iframe.get_by_text("Download PDF").count() > 0:
                log_result("PDF Logic", "PASS", "Download PDF button is generated and visible")
                
            # Test Navigate Button
            if iframe.get_by_text("Navigate to Site").count() > 0:
                log_result("Navigation", "PASS", "Navigate button visible")

            # Test Edit Details
            iframe.get_by_label("Name", exact=True).fill(client_name + "_EDITED")
            iframe.get_by_role("button", name="Save Changes").click()
            iframe.get_by_text("Details Updated!").wait_for()
            log_result("Client Update", "PASS", "Client details edited successfully")

            # ---------------------------------------------------------
            # PHASE 6: LOGOUT
            # ---------------------------------------------------------
            print("Phase 6: Cleanup...")
            iframe.get_by_role("button", name="Logout").click()
            # Verify back to login screen
            iframe.get_by_role("button", name="Login").wait_for()
            log_result("Session", "PASS", "Logout successful")

        except Exception as e:
            print(f"❌ CRITICAL FAILURE: {e}")
            log_result("CRITICAL FAILURE", "FAIL", str(e))
            try: page.screenshot(path="failure_screenshot.png")
            except: pass

        browser.close()

    # --- SAVE REPORT ---
    try:
        with open(REPORT_FILE, "w", encoding="utf-8") as f:
            f.write(f"""
            <html>
            <body style="font-family: sans-serif; background: #0e1117; color: #e0e0e0; padding: 30px;">
                <div style="max-width: 800px; margin: auto;">
                    <h1 style="border-bottom: 1px solid #333; padding-bottom: 10px; color: #ff4b4b;">🩺 Jugnoo CRM Deep-Dive Report</h1>
                    <p><b>Date:</b> {time.ctime()}</p>
                    <br>
                    <table border="0" cellpadding="15" cellspacing="0" style="width: 100%; background: #262730; border-radius: 8px;">
                        <tr style="background: #333; text-align: left;"><th>Test Category</th><th>Status</th><th>Details</th></tr>
                        {''.join(results)}
                    </table>
                </div>
            </body>
            </html>
            """)
        print(f"\n✅ FULL REPORT GENERATED: {os.path.abspath(REPORT_FILE)}")
    except Exception as e:
        print(f"Error saving report: {e}")

if __name__ == "__main__":
    run_tests()