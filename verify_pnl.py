import streamlit as st
from supabase import create_client
import pandas as pd

# Initialize Supabase Connection
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except Exception as e:
    print(f"Error connecting to Supabase: {e}")
    exit()

def verify_pnl():
    print("--- P&L INDEPENDENT VERIFICATION ---")
    
    # 1. Fetch Data
    try:
        clients_resp = supabase.table("clients").select("*").execute()
        purchases_resp = supabase.table("supplier_purchases").select("*").execute()
        settings_resp = supabase.table("settings").select("*").eq("id", 1).execute()
        
        clients = clients_resp.data if clients_resp else []
        purchases = purchases_resp.data if purchases_resp else []
        settings = settings_resp.data[0] if settings_resp and settings_resp.data else {}
        
    except Exception as e:
        print(f"Error fetching data: {e}")
        return

    # 2. Global Constants
    daily_labor_cost = float(settings.get('daily_labor_cost', 1000))
    print(f"Daily Labor Cost Setting: ₹{daily_labor_cost}")

    # 3. Calculate Global Metrics
    
    # A. Revenue (Total Collected)
    # Logic: Sum of 'final_settlement_amount' for ALL clients (or just closed? App uses all for 'Collected' usually, but let's check closed)
    # The app code uses: total_collected = df['final_settlement_amount'].fillna(0).sum() -> This implies ALL clients.
    total_revenue = sum(float(c.get('final_settlement_amount') or 0) for c in clients)
    
    # B. Material Expenses (Actual Cash Out)
    # Logic: Sum of 'cost' from supplier_purchases
    total_material_cost = sum(float(p.get('cost') or 0) for p in purchases)
    
    # C. Labor Expenses (Estimated/Allocated)
    # Logic: Sum of (days * daily_labor_cost) for CLOSED/WORK DONE projects only?
    # App logic: for idx, row in closed_df.iterrows()... total_labor_expense_cash += (days * daily_labor_cost)
    # So we should filter for closed clients.
    closed_clients = [c for c in clients if c.get('status') in ["Work Done", "Closed"]]
    
    total_labor_cost = 0.0
    for c in closed_clients:
        est = c.get('internal_estimate')
        if est:
            days = float(est.get('days', 0))
            total_labor_cost += (days * daily_labor_cost)
            
    # D. Total Expenses
    total_expenses = total_material_cost + total_labor_cost
    
    # E. Net Profit
    net_profit = total_revenue - total_expenses
    
    print("\n--- GLOBAL CASH FLOW METRICS ---")
    print(f"Total Revenue (Collected):   ₹{total_revenue:,.2f}")
    print(f"Total Material Cost (Cash):  ₹{total_material_cost:,.2f}")
    print(f"Total Labor Cost (Allocated):₹{total_labor_cost:,.2f}")
    print(f"Total Expenses:              ₹{total_expenses:,.2f}")
    print(f"Net Cash Profit:             ₹{net_profit:,.2f}")
    
    print("\n--- PROJECT-LEVEL PROFITABILITY (Sample of 5) ---")
    print(f"{'Client':<20} | {'Revenue':<10} | {'Est Cost':<10} | {'Profit':<10}")
    print("-" * 60)
    
    for c in closed_clients[:5]:
        name = c.get('name', 'Unknown')
        rev = float(c.get('final_settlement_amount') or 0)
        
        # Estimate Cost Calculation
        est = c.get('internal_estimate')
        est_mat_cost = 0.0
        est_labor_cost = 0.0
        
        if est:
            items = est.get('items', [])
            # Material Cost from Estimate items
            est_mat_cost = sum(float(i.get('Qty', 0)) * float(i.get('Base Rate', 0)) for i in items)
            # Labor Cost from Estimate days
            days = float(est.get('days', 0))
            est_labor_cost = days * daily_labor_cost
            
        est_total_cost = est_mat_cost + est_labor_cost
        proj_profit = rev - est_total_cost
        
        print(f"{name:<20} | ₹{rev:<9,.0f} | ₹{est_total_cost:<9,.0f} | ₹{proj_profit:<9,.0f}")

if __name__ == "__main__":
    verify_pnl()
