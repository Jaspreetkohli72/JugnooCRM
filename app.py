import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime

# ---------------------------
# 1. SETUP & CONNECTION
# ---------------------------
st.set_page_config(page_title="Jugnoo CRM", page_icon="🏗️", layout="wide")

# CSS: Targets ONLY the metric cards to fix the visibility issue
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Strictly target the metric container to fix white-on-white text */
    [data-testid="stMetric"] {
        background-color: #262730; /* Dark Gray Background */
        border: 1px solid #464b5f;
        padding: 15px;
        border-radius: 8px;
        color: white;
    }
    
    /* Ensure the label inside the metric (e.g. "Base Cost") is also visible */
    [data-testid="stMetricLabel"] {
        color: #b4b4b4; /* Light Gray for labels */
    }
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
    """Fetch settings with safety defaults."""
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
    st.error("Connection Error. Please check your API Secrets.")
    st.stop()

tab1, tab2, tab3, tab4 = st.tabs(["📋 Dashboard", "➕ New Client", "🧮 Estimator", "⚙️ Settings"])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.subheader("Active Projects")
    response = run_query(supabase.table("clients").select("*").order("created_at", desc=True))
    
    if response and response.data:
        df = pd.DataFrame(response.data)
        # Safe column selection for the summary table
        cols = [c for c in ['name', 'status', 'phone', 'address'] if c in df.columns]
        st.dataframe(df[cols], use_container_width=True, hide_index=True)
        
        st.divider()
        
        # Client Actions
        client_map = {c['name']: c for c in response.data}
        selected_client_name = st.selectbox("Select Client to Manage", list(client_map.keys()), index=None)
        
        if selected_client_name:
            client = client_map[selected_client_name]
            
            st.markdown("### 👤 Client Details")
            c1, c2 = st.columns([2, 1])
            
            with c1:
                st.write(f"**Name:** {client['name']}")
                st.write(f"**📞 Phone:** {client.get('phone', 'N/A')}")
                st.write(f"**📍 Address:** {client.get('address', 'N/A')}")
                if client.get('location'):
                    st.markdown(f"**🗺️ Location:** [Open in Google Maps]({client['location']})")
                st.write(f"**📅 Added On:** {client.get('created_at', '')[:10]}")
            
            with c2:
                st.info(f"**Current Status:** {client.get('status', 'Unknown')}")
                
                # Status Logic: Find current index to set default value correctly
                status_options = ["Estimate Given", "Order Received", "Work In Progress", "Work Done", "Closed"]
                try:
                    current_index = status_options.index(client.get('status'))
                except ValueError:
                    current_index = 0
                
                new_status = st.selectbox("Update Status", 
                    status_options,
                    index=current_index,
                    key=f"status_{client['id']}"
                )
                
                if st.button("Update Status", key=f"btn_{client['id']}"):
                    run_query(supabase.table("clients").update({"status": new_status}).eq("id", client['id']))
                    st.success("Status Updated!")
                    st.rerun()

            # Show Saved Estimate if exists
            if client.get('internal_estimate'):
                st.divider()
                st.subheader("📄 Saved Estimate")
                est_data = client['internal_estimate']
                
                # Handle data structure (Dict vs List)
                if isinstance(est_data, dict):
                    # New Format
                    items_df = pd.DataFrame(est_data.get('items', []))
                    margins = est_data.get('margins')
                    if margins:
                        st.caption(f"Using Custom Margins: P {margins['p']*100:.0f}% | L {margins['l']*100:.0f}% | E {margins['e']*100:.0f}%")
                else:
                    # Old Format (List only)
                    items_df = pd.DataFrame(est_data) if isinstance(est_data, list) else pd.DataFrame()

                if not items_df.empty:
                    # Check needed columns
                    if "Total Price" not in items_df.columns and "Total (Internal)" in items_df.columns:
                         items_df["Total Price"] = items_df["Total (Internal)"]
                    
                    if "Total Price" in items_df.columns:
                        st.dataframe(items_df, use_container_width=True)
                        st.metric("Total Quoted Amount", f"₹{items_df['Total Price'].sum():,.2f}")
                    else:
                        st.dataframe(items_df, use_container_width=True)
                else:
                    st.warning("Estimate data is empty.")

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
                "name": name, "phone": phone, "address": address, "location": loc,
                "status": "Estimate Given", "created_at": datetime.now().isoformat()
            }))
            st.success("Client Added!")

# --- TAB 3: ESTIMATOR ---
with tab3:
    st.subheader("Estimator Engine")
    
    # 1. Select Client
    all_clients = run_query(supabase.table("clients").select("id, name, internal_estimate").neq("status", "Closed"))
    client_dict = {c['name']: c for c in all_clients.data} if all_clients and all_clients.data else {}
    
    target_client_name = st.selectbox("Select Client", list(client_dict.keys()))
    
    if target_client_name:
        target_client = client_dict[target_client_name]
        
        # Load Logic
        saved_est = target_client.get('internal_estimate')
        loaded_items = []
        saved_margins = None
        
        if isinstance(saved_est, dict):
            loaded_items = saved_est.get('items', [])
            saved_margins = saved_est.get('margins')
        elif isinstance(saved_est, list):
            loaded_items = saved_est
            
        ss_key = f"est_items_{target_client['id']}"
        if ss_key not in st.session_state:
            st.session_state[ss_key] = loaded_items

        st.divider()
        
        # 2. Margins
        global_settings = get_settings()
        use_custom = st.checkbox("🛠️ Use Custom Margins for this Client", value=(saved_margins is not None))
        
        if use_custom:
            def_p = int((saved_margins['p'] if saved_margins else global_settings['part_margin']) * 100)
            def_l = int((saved_margins['l'] if saved_margins else global_settings['labor_margin']) * 100)
            def_e = int((saved_margins['e'] if saved_margins else global_settings['extra_margin']) * 100)
            
            st.write("**Custom Profit Settings (0-100%)**")
            mc1, mc2, mc3 = st.columns(3)
            cust_p = mc1.slider("Part %", 0, 100, def_p, key="cp") / 100
            cust_l = mc2.slider("Labor %", 0, 100, def_l, key="cl") / 100
            cust_e = mc3.slider("Extra %", 0, 100, def_e, key="ce") / 100
            
            active_margins = {'part_margin': cust_p, 'labor_margin': cust_l, 'extra_margin': cust_e}
        else:
            active_margins = global_settings

        st.divider()

        # 3. Add Item Form
        inv_data = run_query(supabase.table("inventory").select("*"))
        if inv_data and inv_data.data:
            inv_map = {i['item_name']: i['base_rate'] for i in inv_data.data}
            
            with st.form("add_item_form", clear_on_submit=True):
                c1, c2, c3 = st.columns([3, 2, 1])
                item_name = c1.selectbox("Select Item", list(inv_map.keys()))
                qty = c2.number_input("Quantity", min_value=1.0, step=0.5)
                
                if st.form_submit_button("⬇️ Add to List"):
                    st.session_state[ss_key].append({
                        "Item": item_name, "Qty": qty, "Base Rate": inv_map[item_name]
                    })
                    st.rerun()

        # 4. Editable Grid & Calc
        if st.session_state[ss_key]:
            margin_mult = 1 + active_margins['part_margin'] + active_margins['labor_margin'] + active_margins['extra_margin']
            
            df = pd.DataFrame(st.session_state[ss_key])
            if "Qty" not in df.columns: df["Qty"] = 1.0
            if "Base Rate" not in df.columns: df["Base Rate"] = 0.0
            
            # Live Calc
            df["Unit Price (Calc)"] = df["Base Rate"] * margin_mult
            df["Total Price"] = df["Unit Price (Calc)"] * df["Qty"]
            
            st.write("#### Estimate Items (Edit Qty or Delete Rows)")
            edited_df = st.data_editor(
                df,
                num_rows="dynamic",
                column_config={
                    "Item": st.column_config.TextColumn(disabled=True),
                    "Base Rate": st.column_config.NumberColumn(disabled=True, format="₹%.2f"),
                    "Unit Price (Calc)": st.column_config.NumberColumn(disabled=True, format="₹%.2f"),
                    "Total Price": st.column_config.NumberColumn(disabled=True, format="₹%.2f"),
                    "Qty": st.column_config.NumberColumn(min_value=0.1, step=0.5)
                },
                use_container_width=True,
                key=f"edit_{target_client['id']}"
            )
            
            current_items = edited_df.to_dict(orient="records")
            
            total_client = edited_df["Total Price"].sum()
            total_base = (edited_df["Base Rate"] * edited_df["Qty"]).sum()
            profit = total_client - total_base
            
            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("Base Cost", f"₹{total_base:,.0f}")
            c2.metric("Client Quote", f"₹{total_client:,.0f}")
            c3.metric("Projected Profit", f"₹{profit:,.0f}", delta="Profit")
            
            if st.button("💾 Save Estimate", type="primary"):
                save_obj = {
                    "items": current_items,
                    "margins": {
                        'p': active_margins['part_margin'],
                        'l': active_margins['labor_margin'],
                        'e': active_margins['extra_margin']
                    } if use_custom else None
                }
                run_query(supabase.table("clients").update({
                    "internal_estimate": save_obj
                }).eq("id", target_client['id']))
                st.toast("Estimate Saved!", icon="✅")

# --- TAB 4: SETTINGS ---
with tab4:
    st.subheader("Global Settings")
    s = get_settings()
    
    with st.form("margin_settings"):
        st.write("**Global Profit Defaults (0-100%)**")
        
        c1, c2, c3 = st.columns(3)
        
        p_curr = int(s.get('part_margin', 0.15) * 100)
        l_curr = int(s.get('labor_margin', 0.20) * 100)
        e_curr = int(s.get('extra_margin', 0.05) * 100)
        
        p = c1.slider("Part Margin %", 0, 100, p_curr)
        l = c2.slider("Labor Margin %", 0, 100, l_curr)
        e = c3.slider("Extra Margin %", 0, 100, e_curr)
        
        if st.form_submit_button("Update Global Defaults"):
            run_query(supabase.table("settings").upsert({
                "id": 1, 
                "part_margin": p / 100.0, 
                "labor_margin": l / 100.0, 
                "extra_margin": e / 100.0
            }))
            st.success("Settings Saved!")
            st.cache_resource.clear()

    st.divider()
    st.subheader("Inventory")
    
    with st.form("inv_add"):
        c1, c2 = st.columns([2, 1])
        new_item = c1.text_input("Item Name")
        rate = c2.number_input("Base Rate (₹)", min_value=0.0)
        if st.form_submit_button("Add Item"):
            run_query(supabase.table("inventory").insert({"item_name": new_item, "base_rate": rate}))
            st.success("Added")
            st.rerun()
            
    inv = run_query(supabase.table("inventory").select("*").order("item_name"))
    if inv and inv.data:
        st.dataframe(pd.DataFrame(inv.data), use_container_width=True)
