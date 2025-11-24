import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime

# ---------------------------
# 1. SETUP & CONNECTION
# ---------------------------
st.set_page_config(page_title="Jugnoo CRM", page_icon="🏗️", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stMetric {background-color: #f0f2f6; padding: 10px; border-radius: 5px;}
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
    defaults = {"part_margin": 0.15, "labor_margin": 0.20, "extra_margin": 0.05}
    try:
        response = run_query(supabase.table("settings").select("*"))
        if response and response.data:
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
    st.error("Connection Error. Check Secrets.")
    st.stop()

tab1, tab2, tab3, tab4 = st.tabs(["📋 Dashboard", "➕ New Client", "🧮 Estimator", "⚙️ Inventory & Settings"])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.subheader("Active Projects")
    response = run_query(supabase.table("clients").select("*").order("created_at", desc=True))
    
    if response and response.data:
        df = pd.DataFrame(response.data)
        display_cols = [c for c in ['name', 'status', 'phone', 'address'] if c in df.columns]
        st.dataframe(df[display_cols], use_container_width=True, hide_index=True)
        
        st.divider()
        
        # Client Management
        client_map = {c['name']: c for c in response.data}
        selected_client_name = st.selectbox("Select Client to Manage", list(client_map.keys()), index=None)
        
        if selected_client_name:
            client = client_map[selected_client_name]
            c1, c2 = st.columns(2)
            with c1:
                st.info(f"**Status:** {client['status']}")
                st.write(f"📞 {client['phone']}")
                if client.get('location'):
                    st.markdown(f"📍 [View Map]({client['location']})")
            
            with c2:
                new_status = st.selectbox("Update Status", 
                    ["Estimate Given", "Order Received", "Work In Progress", "Work Done", "Closed"],
                    key=f"status_{client['id']}"
                )
                if st.button("Update Status", key=f"btn_{client['id']}"):
                    run_query(supabase.table("clients").update({"status": new_status}).eq("id", client['id']))
                    st.success("Updated!")
                    st.rerun()

# --- TAB 2: NEW CLIENT ---
with tab2:
    st.subheader("Add New Client")
    with st.form("add_client"):
        c1, c2 = st.columns(2)
        name = c1.text_input("Client Name")
        phone = c2.text_input("Phone")
        address = st.text_area("Address")
        loc = st.text_input("Google Maps Link")
        
        if st.form_submit_button("Save Client", type="primary"):
            run_query(supabase.table("clients").insert({
                "name": name, "phone": phone, "address": address, "location": loc,
                "status": "Estimate Given", "created_at": datetime.now().isoformat()
            }))
            st.success("Client Added!")

# --- TAB 3: ESTIMATOR (GRANULAR CONTROL) ---
with tab3:
    st.subheader("Estimator Engine")
    
    # 1. Select Client
    all_clients = run_query(supabase.table("clients").select("id, name, internal_estimate").neq("status", "Closed"))
    client_dict = {c['name']: c for c in all_clients.data} if all_clients and all_clients.data else {}
    
    target_client_name = st.selectbox("Select Client", list(client_dict.keys()))
    
    if target_client_name:
        target_client = client_dict[target_client_name]
        st.divider()
        
        # 2. Load Existing Data into Session State
        # We use a specific key for session state based on the client ID to avoid mixing data
        ss_key = f"est_rows_{target_client['id']}"
        
        if ss_key not in st.session_state:
            # Attempt to load from DB first
            if target_client.get('internal_estimate') and isinstance(target_client['internal_estimate'], list):
                st.session_state[ss_key] = target_client['internal_estimate']
            else:
                st.session_state[ss_key] = []

        # 3. Add Item Form (Clean Form Style)
        inv_data = run_query(supabase.table("inventory").select("*"))
        if inv_data and inv_data.data:
            inv_map = {i['item_name']: i['base_rate'] for i in inv_data.data}
            
            st.write("#### 1. Add Items")
            with st.form("add_item_form", clear_on_submit=True):
                c1, c2, c3 = st.columns([3, 2, 1])
                item_name = c1.selectbox("Select Item", list(inv_map.keys()))
                qty = c2.number_input("Quantity", min_value=1.0, step=0.5)
                
                if st.form_submit_button("⬇️ Add to List"):
                    base_rate = inv_map[item_name]
                    # Append new item
                    st.session_state[ss_key].append({
                        "Item": item_name,
                        "Qty": qty,
                        "Base Rate": base_rate,
                        # We don't calculate total yet, we do it live below
                    })
                    st.rerun()

        # 4. Editable List (Granular Control)
        st.write("#### 2. Edit Estimate List")
        if st.session_state[ss_key]:
            # Fetch settings for live calculation
            s = get_settings()
            margin_multiplier = 1 + s['part_margin'] + s['labor_margin'] + s['extra_margin']
            
            # Prepare data for editor
            df = pd.DataFrame(st.session_state[ss_key])
            
            # Ensure columns exist
            if "Qty" not in df.columns: df["Qty"] = 1.0
            if "Base Rate" not in df.columns: df["Base Rate"] = 0.0
            
            # Calculate Live Totals based on Global Settings
            df["Unit Price (Calc)"] = df["Base Rate"] * margin_multiplier
            df["Total Price"] = df["Unit Price (Calc)"] * df["Qty"]
            
            # Show Data Editor (Allows Deleting Rows and Changing Qty)
            edited_df = st.data_editor(
                df,
                num_rows="dynamic", # Allows adding/deleting rows
                column_config={
                    "Item": st.column_config.TextColumn(disabled=True),
                    "Base Rate": st.column_config.NumberColumn(disabled=True, format="₹%.2f"),
                    "Unit Price (Calc)": st.column_config.NumberColumn(disabled=True, format="₹%.2f"),
                    "Total Price": st.column_config.NumberColumn(disabled=True, format="₹%.2f"),
                    "Qty": st.column_config.NumberColumn(min_value=0.1, step=0.5)
                },
                use_container_width=True,
                key=f"editor_{target_client['id']}"
            )
            
            # Update Session State with Edits
            # This allows the "Save" button to see the changes made in the table
            current_data = edited_df.to_dict(orient="records")
            
            # 5. Totals & Actions
            total_client = edited_df["Total Price"].sum()
            total_base = (edited_df["Base Rate"] * edited_df["Qty"]).sum()
            profit = total_client - total_base
            
            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("Base Cost", f"₹{total_base:,.2f}")
            c2.metric("Client Quote", f"₹{total_client:,.2f}")
            c3.metric("Projected Profit", f"₹{profit:,.2f}")
            
            if st.button("💾 Save Changes to Database", type="primary"):
                run_query(supabase.table("clients").update({
                    "internal_estimate": current_data
                }).eq("id", target_client['id']))
                st.toast("Estimate Updated Successfully!", icon="✅")
                
        else:
            st.info("List is empty. Add items above.")

# --- TAB 4: SETTINGS (SLIDERS) ---
with tab4:
    st.subheader("Global Profit Margins")
    s = get_settings()
    
    with st.form("margin_settings"):
        # SLIDERS RESTORED
        p = st.slider("Part Margin %", 0.0, 1.0, float(s['part_margin']), 0.01)
        l = st.slider("Labor Margin %", 0.0, 1.0, float(s['labor_margin']), 0.01)
        e = st.slider("Extra Margin %", 0.0, 1.0, float(s['extra_margin']), 0.01)
        
        st.write(f"**Total Markup:** {(p+l+e)*100:.0f}%")
        
        if st.form_submit_button("Update Global Margins"):
            run_query(supabase.table("settings").upsert({
                "id": 1, 
                "part_margin": p, "labor_margin": l, "extra_margin": e
            }))
            st.success("Margins Updated!")
            st.cache_resource.clear()

    st.divider()
    st.subheader("Inventory Management")
    
    with st.form("new_inv"):
        c1, c2 = st.columns([2, 1])
        new_name = c1.text_input("Item Name")
        new_rate = c2.number_input("Base Rate (₹)", min_value=0.0)
        if st.form_submit_button("Add Item"):
            run_query(supabase.table("inventory").insert({"item_name": new_name, "base_rate": new_rate}))
            st.success("Added!")
            st.rerun()
            
    # View Inventory
    inv = run_query(supabase.table("inventory").select("*").order("item_name"))
    if inv and inv.data:
        st.dataframe(pd.DataFrame(inv.data), use_container_width=True)