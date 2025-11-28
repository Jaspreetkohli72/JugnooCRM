import streamlit as st
from supabase import create_client
from utils import helpers, auth
from utils.helpers import create_pdf

from datetime import datetime, timedelta
import time
import pandas as pd
import math

from streamlit_js_eval import get_geolocation
import altair as alt
import extra_streamlit_components as stx

# ---------------------------
# 1. SETUP & CONNECTION
# ---------------------------
st.set_page_config(page_title="Jugnoo", page_icon="🏗️", layout="wide")

# === START OF CRITICAL CACHE FIX ===
if st.session_state.get('cache_fix_needed', True):
    st.cache_resource.clear()
    st.session_state.cache_fix_needed = False
# === END OF CRITICAL CACHE FIX ===

# Initialize Session State
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ""

st.markdown("""
    <style>
    .stApp { background-color: #0E1117 !important; }
    header[data-testid="stHeader"] { background-color: #0E1117 !important; }
    [data-testid="stAppViewContainer"] {
        background-color: #0e1117;
    }
    [data-testid="stSidebar"] {
        background-color: #0e1117;
    }
    html, body {
        background-color: #0E1117;
        height: 100%;
        margin: 0;
    }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    [data-testid="stMetric"] {
        background-color: #262730;
        border: 1px solid #464b5f;
        padding: 15px;
        border-radius: 8px;
        color: white;
    }
    [data-testid="stMetricLabel"] { color: #b4b4b4; }
    </style>
    <!-- Fix for mobile safe areas and browser chrome -->
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
    <meta name="theme-color" content="#0E1117">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-capable" content="yes">
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
# 2. CACHED DATA FUNCTIONS
# ---------------------------
@st.cache_data(ttl=60)
def get_clients():
    return supabase.table("clients").select("*").order("created_at", desc=True).execute()

@st.cache_data(ttl=300)
def get_inventory():
    return supabase.table("inventory").select("*").order("item_name").execute()

@st.cache_data(ttl=300)
def get_suppliers():
    return supabase.table("suppliers").select("*").order("name").execute()

@st.cache_data(ttl=3600)
def get_settings():
    try:
        res = supabase.table("settings").select("*").eq("id", 1).execute()
        if res and res.data: return res.data[0]
        return {}
    except: return {}

import re
def sanitize_filename(name):
    return re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')

# ---------------------------
# 3. AUTHENTICATION
# ---------------------------
def get_manager():
    return stx.CookieManager(key="auth_cookie_manager")

cookie_manager = get_manager()

def check_login(username, password):
    try:
        res = supabase.table("users").select("username, password").eq("username", username).execute()
        if res and res.data:
            stored_password = res.data[0]['password']
            return stored_password == password  # Plain text comparison
        return False
    except Exception as e:
        st.error(f"Database Error: {e}")
        return False

def login_section():
    st.title("🔐 Jugnoo")
    time.sleep(0.1)
    
    # Check if user already logged in via cookie
    cookie_user = cookie_manager.get(cookie="jugnoo_user")
    if cookie_user:
        st.session_state.logged_in = True
        st.session_state.username = cookie_user
        return  # Exit here, don't show login UI
    
    # If already logged in (from this session), don't show form
    if st.session_state.get('logged_in'):
        return

    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        with st.form("login"):
            st.subheader("Sign In")
            user = st.text_input("Username")
            pwd = st.text_input("Password", type="password")
            if st.form_submit_button("Login", type="primary"):
                if check_login(user, pwd):
                    st.session_state.logged_in = True
                    st.session_state.username = user
                    expires = datetime.now() + timedelta(days=7)
                    cookie_manager.set("jugnoo_user", user, expires_at=expires)
                    st.rerun()
                else:
                    st.error("Invalid Username or Password")

# ---------------------------
# 4. MAIN APP LOGIC
# ---------------------------
login_section()

if not st.session_state.get('logged_in'):
    st.stop()

# Top Bar
top_c1, top_c2 = st.columns([10, 2])
top_c1.write(f"👤 Logged in as: **{st.session_state.username}**")
if top_c2.button("Log Out", type="secondary"):
    st.session_state.logged_in = False
    cookie_manager.delete("jugnoo_user")
    st.rerun()

# Define Tabs
tab1, tab2, tab3, tab_inv, tab5, tab6, tab4 = st.tabs(["📋 Dashboard", "➕ New Client", "🧮 Estimator", "📦 Inventory", "🚚 Suppliers", "📈 P&L", "⚙️ Settings"])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.subheader("Client Dashboard")
    status_filter = st.radio("Show:", ["Active", "All", "Closed"], horizontal=True)
    
    try:
        all_clients_resp = get_clients()
        if all_clients_resp and all_clients_resp.data:
            df = pd.DataFrame(all_clients_resp.data)
            if status_filter == "Active":
                df = df[~df['status'].isin(["Closed", "Work Done"])]
            elif status_filter == "Closed":
                df = df[df['status'].isin(["Closed", "Work Done"])]
            
            if not df.empty:
                for idx, client in df.iterrows():
                    with st.expander(f"{client['name']} - {client['status']}"):
                        st.markdown("### 🛠️ Manage Client")
                        c1, c2 = st.columns([1.5, 1])
                        with c1:
                            st.write("**Edit Details**")
                            with st.form(f"edit_details_{client['id']}"):
                                nn = st.text_input("Name", value=client['name'])
                                np = st.text_input("Phone", value=client.get('phone', ''))
                                na = st.text_area("Address", value=client.get('address', ''))
                                ml = st.text_input("Maps Link", value=client.get('location', ''))
                                
                                if client.get('location'):
                                    st.link_button("📍 Open Location", url=client['location'], use_container_width=True)

                                if st.form_submit_button("💾 Save Changes"):
                                    try:
                                        supabase.table("clients").update({"name": nn, "phone": np, "address": na, "location": ml}).eq("id", client['id']).execute()
                                        st.success("Saved!")
                                        get_clients.clear()
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error: {e}")
                        
                        with c2:
                            st.write("**Project Status**")
                            opts = helpers.ACTIVE_STATUSES + helpers.INACTIVE_STATUSES
                            curr_status = client.get('status')
                            try: idx = opts.index(curr_status)
                            except: idx = 0
                            n_stat = st.selectbox("Status", opts, index=idx, key=f"st_{client['id']}")
                            
                            s_date = None
                            if n_stat in ["Order Received", "Work In Progress", "Work Done"]:
                                d_str = client.get('start_date')
                                def_d = datetime.strptime(d_str, '%Y-%m-%d').date() if d_str else datetime.now().date()
                                s_date = st.date_input("📅 Start Date", value=def_d, key=f"sd_{client['id']}")
                            
                            if st.button("Update Status", key=f"btn_{client['id']}"):
                                upd = {"status": n_stat}
                                if s_date: upd["start_date"] = s_date.isoformat()
                                try:
                                    supabase.table("clients").update(upd).eq("id", client['id']).execute()
                                    st.success("Status Updated!")
                                    get_clients.clear()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")

                            # Payment Section (Only for Closed)
                            if client.get('status') == "Closed":
                                st.divider()
                                st.write("💰 **Record Payment Received**")
                                est_data = client.get('internal_estimate', {})
                                est_advance = 0
                                if est_data:
                                    try:
                                        gs = get_settings()
                                        am_normalized = helpers.normalize_margins(est_data.get('margins'), gs)
                                        calc_results = helpers.calculate_estimate_details(
                                            edf_items_list=est_data.get('items', []),
                                            days=est_data.get('days', 1.0),
                                            margins=am_normalized,
                                            global_settings=gs
                                        )
                                        est_advance = calc_results["rounded_grand_total"]
                                    except:
                                        pass
                                
                                curr_pay = client.get('final_settlement_amount', 0.0)
                                val_to_show = float(curr_pay) if curr_pay else float(est_advance)
                                # Enforce rounding (Ceil to 100) and ensure integer type
                                if pd.isna(val_to_show) or val_to_show == 0:
                                    val_to_show = int(est_advance) if not pd.isna(est_advance) else 0
                                else:
                                    val_to_show = int(math.ceil(val_to_show / 100) * 100)
                                
                                payment_col1, payment_col2 = st.columns(2)
                                with payment_col1:
                                    st.metric("Estimated Grand Total", f"₹{est_advance:,.0f}")
                                with payment_col2:
                                    new_pay_key = f"pay_{client['id']}"
                                    if new_pay_key not in st.session_state or (st.session_state[new_pay_key] == 0 and val_to_show > 0):
                                        st.session_state[new_pay_key] = val_to_show
                                    
                                    new_pay = st.number_input("Final Amount Received (₹)", min_value=0, value=val_to_show, step=100, key=new_pay_key)
                                
                                if st.button("Save Final Payment", key=f"save_pay_{client['id']}"):
                                    new_pay_rounded = int(math.ceil(new_pay / 100) * 100)
                                    supabase.table("clients").update({"final_settlement_amount": new_pay_rounded}).eq("id", client['id']).execute()
                                    st.toast("Payment Saved Successfully!", icon="✅")
                                    time.sleep(1.0)
                                    get_clients.clear()
                                    st.rerun()

                        st.expander("Danger Zone").button("Delete Client", type="secondary", use_container_width=True, on_click=lambda id=client['id']: (
                            supabase.table("clients").delete().eq("id", id).execute()
                        ), key=f"del_{client['id']}")
                        
                        if st.session_state.get(f"del_{client['id']}"):
                             get_clients.clear()
                             st.rerun()

                        # --- Restore "Manage Estimate" Section ---
                        if client.get('internal_estimate'):
                            st.divider()
                            st.subheader("📋 Manage Estimate")
                            est_data = client['internal_estimate']
                            s_items_raw = est_data.get('items', [])
                            s_days = float(est_data.get('days', 1.0))
                            
                            s_items_sanitized = []
                            for item in s_items_raw:
                                sanitized_item = item.copy()
                                sanitized_item['Qty'] = float(sanitized_item.get('Qty', 0))
                                sanitized_item['Base Rate'] = float(sanitized_item.get('Base Rate', 0))
                                s_items_sanitized.append(sanitized_item)
                            
                            ssk_dash = f"dash_est_{client['id']}"
                            if ssk_dash not in st.session_state:
                                st.session_state[ssk_dash] = s_items_sanitized

                            if st.session_state[ssk_dash]:
                                idf = helpers.create_item_dataframe(st.session_state[ssk_dash])
                                idf.insert(0, 'Sr No', range(1, len(idf) + 1))
                                edited_est = st.data_editor(idf, num_rows="dynamic", use_container_width=True, key=f"de_{client['id']}",
                                                            column_config={
                                                                "Sr No": st.column_config.NumberColumn("Sr No", width="small", disabled=True),
                                                                "Qty": st.column_config.NumberColumn("Qty", width="small", step=0.1),
                                                                "Item": st.column_config.TextColumn("Item", width="large"),
                                                                "Unit": st.column_config.TextColumn("Unit", width="small", disabled=True),
                                                                "Base Rate": st.column_config.NumberColumn("Base Rate", width="small"),
                                                                "Unit Price": st.column_config.NumberColumn("Unit Price", format="₹%.2f", width="small", disabled=True),
                                                                "Total Price": st.column_config.NumberColumn("Total Price", format="₹%.2f", width="small", disabled=True)
                                                            })
                                
                                gs = get_settings()
                                am_normalized = helpers.normalize_margins(est_data.get('margins'), gs)
                                
                                calculated_results = helpers.calculate_estimate_details(
                                    edf_items_list=edited_est.to_dict(orient="records"),
                                    days=s_days,
                                    margins=am_normalized,
                                    global_settings=gs
                                )
                                
                                mat_sell = calculated_results["mat_sell"]
                                labor_charged_display = calculated_results["disp_lt"]
                                rounded_grand_total = calculated_results["rounded_grand_total"]
                                total_profit = calculated_results["total_profit"]
                                advance_amount = calculated_results["advance_amount"]
                                edited_est_with_prices = calculated_results["edf_details_df"]
                                
                                m1, m2, m3, m4, m5 = st.columns(5)
                                m1.metric("Material Total", f"₹{mat_sell:,.0f}"); m2.metric("Labor", f"₹{labor_charged_display:,.0f}"); m3.metric("Grand Total", f"₹{rounded_grand_total:,.0f}"); m4.metric("Total Profit", f"₹{total_profit:,.0f}"); m5.metric("Advance Required", f"₹{advance_amount:,.0f}")
                                
                                if st.button("💾 Save Estimate Changes", key=f"sv_{client['id']}"):
                                    df_to_save = edited_est_with_prices.copy()
                                    for col in ['Qty', 'Base Rate', 'Total Price', "Unit Price"]:
                                        df_to_save[col] = pd.to_numeric(df_to_save[col].fillna(0))
                                    for col in ['Item', 'Unit']: df_to_save[col] = df_to_save[col].fillna("")
                                    
                                    
                                    st.dataframe(df_profit[['Item', 'Qty', 'Unit', 'Base Rate', 'Total Sell Price', 'Row Profit']], use_container_width=True, hide_index=True)
                                    st.metric("Net Profit (from Grand Total)", f"₹{total_profit:,.0f}")
                                else:
                                    st.info("Mark status as 'Work Done' or 'Closed' to view Internal Profit Analysis.")
                            else:
                                st.warning("Estimate Empty")
            else:
                st.info("No clients match the filter.")
        else:
            st.info("No clients found.")
    except Exception as e:
        st.error(f"Error: {e}")

# --- TAB 2: NEW CLIENT ---
with tab2:
    st.subheader("Add New Client")
    loc_new_client = get_geolocation(component_key="geo_tab2_new_client")
    gmaps_new_client = ""
    if loc_new_client:
        st.write(f"Detected: {loc_new_client['coords']['latitude']}, {loc_new_client['coords']['longitude']}")
        if st.button("Paste Location to Form", key="paste_loc_tab2_new_client"):
            gmaps_new_client = f"https://www.google.com/maps/search/{loc_new_client['coords']['latitude']},{loc_new_client['coords']['longitude']}"
            st.session_state["loc_in_new_client"] = gmaps_new_client
    
    with st.form("new_client"):
        c1, c2 = st.columns(2)
        nm, ph = c1.text_input("Client Name"), c2.text_input("Phone")
        ad = st.text_area("Address")
        maps_link_new_client_key = "loc_in_new_client"
        if maps_link_new_client_key not in st.session_state:
            st.session_state[maps_link_new_client_key] = ""
        
        ml_new_client = st.text_input("Google Maps Link", key=maps_link_new_client_key)
        
        if st.form_submit_button("Create Client", type="primary"):
            try:
                res = supabase.table("clients").insert({"name": nm, "phone": ph, "address": ad, "location": ml_new_client, "status": "Estimate Given", "created_at": datetime.now().isoformat()}).execute()
                if res and res.data: 
                    st.success(f"Client {nm} Added!")
                    get_clients.clear()
                    st.rerun()
                else: st.error("Save Failed.")
            except Exception as e:
                st.error(f"Database Error: {e}")

# --- TAB 3: ESTIMATOR ---
with tab3:
    st.subheader("Estimator Engine")
    with st.spinner("Loading Estimator..."):
        try:
            ac = supabase.table("clients").select("id, name, internal_estimate").neq("status", "Closed").execute()
        except Exception as e:
            st.error(f"Database Error: {e}")
            ac = None
    cd = {c['name']: c for c in ac.data} if ac and ac.data else {}
    tn = st.selectbox("Select Client", list(cd.keys()), key="est_sel")
    
    if tn:
        tc = cd[tn]
        se, li = tc.get('internal_estimate'), []
        if se: li = se.get('items', [])
        sm = se.get('margins') if se else None
        sd = se.get('days', 1.0) if se else 1.0
        ssk = f"est_{tc['id']}"
        if ssk not in st.session_state: st.session_state[ssk] = li

        st.divider(); gs = get_settings()
        col1, col2 = st.columns([1, 3])
        with col1:
            uc = st.checkbox("🛠️ Use Custom Margins", value=(sm is not None), key="cm")
        with col2:
            dys = st.number_input("⏳ Days", min_value=1, step=1, value=int(sd))
        am = gs
        if uc:
            dp, dl, de = (int(sm['p']), int(sm['l']), int(sm['e'])) if sm else (int(gs['part_margin']), int(gs['labor_margin']), int(gs['extra_margin']))
            mc1, mc2, mc3 = st.columns(3)
            cp, cl, ce = mc1.slider("Part %", 0, 100, dp, key="cp"), mc2.slider("Labor %", 0, 100, dl, key="cl"), mc3.slider("Extra %", 0, 100, de, key="ce")
            am = {'part_margin': cp, 'labor_margin': cl, 'extra_margin': ce}

        st.divider()

        # Step A: Fetch Stock Data
        try:
            inv_all_items_response = get_inventory()
        except Exception as e:
            st.error(f"Database Error: {e}")
            inv_all_items_response = None
        stock_map = {}
        if inv_all_items_response and inv_all_items_response.data:
            stock_map = {item['item_name']: item.get('stock_quantity', 0.0) for item in inv_all_items_response.data}
            
        inv = inv_all_items_response
        if inv and inv.data:
            imap = {i['item_name']: i for i in inv.data}
            with st.form("add_est"):
                c1, c2, c3 = st.columns([3, 1, 1])
                inam = c1.selectbox("Item", list(imap.keys()))
                
                default_unit = imap.get(inam, {}).get('unit', 'pcs')
                step_val = 1.0 if default_unit == "pcs" else 0.1
                
                iqty = c2.number_input("Qty", min_value=0.1, step=step_val)
                iunit = c3.text_input("Unit", value=default_unit, disabled=True)
                
                if st.form_submit_button("⬇️ Add"):
                    selected_item = imap.get(inam, {})
                    st.session_state[ssk].append({"Item": inam, "Qty": iqty, "Base Rate": selected_item.get('base_rate', 0), "Unit": default_unit})
                    st.rerun()

        if st.session_state[ssk]:
            df = helpers.create_item_dataframe(st.session_state[ssk])
            df.insert(0, 'Sr No', range(1, len(df) + 1))

            st.write("#### Items")
            edf = st.data_editor(df, num_rows="dynamic", use_container_width=True, key=f"t_{tc['id']}", 
                column_config={
                    "Sr No": st.column_config.NumberColumn("Sr No", width="small", disabled=True),
                    "Qty": st.column_config.NumberColumn("Qty", width="small", step=0.1), # Allow float generally, restricted at input
                    "Item": st.column_config.TextColumn("Item", width="large"),
                    "Unit": st.column_config.TextColumn("Unit", width="small", disabled=True),
                    "Base Rate": st.column_config.NumberColumn("Base Rate", width="small"),
                    "Unit Price": st.column_config.NumberColumn("Unit Price", format="₹%.2f", width="small", disabled=True),
                    "Total Price": st.column_config.NumberColumn("Total Price", format="₹%.2f", width="small", disabled=True)
                })
            
            # Enforce float types for calculation consistency early
            edf['Qty'] = pd.to_numeric(edf['Qty'], errors='coerce').fillna(0).astype(float)
            edf['Base Rate'] = pd.to_numeric(edf['Base Rate'], errors='coerce').fillna(0).astype(float)

            # --- Universal Calculation Logic ---
            gs = get_settings()
            am_for_calc = am  # Use the margins already set above

            calculated_results = helpers.calculate_estimate_details(
                edf_items_list=edf.to_dict(orient="records"),
                days=dys,
                margins=am_for_calc,
                global_settings=gs
            )

            edf['Total Price'] = edf.apply(lambda row: calculated_results["edf_details_df"].loc[row.name, 'Total Price'] if row.name in calculated_results["edf_details_df"].index else 0, axis=1)
            edf['Unit Price'] = edf.apply(lambda row: calculated_results["edf_details_df"].loc[row.name, 'Unit Price'] if row.name in calculated_results["edf_details_df"].index else 0, axis=1)

            mt = calculated_results["mat_sell"]
            daily_cost = float(gs.get('daily_labor_cost', 1000))
            raw_lt = calculated_results["labor_actual_cost"]
            rounded_gt = calculated_results["rounded_grand_total"]
            total_profit = calculated_results["total_profit"]
            advance_amount = calculated_results["advance_amount"]
            disp_lt = calculated_results["disp_lt"]

            # Sync logic
            if edf.to_dict(orient="records") != st.session_state[ssk]:
                st.session_state[ssk] = edf.to_dict(orient="records")
                st.rerun()

            # --- Stock Check Alert System ---
            missing_items = []
            for index, row in edf.iterrows():
                item_name = row.get('Item')
                estimated_qty = float(row.get('Qty', 0))
                available_stock = float(stock_map.get(item_name, 0.0)) # Ensure available_stock is float for comparison
                
                if estimated_qty > available_stock:
                    missing_items.append(f"{item_name}: Need {int(estimated_qty)}, Have {int(available_stock)}")
            
            if missing_items:
                st.error("⚠️ **Low Stock Warning:** You do not have enough inventory for: " + ", ".join(missing_items) + ". Please visit Suppliers tab to restock.")
            
            # --- End Stock Check Alert System ---

            # Update dataframe with calculated prices from helper function
            edf = calculated_results["edf_details_df"].copy()

            st.divider()
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Material", f"₹{mt:,.0f}"); c2.metric("Labor", f"₹{disp_lt:,.0f}"); c3.metric("Grand Total", f"₹{rounded_gt:,.0f}"); c4.metric("Total Profit", f"₹{total_profit:,.0f}"); c5.metric("Advance Required", f"₹{advance_amount:,.0f}")
            
            cs, cp = st.columns(2)
            if cs.button("💾 Save", type="primary"):
                df_to_save = edf.copy()
                for col in ['Qty', 'Base Rate', 'Total Price', "Unit Price"]:
                    df_to_save[col] = pd.to_numeric(df_to_save[col].fillna(0))
                for col in ['Item', 'Unit']: df_to_save[col] = df_to_save[col].fillna("")
                cit = df_to_save.to_dict(orient="records")
                sobj = {"items": cit, "days": dys, "margins": am if uc else None}
                try:
                    res = supabase.table("clients").update({"internal_estimate": sobj}).eq("id", tc['id']).execute()
                    if res and res.data: st.toast("Saved!", icon="✅")
                except Exception as e:
                    st.error(f"Database Error: {e}")
            
            pbytes = create_pdf(tc['name'], edf.to_dict(orient="records"), dys, disp_lt, rounded_gt, advance_amount, is_final=False)
            sanitized_est_name = sanitize_filename(tc['name'])
            cp.download_button("📄 Download PDF", pbytes, f"Est_{sanitized_est_name}.pdf", "application/pdf", key=f"pe_{tc['id']}")
# --- TAB 4: INVENTORY ---
with tab_inv:
    st.subheader("📦 Inventory Management")
    
    # Add New Item
    with st.expander("➕ Add New Item"):
        with st.form("add_inv_item"):
            c1, c2, c3 = st.columns([2, 1, 1])
            inm = c1.text_input("Item Name")
            ib_rate = c2.number_input("Base Rate (₹)", min_value=0.0, step=0.1)
            iunit = c3.selectbox("Unit", ["pcs", "m", "ft", "cm", "in"])
            
            if st.form_submit_button("Add Item"):
                try:
                    supabase.table("inventory").insert({"item_name": inm, "base_rate": ib_rate, "unit": iunit, "stock_quantity": 0}).execute()
                    st.success(f"Item '{inm}' added!")
                    get_inventory.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # List Inventory
    try:
        inv_resp = get_inventory()
        if inv_resp and inv_resp.data:
            idf = pd.DataFrame(inv_resp.data)
            idf['Sr No'] = range(1, len(idf) + 1)
            
            # Editable Dataframe
            edited_inv = st.data_editor(
                idf[['Sr No', 'item_name', 'stock_quantity', 'base_rate', 'unit']],
                key="inv_editor",
                use_container_width=True,
                column_config={
                    "Sr No": st.column_config.NumberColumn("Sr No", disabled=True),
                    "item_name": st.column_config.TextColumn("Item Name"),
                    "stock_quantity": st.column_config.NumberColumn("Stock", step=1),
                    "base_rate": st.column_config.NumberColumn("Base Rate", format="₹%.2f"),
                    "unit": st.column_config.SelectboxColumn("Unit", options=["pcs", "m", "ft", "cm", "in"])
                },
                hide_index=True
            )
            
            with st.expander("🛠️ Manage Item"):
                item_list = {i['item_name']: i for i in inv_resp.data}
                sel_item_name = st.selectbox("Select Item", list(item_list.keys()))
                if sel_item_name:
                    item = item_list[sel_item_name]
                    with st.form("edit_inv"):
                        c1, c2 = st.columns(2)
                        new_name = c1.text_input("Name", value=item['item_name'])
                        new_rate = c2.number_input("Base Rate", value=float(item['base_rate']))
                        new_stock = st.number_input("Stock", value=float(item['stock_quantity']))
                        new_unit = st.selectbox("Unit", ["pcs", "m", "ft", "cm", "in"], index=["pcs", "m", "ft", "cm", "in"].index(item['unit']) if item['unit'] in ["pcs", "m", "ft", "cm", "in"] else 0)
                        
                        if st.form_submit_button("Update Item"):
                            supabase.table("inventory").update({
                                "item_name": new_name,
                                "base_rate": new_rate,
                                "stock_quantity": new_stock,
                                "unit": new_unit
                            }).eq("id", item['id']).execute()
                            st.success("Updated!")
                            get_inventory.clear()
                            st.rerun()
                    
                    if st.button("Delete Item", type="secondary"):
                        supabase.table("inventory").delete().eq("id", item['id']).execute()
                        st.success("Deleted!")
                        get_inventory.clear()
                        st.rerun()

    except Exception as e:
        st.error(f"Error loading inventory: {e}")

# --- TAB 5: SUPPLIERS ---
with tab5:
    st.subheader("Supplier Management")
    
    # 1. Record Purchase
    with st.expander("📝 Record Purchase", expanded=True):
        try:
            sup_resp = get_suppliers()
            inv_resp = get_inventory()
        except:
            sup_resp = None; inv_resp = None
            
        if sup_resp and sup_resp.data and inv_resp and inv_resp.data:
            s_map = {s['name']: s['id'] for s in sup_resp.data}
            i_map = {i['item_name']: i for i in inv_resp.data}
            
            with st.form("rec_pur"):
                c1, c2 = st.columns(2)
                s_name = c1.selectbox("Supplier", list(s_map.keys()))
                i_name = c2.selectbox("Item", list(i_map.keys()))
                
                c3, c4 = st.columns(2)
                qty = c3.number_input("Quantity Purchased", min_value=1.0, step=1.0)
                rate = c4.number_input("Purchase Rate", min_value=0.0, step=0.1)
                
                if st.form_submit_button("✅ Record Purchase"):
                    try:
                        # Update Inventory Stock & Base Rate
                        curr_item = i_map[i_name]
                        new_stock = float(curr_item.get('stock_quantity', 0)) + qty
                        # Update base rate to latest purchase rate (or weighted average - keeping simple for now)
                        
                        supabase.table("inventory").update({"stock_quantity": new_stock, "base_rate": rate}).eq("id", curr_item['id']).execute()
                        
                        # Log Purchase (Optional - if you had a purchases table)
                        # supabase.table("purchases").insert({...}).execute()
                        
                        st.success(f"Purchase Recorded! New Stock: {new_stock}")
                        get_inventory.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
        else:
            st.warning("Add Suppliers and Inventory Items first.")

    st.divider()
    
    # 2. Supplier Directory
    st.markdown("### 📒 Supplier Directory")
    if sup_resp and sup_resp.data:
        sdf = pd.DataFrame(sup_resp.data)
        st.dataframe(sdf[['name', 'contact_person', 'phone']], use_container_width=True, hide_index=True)
    else:
        st.info("No suppliers found.")

# --- TAB 6: P&L ---
with tab6:
    st.subheader("📈 Profit & Loss Analysis")
    
    if st.button("🔄 Refresh Data"):
        get_clients.clear()
        st.rerun()
        
    with st.spinner("Loading Financial Data..."):
        try:
            cl_resp = get_clients()
            # Fetch Purchase Log for Global Expense Calculation (Main Branch Feature)
            purchase_log_resp = supabase.table("purchase_log").select("total_cost").execute()
            settings = get_settings()
        except Exception as e:
            st.error(f"Data Fetch Error: {e}")
            cl_resp = None
            purchase_log_resp = None
            settings = {}

    if cl_resp and cl_resp.data:
        df = pd.DataFrame(cl_resp.data)
        # Filter for completed projects for Project-based P&L
        closed_df = df[df['status'].isin(["Work Done", "Closed"])]
        
        # --- 1. GLOBAL CASH FLOW ANALYSIS (Main Branch Logic) ---
        # This tracks actual money in vs money out, regardless of project status
        
        # Total Revenue (Collected)
        # In Dev branch, we use 'final_settlement_amount' as the source of truth for collection
        # In Main branch, it was 'amount_received'
        # We will sum 'final_settlement_amount' for ALL clients (assuming partial payments aren't tracked separately yet)
        # For accurate cash flow, we should sum payments from ALL clients, but currently payment is only recorded on Close.
        # So we stick to Closed clients for Revenue to be safe, or if we want "Total Collected", we sum all non-null final_settlement_amounts.
        
        total_collected = df['final_settlement_amount'].fillna(0).sum()
        
        # Total Quoted Value (Sum of Estimates for Closed Projects)
        total_quoted = 0.0
        for idx, row in closed_df.iterrows():
            est = row.get('internal_estimate')
            if est:
                 try:
                    # Recalculate grand total to be sure
                    am_normalized = helpers.normalize_margins(est.get('margins'), settings)
                    calc = helpers.calculate_estimate_details(est.get('items', []), est.get('days', 1.0), am_normalized, settings)
                    total_quoted += calc["rounded_grand_total"]
                 except: pass

        # Total Expenses (Global)
        # Material Expense from Purchase Log
        purchase_log_data = purchase_log_resp.data if purchase_log_resp and purchase_log_resp.data else []
        total_material_expense_cash = sum(float(log.get('total_cost', 0.0)) for log in purchase_log_data if log.get('total_cost'))
        
        # Labor Expense (Sum of labor cost from Closed projects)
        # We assume labor is paid when project is closed/done.
        total_labor_expense_cash = 0.0
        daily_labor_cost = float(settings.get('daily_labor_cost', 1000.0))
        
        for idx, row in closed_df.iterrows():
            est = row.get('internal_estimate')
            if est:
                days = float(est.get('days', 0.0))
                total_labor_expense_cash += (days * daily_labor_cost)
                
        total_expenses_cash = total_material_expense_cash + total_labor_expense_cash
        
        # Actual Cash Profit
        actual_cash_profit = total_collected - total_expenses_cash
        actual_margin_pct = (actual_cash_profit / total_collected * 100) if total_collected > 0 else 0
        
        # Discount Loss (Quoted vs Collected)
        discount_loss = total_quoted - total_collected

        # --- 2. PROJECT-BASED PROFITABILITY (Dev Branch Logic) ---
        # This analyzes profitability per project based on ESTIMATED costs vs ACTUAL revenue
        
        pl_data = []
        total_est_cost_project = 0.0
        total_est_profit_project = 0.0
        
        for idx, row in closed_df.iterrows():
            est = row.get('internal_estimate')
            actual_rev = float(row.get('final_settlement_amount', 0.0))
            
            # Fallback if 0
            if actual_rev == 0 and est:
                try:
                    am_normalized = helpers.normalize_margins(est.get('margins'), settings)
                    calc = helpers.calculate_estimate_details(est.get('items', []), est.get('days', 1.0), am_normalized, settings)
                    actual_rev = calc["rounded_grand_total"]
                except: pass
            
            est_cost = 0.0
            est_profit = 0.0
            mat_cost = 0.0
            labor_cost = 0.0
            
            if est:
                try:
                    am_normalized = helpers.normalize_margins(est.get('margins'), settings)
                    calc = helpers.calculate_estimate_details(est.get('items', []), est.get('days', 1.0), am_normalized, settings)
                    
                    items = est.get('items', [])
                    mat_cost = sum([float(i.get('Qty',0)) * float(i.get('Base Rate',0)) for i in items])
                    labor_cost = calc["labor_actual_cost"]
                    
                    est_cost = mat_cost + labor_cost
                    est_profit = actual_rev - est_cost
                except: pass
            
            total_est_cost_project += est_cost
            total_est_profit_project += est_profit
            
            pl_data.append({
                "Client": row['name'],
                "Revenue": actual_rev,
                "Cost": est_cost,
                "Profit": est_profit,
                "Material Cost": mat_cost,
                "Labor Cost": labor_cost,
                "created_at": row.get('created_at')
            })
            
        pl_df = pd.DataFrame(pl_data)

        # --- DISPLAY METRICS ---
        
        st.markdown("### 📊 Executive Summary (Cash Flow)")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Collected", f"₹{total_collected:,.0f}", delta=f"Quoted: ₹{total_quoted:,.0f}")
        k2.metric("Total Expenses (Cash)", f"₹{total_expenses_cash:,.0f}")
        k3.metric("Net Cash Profit", f"₹{actual_cash_profit:,.0f}", delta=f"{actual_margin_pct:.1f}% Margin")
        k4.metric("Revenue Gap (Discounts)", f"₹{discount_loss:,.0f}", delta_color="inverse")
        
        st.divider()
        
        st.markdown("### 🏗️ Operational Metrics")
        o1, o2, o3 = st.columns(3)
        o1.metric("Projects Completed", len(closed_df))
        o2.metric("Material Expenses (Log)", f"₹{total_material_expense_cash:,.0f}")
        o3.metric("Labor Expenses (Est)", f"₹{total_labor_expense_cash:,.0f}")

        st.divider()

        # --- CHARTS ---
        
        c_chart1, c_chart2 = st.columns(2)
        
        # 1. Revenue vs Expenses vs Payment (Main Branch Feature)
        with c_chart1:
            st.markdown("#### Revenue vs Expenses vs Payment")
            chart_data_comparison = pd.DataFrame({
                'Category': ['Quoted Total', 'Collected', 'Total Expenses'],
                'Amount': [total_quoted, total_collected, total_expenses_cash]
            })
            
            comparison_chart = alt.Chart(chart_data_comparison).mark_bar().encode(
                x=alt.X('Category:N', axis=alt.Axis(labelAngle=0)),
                y=alt.Y('Amount:Q', axis=alt.Axis(format='₹,.0f')),
                color=alt.Color('Category:N', scale=alt.Scale(domain=['Quoted Total', 'Collected', 'Total Expenses'], range=['#3498db', '#2ecc71', '#e74c3c'])),
                tooltip=['Category', 'Amount']
            ).properties(height=300)
            st.altair_chart(comparison_chart, use_container_width=True)

        # 2. Cost Split (Main Branch Feature)
        with c_chart2:
            st.markdown("#### Global Cost Split")
            cost_data = pd.DataFrame({
                'Category': ['Material (Log)', 'Labor (Est)'],
                'Amount': [total_material_expense_cash, total_labor_expense_cash]
            })
            chart_cost = alt.Chart(cost_data).mark_arc(innerRadius=50).encode(
                theta='Amount',
                color=alt.Color('Category', scale=alt.Scale(range=['#FF9800', '#9C27B0'])),
                tooltip=['Category', 'Amount']
            ).properties(height=300)
            st.altair_chart(chart_cost, use_container_width=True)

        st.divider()
        
        # 3. Monthly Trend (Dev Branch Feature)
        if not pl_df.empty:
            st.markdown("### 📅 Monthly Performance")
            pl_df['created_at'] = pd.to_datetime(pl_df['created_at'])
            pl_df['Month'] = pl_df['created_at'].dt.strftime('%Y-%m')
            monthly_data = pl_df.groupby('Month')[['Revenue', 'Profit']].sum().reset_index()
            
            chart_monthly = alt.Chart(monthly_data).mark_bar().encode(
                x='Month',
                y='Revenue',
                color=alt.value('#2196F3')
            ) + alt.Chart(monthly_data).mark_line(color='#FFC107').encode(
                x='Month',
                y='Profit'
            )
            st.altair_chart(chart_monthly, use_container_width=True)

        # 4. Business Health Table (Main Branch Feature)
        st.markdown("### 🏥 Business Health Scorecard")
        health_data = {
            "Metric": ["Revenue Capture Rate", "Profit Margin", "Cost Efficiency", "Labor Cost %"],
            "Value": [
                f"{(total_collected / total_quoted * 100) if total_quoted > 0 else 0:.1f}%",
                f"{actual_margin_pct:.1f}%",
                f"{(total_expenses_cash / total_collected * 100) if total_collected > 0 else 0:.1f}%",
                f"{(total_labor_expense_cash / total_expenses_cash * 100) if total_expenses_cash > 0 else 0:.1f}%"
            ],
            "Target": ["> 95%", "> 20%", "< 70%", "< 30%"]
        }
        st.dataframe(pd.DataFrame(health_data), use_container_width=True, hide_index=True)

    else:
        st.info("No data available.")


# --- TAB 4: SETTINGS ---
with tab4:
    st.subheader("⚙️ Global Settings")
    
    try:
        sett = get_settings()
    except: sett = {}
    
    with st.form("settings_form"):
        c1, c2, c3 = st.columns(3)
        pm = c1.number_input("Default Parts Margin (%)", value=int(sett.get('part_margin', 20)))
        lm = c2.number_input("Default Labor Margin (%)", value=int(sett.get('labor_margin', 20)))
        em = c3.number_input("Default Extra Margin (%)", value=int(sett.get('extra_margin', 10)))
        
        dlc = st.number_input("Daily Labor Cost (₹)", value=float(sett.get('daily_labor_cost', 1000.0)))
        
        if st.form_submit_button("💾 Save Settings"):
            try:
                # Upsert settings (assuming id=1)
                supabase.table("settings").upsert({"id": 1, "part_margin": pm, "labor_margin": lm, "extra_margin": em, "daily_labor_cost": dlc}).execute()
                st.success("Settings Saved!")
                get_settings.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    st.divider()
    st.subheader("🧮 Advance Payment Calculator")
    
    ac1, ac2 = st.columns([1, 2])
    with ac1:
        total_est_val = st.number_input("Total Estimate Value (₹)", min_value=0.0, value=100000.0, step=1000.0)
        adv_percent = st.slider("Advance Percentage", 0, 100, 60)
    
    with ac2:
        adv_amt = total_est_val * (adv_percent / 100)
        st.metric("Advance Required", f"₹{adv_amt:,.0f}")
        st.info(f"Formula: Total Value * {adv_percent}%")
