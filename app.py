import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime

# ---------------------------
# 1. SETUP & CONNECTION
# ---------------------------
st.set_page_config(page_title="Jugnoo CRM", page_icon="🏗️", layout="wide")

# Hide Streamlit footer
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

@st.cache_resource(ttl="1h")
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except:
        return None

supabase = init_connection()

# ---------------------------
# 2. HELPER FUNCTIONS
# ---------------------------
def run_query(query_func):
    try:
        return query_func.execute()
    except Exception as e:
        return None

def get_settings():
    """
    Fetches settings but provides 'Safety Net' defaults 
    so the app NEVER crashes even if DB is empty.
    """
    defaults = {
        "part_margin": 0.15, 
        "labor_margin": 0.20, 
        "extra_margin": 0.05
    }
    
    try:
        response = run_query(supabase.table("settings").select("*"))
        if response and response.data:
            # Combine defaults with actual data (overwrites defaults if key exists)
            db_data = response.data[0]
            return {k: db_data.get(k, v) for k, v in defaults.items()}
    except:
        pass
    
    return defaults

# ---------------------------
# 3. UI TABS
# ---------------------------
st.title("🏗️ Jugnoo CRM")

if not supabase:
    st.error("Database connection failed. Check your secrets.")
    st.stop()

tab1, tab2, tab3, tab4 = st.tabs(["📋 Dashboard", "➕ New Client", "🧮 Estimator", "⚙️ Inventory & Settings"])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.subheader("Active Projects")
    
    # Fetch Clients
    response = run_query(supabase.table("clients").select("*").order("created_at", desc=True))
    
    if response and response.data:
        clients = response.data
        
        # Summary Table
        df = pd.DataFrame(clients)
        # Safe column selection
        cols = [c for c in ['name', 'status', 'phone', 'address'] if c in df.columns]
        st.dataframe(df[cols], use_container_width=True, hide_index=True)
        
        st.divider()
        
        # Manage Specific Client
        client_names = [c['name'] for c in clients]
        selected_name = st.selectbox("Select Client to Manage", client_names, index=None)
        
        if selected_name:
            # Get client data safely
            client = next((c for c in clients if c['name'] == selected_name), None)
            
            c1, c2 = st.columns(2)
            with c1:
                st.info(f"**Current Status:** {client.get('status', 'Unknown')}")
                st.write(f"📞 {client.get('phone', 'N/A')}")
                st.write(f"📍 {client.get('address', 'N/A')}")
                
                if client.get('location'):
                    st.markdown(f"[Open in Google Maps]({client['location']})")
            
            with c2:
                new_status = st.selectbox("Update Status", 
                    ["Estimate Given", "Order Received", "Work In Progress", "Work Done", "Closed"],
                    key=f"status_{client['id']}"
                )
                if st.button("Update Status", key=f"btn_{client['id']}"):
                    run_query(supabase.table("clients").update({"status": new_status}).eq("id", client['id']))
                    st.success("Status Updated!")
                    st.rerun()

            # Show Estimate
            if client.get('internal_estimate'):
                st.write("---")
                st.write("### 📄 Saved Estimate")
                est_data = client['internal_estimate']
                if isinstance(est_data, list) and len(est_data) > 0:
                    st.dataframe(pd.DataFrame(est_data), use_container_width=True)
                else:
                    st.warning("Estimate is empty.")

# --- TAB 2: NEW CLIENT ---
with tab2:
    st.subheader("Add New Client")
    with st.form("add_client"):
        c1, c2 = st.columns(2)
        name = c1.text_input("Client Name")
        phone = c2.text_input("Phone Number")
        address = st.text_area("Address")
        loc = st.text_input("Google Maps Link")
        
        if st.form_submit_button("Save Client", type="primary"):
            run_query(supabase.table("clients").insert({
                "name": name,
                "phone": phone,
                "address": address,
                "location": loc,
                "status": "Estimate Given",
                "created_at": datetime.now().isoformat()
            }))
            st.success(f"Client {name} added!")

# --- TAB 3: ESTIMATOR (FIXED UI) ---
with tab3:
    st.subheader("Create Estimate")
    
    # Initialize Session State list
    if "est_rows" not in st.session_state:
        st.session_state.est_rows = []

    # 1. Select Client
    all_clients = run_query(supabase.table("clients").select("id, name").neq("status", "Closed"))
    client_dict = {c['name']: c['id'] for c in all_clients.data} if all_clients and all_clients.data else {}
    
    target_client = st.selectbox("Select Client", list(client_dict.keys()), key="est_select")
    
    if target_client:
        st.divider()
        
        # 2. Add Item Form (The UI you requested)
        inv_data = run_query(supabase.table("inventory").select("*"))
        
        if inv_data and inv_data.data:
            inv_map = {i['item_name']: i['base_rate'] for i in inv_data.data}
            
            with st.form("add_item_form", clear_on_submit=True):
                c1, c2 = st.columns([3, 1])
                item_name = c1.selectbox("Select Item", list(inv_map.keys()))
                qty = c2.number_input("Quantity", min_value=1.0, step=0.5)
                
                # Calculate button inside form
                if st.form_submit_button("⬇️ Add to Estimate"):
                    base_rate = inv_map[item_name]
                    s = get_settings()
                    
                    # Calculate Internal Cost
                    my_cost = base_rate * (1 + s['part_margin'] + s['labor_margin'] + s['extra_margin'])
                    
                    st.session_state.est_rows.append({
                        "Item": item_name,
                        "Qty": qty,
                        "Base Rate": base_rate,
                        "My Cost": my_cost,
                        "Total (Internal)": my_cost * qty
                    })
                    st.rerun()

        # 3. Show List
        if st.session_state.est_rows:
            st.write("### Draft Items")
            df_est = pd.DataFrame(st.session_state.est_rows)
            st.dataframe(df_est, use_container_width=True)
            
            # Totals
            total_internal = df_est['Total (Internal)'].sum()
            total_base = (df_est['Base Rate'] * df_est['Qty']).sum()
            profit = total_internal - total_base
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Base Cost", f"₹{total_base:,.0f}")
            c2.metric("Client Quote", f"₹{total_internal:,.0f}")
            c3.metric("Your Profit", f"₹{profit:,.0f}")
            
            col1, col2 = st.columns([1, 4])
            if col1.button("Clear List"):
                st.session_state.est_rows = []
                st.rerun()
                
            if col2.button("💾 Save Estimate to Database", type="primary"):
                cid = client_dict[target_client]
                run_query(supabase.table("clients").update({
                    "internal_estimate": st.session_state.est_rows
                }).eq("id", cid))
                st.success("Saved!")

# --- TAB 4: SETTINGS ---
with tab4:
    st.subheader("Global Margins")
    
    # Safe Get Settings
    s = get_settings()
    
    with st.form("global_margins"):
        c1, c2, c3 = st.columns(3)
        # Float conversion ensures type safety
        p = c1.number_input("Part Margin %", value=float(s['part_margin']), step=0.01)
        l = c2.number_input("Labor Margin %", value=float(s['labor_margin']), step=0.01)
        e = c3.number_input("Extra Margin %", value=float(s['extra_margin']), step=0.01)
        
        if st.form_submit_button("Update Margins"):
            # Use upsert to handle first-time creation
            run_query(supabase.table("settings").upsert({
                "id": 1, 
                "part_margin": p, 
                "labor_margin": l, 
                "extra_margin": e
            }))
            st.success("Margins Updated!")
            st.cache_resource.clear() # Clear cache to refresh settings

    st.divider()
    st.subheader("Inventory List")
    
    with st.form("add_inv_item"):
        c1, c2 = st.columns([2, 1])
        new_item = c1.text_input("New Item Name")
        new_rate = c2.number_input("Base Rate", min_value=0.0)
        
        if st.form_submit_button("Add to Inventory"):
            run_query(supabase.table("inventory").insert({
                "item_name": new_item, "base_rate": new_rate
            }))
            st.success("Item Added!")
            st.rerun()
            
    # View Inventory
    inv_resp = run_query(supabase.table("inventory").select("*").order("item_name"))
    if inv_resp and inv_resp.data:
        st.dataframe(pd.DataFrame(inv_resp.data), use_container_width=True)
