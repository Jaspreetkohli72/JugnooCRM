import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
import time
from fpdf import FPDF
from streamlit_js_eval import get_geolocation

# ---------------------------
# 1. SETUP & CONNECTION
# ---------------------------
st.set_page_config(page_title="Jugnoo CRM", page_icon="🏗️", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stMetric"] {
        background-color: #262730;
        border: 1px solid #464b5f;
        padding: 15px;
        border-radius: 8px;
        color: white;
    }
    [data-testid="stMetricLabel"] { color: #b4b4b4; }
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
# 2. AUTH & HELPERS
# ---------------------------
def check_login(username, password):
    try:
        res = supabase.table("users").select("*").eq("username", username).eq("password", password).execute()
        return len(res.data) > 0
    except:
        return False

def login_page():
    st.title("🔒 Jugnoo CRM Login")
    if "logged_in" not in st.session_state: st.session_state.logged_in = False
    if st.session_state.logged_in: return

    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        with st.form("login"):
            user = st.text_input("Username")
            pwd = st.text_input("Password", type="password")
            if st.form_submit_button("Sign In", type="primary"):
                if check_login(user, pwd):
                    st.session_state.logged_in = True
                    st.session_state.username = user
                    st.rerun()
                else:
                    st.error("Invalid Credentials")
    st.stop()

login_page()

def run_query(query_func):
    try:
        return query_func.execute()
    except:
        return None

def get_settings():
    defaults = {"part_margin": 0.15, "labor_margin": 0.20, "extra_margin": 0.05, "daily_labor_cost": 1000.0}
    try:
        response = run_query(supabase.table("settings").select("*"))
        if response and response.data:
            db_data = response.data[0]
            return {k: db_data.get(k, v) for k, v in defaults.items()}
    except:
        pass
    return defaults

def create_pdf(client_name, items, labor_days, labor_total, grand_total):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Jugnoo - Estimate", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"Client: {client_name}", ln=True)
    pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d')}", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(100, 10, "Item", 1)
    pdf.cell(30, 10, "Qty", 1)
    pdf.cell(60, 10, "Amount", 1)
    pdf.ln()
    pdf.set_font("Arial", '', 12)
    for item in items:
        pdf.cell(100, 10, str(item['Item']), 1)
        pdf.cell(30, 10, str(item['Qty']), 1)
        pdf.cell(60, 10, f"{item['Total Price']:.2f}", 1)
        pdf.ln()
    pdf.ln(5)
    pdf.cell(130, 10, f"Labor / Installation ({labor_days} Days)", 1)
    pdf.cell(60, 10, f"{labor_total:.2f}", 1)
    pdf.ln()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(130, 10, "Grand Total", 1)
    pdf.cell(60, 10, f"{grand_total:.2f}", 1)
    return pdf.output(dest='S').encode('latin-1')

# ---------------------------
# 3. MAIN UI
# ---------------------------
st.title("🏗️ Jugnoo CRM")
st.sidebar.write(f"👤 **{st.session_state.username}**")
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

if not supabase: st.stop()

tab1, tab2, tab3, tab4 = st.tabs(["📋 Dashboard", "➕ New Client", "🧮 Estimator", "⚙️ Settings"])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.subheader("Active Projects")
    response = run_query(supabase.table("clients").select("*").order("created_at", desc=True))
    
    if response and response.data:
        df = pd.DataFrame(response.data)
        cols = [c for c in ['name', 'status', 'phone', 'address'] if c in df.columns]
        st.dataframe(df[cols], use_container_width=True, hide_index=True)
        
        st.divider()
        
        # Key fixed: Prevents reset on interaction
        client_map = {c['name']: c for c in response.data}
        selected_client_name = st.selectbox("Select Client to Manage", list(client_map.keys()), index=None, key="dash_client_select")
        
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
                status_options = ["Estimate Given", "Order Received", "Work In Progress", "Work Done", "Closed"]
                # Find index safely
                try:
                    idx = status_options.index(client.get('status'))
                except:
                    idx = 0
                    
                new_status = st.selectbox("Update Status", status_options, index=idx, key=f"status_{client['id']}")
                
                if st.button("Update Status", key=f"btn_{client['id']}"):
                    run_query(supabase.table("clients").update({"status": new_status}).eq("id", client['id']))
                    st.success("Status Updated!")
                    time.sleep(0.5)
                    st.rerun()

            if client.get('internal_estimate'):
                st.divider()
                st.subheader("📄 Saved Estimate")
                est_data = client['internal_estimate']
                if isinstance(est_data, dict):
                    items_df = pd.DataFrame(est_data.get('items', []))
                    margins = est_data.get('margins')
                    if margins: st.caption(f"Custom Margins Applied: P {margins['p']*100:.0f}%")
                else:
                    items_df = pd.DataFrame(est_data) if isinstance(est_data, list) else pd.DataFrame()

                if not items_df.empty:
                    if "Total Price" not in items_df.columns and "Total (Internal)" in items_df.columns:
                         items_df["Total Price"] = items_df["Total (Internal)"]
                    st.dataframe(items_df, use_container_width=True)
                    if "Total Price" in items_df.columns:
                        st.metric("Total Quoted Amount", f"₹{items_df['Total Price'].sum():,.2f}")

# --- TAB 2: NEW CLIENT (WITH GPS) ---
with tab2:
    st.subheader("Add New Client")
    
    # GPS Logic
    loc_button = get_geolocation()
    if loc_button:
        lat = loc_button['coords']['latitude']
        long = loc_button['coords']['longitude']
        st.session_state['nc_loc'] = f"https://maps.google.com/?q={lat},{long}"
        
    # Form using Session State keys to allow GPS update
    with st.form("add_client"):
        c1, c2 = st.columns(2)
        name = st.text_input("Client Name", key="nc_name")
        phone = st.text_input("Phone Number", key="nc_phone")
        address = st.text_area("Address", key="nc_addr")
        
        # Location field (Auto-filled by GPS)
        if 'nc_loc' not in st.session_state: st.session_state['nc_loc'] = ""
        loc = st.text_input("Google Maps Link (Click GPS button above to auto-fill)", key="nc_loc")
        
        if st.form_submit_button("Save Client", type="primary"):
            run_query(supabase.table("clients").insert({
                "name": name, "phone": phone, "address": address, "location": loc,
                "status": "Estimate Given", "created_at": datetime.now().isoformat()
            }))
            st.success("Client Added!")
            # Clear form
            for key in ['nc_name', 'nc_phone', 'nc_addr', 'nc_loc']:
                if key in st.session_state: del st.session_state[key]
            st.rerun()

# --- TAB 3: ESTIMATOR ---
with tab3:
    st.subheader("Estimator Engine")
    all_clients = run_query(supabase.table("clients").select("id, name, internal_estimate").neq("status", "Closed"))
    client_dict = {c['name']: c for c in all_clients.data} if all_clients and all_clients.data else {}
    
    # Key fixed: Prevents reset
    target_client_name = st.selectbox("Select Client", list(client_dict.keys()), key="est_client_select")
    
    if target_client_name:
        target_client = client_dict[target_client_name]
        saved_est = target_client.get('internal_estimate')
        loaded_items = []
        saved_margins = None
        saved_days = 1.0
        
        if isinstance(saved_est, dict):
            loaded_items = saved_est.get('items', [])
            saved_margins = saved_est.get('margins')
            saved_days = saved_est.get('days', 1.0)
        elif isinstance(saved_est, list):
            loaded_items = saved_est
            
        ss_key = f"est_items_{target_client['id']}"
        if ss_key not in st.session_state: st.session_state[ss_key] = loaded_items

        st.divider()
        global_settings = get_settings()
        use_custom = st.checkbox("🛠️ Use Custom Margins", value=(saved_margins is not None), key="cust_check")
        
        if use_custom:
            def_p = int((saved_margins['p'] if saved_margins else global_settings['part_margin']) * 100)
            def_l = int((saved_margins['l'] if saved_margins else global_settings['labor_margin']) * 100)
            def_e = int((saved_margins['e'] if saved_margins else global_settings['extra_margin']) * 100)
            
            mc1, mc2, mc3 = st.columns(3)
            cust_p = mc1.slider("Part %", 0, 100, def_p, key="cp") / 100
            cust_l = mc2.slider("Labor %", 0, 100, def_l, key="cl") / 100
            cust_e = mc3.slider("Extra %", 0, 100, def_e, key="ce") / 100
            active_margins = {'part_margin': cust_p, 'labor_margin': cust_l, 'extra_margin': cust_e}
        else:
            active_margins = global_settings
            
        days_to_complete = st.slider("⏳ Days to Complete", 0.5, 30.0, float(saved_days), 0.5, key="days_slider")

        st.divider()
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

        if st.session_state[ss_key]:
            margin_mult = 1 + active_margins['part_margin'] + active_margins['labor_margin'] + active_margins['extra_margin']
            df = pd.DataFrame(st.session_state[ss_key])
            if "Qty" not in df.columns: df["Qty"] = 1.0
            if "Base Rate" not in df.columns: df["Base Rate"] = 0.0
            
            df["Unit Price (Calc)"] = df["Base Rate"] * margin_mult
            df["Total Price"] = df["Unit Price (Calc)"] * df["Qty"]
            
            st.write("#### Estimate Items")
            edited_df = st.data_editor(
                df, num_rows="dynamic", use_container_width=True, key=f"edit_{target_client['id']}",
                column_config={
                    "Item": st.column_config.TextColumn(disabled=True),
                    "Base Rate": st.column_config.NumberColumn(disabled=True, format="₹%.2f"),
                    "Total Price": st.column_config.NumberColumn(disabled=True, format="₹%.2f"),
                    "Qty": st.column_config.NumberColumn(min_value=0.1, step=0.5)
                }
            )
            
            current_items = edited_df.to_dict(orient="records")
            material_total_client = edited_df["Total Price"].sum()
            material_base = (edited_df["Base Rate"] * edited_df["Qty"]).sum()
            labor_cost_client = days_to_complete * float(global_settings.get('daily_labor_cost', 1000))
            grand_total = material_total_client + labor_cost_client
            profit = grand_total - (material_base + (labor_cost_client * 0.5))
            
            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("Material", f"₹{material_total_client:,.0f}")
            c2.metric("Labor", f"₹{labor_cost_client:,.0f}")
            c3.metric("Grand Total", f"₹{grand_total:,.0f}")
            
            col_save, col_pdf = st.columns(2)
            if col_save.button("💾 Save Estimate", type="primary"):
                save_obj = {
                    "items": current_items, "days": days_to_complete,
                    "margins": {'p': active_margins['part_margin'], 'l': active_margins['labor_margin'], 'e': active_margins['extra_margin']} if use_custom else None
                }
                run_query(supabase.table("clients").update({"internal_estimate": save_obj}).eq("id", target_client['id']))
                st.toast("Saved!", icon="✅")
                
            pdf_bytes = create_pdf(target_client_name, current_items, days_to_complete, labor_cost_client, grand_total)
            col_pdf.download_button("📄 Download PDF", data=pdf_bytes, file_name=f"Estimate_{target_client_name}.pdf", mime="application/pdf")

# --- TAB 4: SETTINGS ---
with tab4:
    st.subheader("Global Profit Defaults")
    s = get_settings()
    with st.form("margin_settings"):
        c1, c2, c3 = st.columns(3)
        p = c1.slider("Part %", 0, 100, int(s.get('part_margin', 0.15) * 100))
        l = c2.slider("Labor %", 0, 100, int(s.get('labor_margin', 0.20) * 100))
        e = c3.slider("Extra %", 0, 100, int(s.get('extra_margin', 0.05) * 100))
        lc = st.number_input("Daily Labor Charge (₹)", value=float(s.get('daily_labor_cost', 1000.0)), step=100.0)
        if st.form_submit_button("Update Defaults"):
            run_query(supabase.table("settings").upsert({
                "id": 1, "part_margin": p/100, "labor_margin": l/100, "extra_margin": e/100, "daily_labor_cost": lc
            }))
            st.success("Saved!")
            st.cache_resource.clear()

    st.divider()
    st.subheader("Inventory")
    with st.form("inv_add"):
        c1, c2 = st.columns([2, 1])
        new_item = c1.text_input("Item Name")
        rate = c2.number_input("Rate", min_value=0.0)
        if st.form_submit_button("Add Item"):
            run_query(supabase.table("inventory").insert({"item_name": new_item, "base_rate": rate}))
            st.success("Added")
            st.rerun()
    inv = run_query(supabase.table("inventory").select("*").order("item_name"))
    if inv and inv.data:
        st.dataframe(pd.DataFrame(inv.data), use_container_width=True)