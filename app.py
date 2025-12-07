import streamlit as st
from supabase import create_client
from utils import helpers, auth
from utils.helpers import create_pdf

from datetime import datetime, timedelta
import time
import pandas as pd
import math
import textwrap

from streamlit_js_eval import get_geolocation
import altair as alt
import plotly.graph_objects as go
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

# --- HIDE STREAMLIT ANCHORS & TOOLBAR ---
st.markdown("""
    <style>
    /* Hide the link icon next to headers */
    [data-testid="stHeader"] a {
        display: none;
    }
    /* Hide Streamlit Header and Toolbar */
    [data-testid="stHeader"] {
        visibility: hidden;
    }
    [data-testid="stToolbar"] {
        visibility: hidden;
    }
    /* Reduce top spacing */
    .block-container {
        padding-top: 1rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Initialize Session State
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ""

st.markdown("""
    <style>
    /* System Fonts for Emoji Support */
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol";
    }
    
    /* Deep Space Background */
    .stApp {
        background: radial-gradient(circle at 10% 20%, #0f172a 0%, #020617 90%);
        color: #e2e8f0;
    }
    
    /* Glassmorphism Cards (With Border) */
    [data-testid="stMetric"] {
        background: rgba(30, 41, 59, 0.4);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.2);
        transition: all 0.3s ease;
        font-weight: 700;
        letter-spacing: -0.02em;
        background: none !important;
        -webkit-text-fill-color: initial !important;
    }

    /* DataFrame & Tables - Match UI */
    div.stDataFrame {
        background-color: transparent !important;
        border: none !important;
    }
    
    [data-testid="stDataFrame"] div[class*="stDataFrame"] {
        background-color: transparent !important;
    }
    
    /* Premium Slate Buttons */
    div.stButton > button {
        background: rgba(30, 41, 59, 0.6) !important;
        color: #f1f5f9 !important;
        border: 1px solid rgba(148, 163, 184, 0.1) !important;
        padding: 0.6rem 1.5rem !important; /* Increased padding */
        border-radius: 8px;
        font-weight: 500;
        letter-spacing: 0.02em;
        transition: all 0.2s ease;
    }
    
    div.stButton > button:hover {
        background: rgba(51, 65, 85, 0.8) !important;
        border-color: rgba(148, 163, 184, 0.3) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        color: #ffffff !important;
    }
    
    div.stButton > button:active {
        transform: translateY(0);
        background: rgba(30, 41, 59, 0.8) !important;
    }
    
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

@st.cache_data(ttl=300)
def get_staff():
    try:
        return supabase.table("staff").select("*").order("name").execute()
    except: return None

@st.cache_data(ttl=300)
def get_staff_roles():
    try:
        return supabase.table("staff_roles").select("*").execute()
    except: return None

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

def calculate_labor_from_assignments(assigned_ids):
    """
    Calculates total daily labor cost for a list of assigned staff IDs.
    Returns the sum of their daily wages.
    """
    if not assigned_ids:
        return 0.0
    
    try:
        # Fetch staff data for these IDs
        res = supabase.table("staff").select("daily_wage").in_("id", assigned_ids).execute()
        if res and res.data:
            total = sum(float(item['daily_wage']) for item in res.data if item.get('daily_wage'))
            return total
    except Exception as e:
        print(f"Error calculating labor: {e}")
        return 0.0

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
    # Check if user already logged in via cookie
    with st.spinner("Checking session..."):
        time.sleep(0.3) # Allow cookie manager to sync
        cookie_user = cookie_manager.get(cookie="jugnoo_user")
    
    if cookie_user:
        st.session_state.logged_in = True
        st.session_state.username = cookie_user
        return  # Exit here, don't show login UI
    
    # If already logged in (from this session), don't show form
    if st.session_state.get('logged_in'):
        return

    st.title("🔐 Jugnoo CRM")

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
                    expires = datetime.now() + timedelta(days=3650)
                    cookie_manager.set("jugnoo_user", user, expires_at=expires)
                    time.sleep(0.5)
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
st.title("🚀 Jugnoo CRM")
st.markdown(f"""
<div style="display: flex; align-items: center; margin-bottom: 0px;">
    <span style="font-size: 1.75rem; margin-right: 10px;">👋</span>
    <span style="font-size: 1.75rem; font-weight: 700; background: linear-gradient(to right, #f8fafc, #94a3b8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">Welcome back, {st.session_state.username}</span>
</div>
""", unsafe_allow_html=True)

# Define Tabs
tab1, tab2, tab3, tab_inv, tab5, tab8, tab6, tab4 = st.tabs(["📋 Dashboard", "➕ New Client", "🧮 Estimator", "📦 Inventory", "🚚 Suppliers", "👥 Staff", "📈 P&L", "⚙️ Settings"])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.subheader("📋 Project Dashboard")
    
    # Dashboard Metrics
    try:
        cl_data = get_clients().data
        if cl_data:
            df_dash = pd.DataFrame(cl_data)
            total_clients = len(df_dash)
            active_clients = len(df_dash[df_dash['status'].isin(helpers.ACTIVE_STATUSES)])
            
            d1, d2, d3 = st.columns(3)
            d1.metric("Total Clients", total_clients)
            d2.metric("Active Projects", active_clients)
            d3.metric("Completion Rate", f"{(len(df_dash[df_dash['status']=='Closed'])/total_clients*100):.1f}%" if total_clients > 0 else "0%")
            
            st.divider()
            
            # Recent Activity & Top Clients
            c_act, c_top = st.columns(2)
            with c_act:
                st.markdown("#### 🕒 Recent Activity")
                if 'created_at' in df_dash.columns:
                    rec_df = df_dash.sort_values('created_at', ascending=False).head(5)
                    for _, r in rec_df.iterrows():
                        st.text(f"{r['created_at'][:10]} - {r['name']} ({r['status']})")
                else: st.info("No activity data.")
            
            with c_top:
                st.markdown("#### 🏆 Top Clients (Value)")
                if 'internal_estimate' in df_dash.columns:
                    def get_val(x):
                        try: return float(x.get('total', 0)) if x else 0
                        except: return 0
                    
                    df_dash['est_val'] = df_dash['internal_estimate'].apply(get_val)
                    top_df = df_dash.sort_values('est_val', ascending=False).head(5)
                    st.dataframe(top_df[['name', 'est_val']], column_config={"name": "Client", "est_val": st.column_config.NumberColumn("Est. Value", format="₹%.2f")}, hide_index=True, use_container_width=True)
                else: st.info("No value data.")
            
            st.markdown("---") # Use a thinner separator or just margin
    except: pass

    st.markdown("### 📂 Client Projects")
    status_filter = st.radio("Filter", ["Active", "All", "Closed"], horizontal=True, label_visibility="collapsed")
    
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
                                np = st.text_input("Phone", value=client.get('phone', ''), max_chars=15, help="Enter digits only")
                                na = st.text_area("Address", value=client.get('address', ''))
                                ml = st.text_input("Maps Link", value=client.get('location', ''))
                                
                                if client.get('location'):
                                    st.link_button("📍 Open Location", url=client['location'], use_container_width=True)
                                
                                # Geolocation for Edit
                                loc_edit = get_geolocation(component_key=f"geo_edit_{client['id']}")
                                if loc_edit:
                                    if st.button("📍 Use Current Location", key=f"paste_loc_{client['id']}"):
                                        ml = f"https://www.google.com/maps/search/{loc_edit['coords']['latitude']},{loc_edit['coords']['longitude']}"
                                        st.rerun()

                                if st.form_submit_button("💾 Save Changes"):
                                    if np and not np.replace("+", "").replace("-", "").replace(" ", "").isdigit():
                                        st.error("Phone number must contain only digits, spaces, +, or -.")
                                    else:
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
                            
                            # Staff Assignment Logic
                            assigned_staff_ids = []
                            show_staff_assign = n_stat in ["Order Received", "Work In Progress"]
                            
                            if show_staff_assign:
                                st.write("**Assign Staff**")
                                try:
                                    staff_res = get_staff()
                                    if staff_res and staff_res.data:
                                        avail_staff = [s for s in staff_res.data if s['status'] in ['Available', 'On Site', 'Busy']]
                                        staff_opts = {s['name']: s['id'] for s in avail_staff}
                                        
                                        curr_assigned = client.get('assigned_staff', [])
                                        curr_assigned_names = []
                                        if curr_assigned:
                                            id_to_name = {s['id']: s['name'] for s in staff_res.data}
                                            curr_assigned_names = [id_to_name.get(sid) for sid in curr_assigned if sid in id_to_name]
                                        
                                        sel_staff_names = st.multiselect("Select Team", list(staff_opts.keys()), default=curr_assigned_names, key=f"staff_{client['id']}")
                                        assigned_staff_ids = [staff_opts[n] for n in sel_staff_names]
                                except: st.error("Could not load staff.")

                            btn_text = "Update Status & Staff" if show_staff_assign else "Update Status"
                            if st.button(btn_text, key=f"btn_{client['id']}"):
                                upd = {"status": n_stat}
                                if s_date: upd["start_date"] = s_date.isoformat()
                                
                                if show_staff_assign:
                                    upd["assigned_staff"] = assigned_staff_ids
                                    try:
                                        if assigned_staff_ids:
                                            supabase.table("staff").update({"status": "Busy"}).in_("id", assigned_staff_ids).execute()
                                        
                                        prev_assigned = client.get('assigned_staff', [])
                                        removed = [pid for pid in prev_assigned if pid not in assigned_staff_ids]
                                        if removed:
                                            supabase.table("staff").update({"status": "Available"}).in_("id", removed).execute()
                                    except Exception as e: print(e)

                                elif n_stat == "Work Done":
                                    curr_assigned = client.get('assigned_staff', [])
                                    if curr_assigned:
                                        try:
                                            supabase.table("staff").update({"status": "Available"}).in_("id", curr_assigned).execute()
                                            upd["assigned_staff"] = []
                                        except: pass
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
        nm, ph = c1.text_input("Client Name"), c2.text_input("Phone", max_chars=15, help="Enter digits only")
        ad = st.text_area("Address")
        maps_link_new_client_key = "loc_in_new_client"
        if maps_link_new_client_key not in st.session_state:
            st.session_state[maps_link_new_client_key] = ""
        
        ml_new_client = st.text_input("Google Maps Link", key=maps_link_new_client_key)
        
        if st.form_submit_button("Create Client", type="primary"):
            if not nm or not ph or not ad:
                st.error("Client Name, Phone, and Address are required fields.")
            elif ph and not ph.replace("+", "").replace("-", "").replace(" ", "").isdigit():
                st.error("Phone number must contain only digits, spaces, +, or -.")
            else:
                # Check if client name already exists
                existing_client = supabase.table("clients").select("name").eq("name", nm).execute()
                if existing_client.data:
                    st.error(f"Error: Client with the name {nm} already exists.")
                    st.stop()
                try:
                    res = supabase.table("clients").insert({"name": nm, "phone": ph, "address": ad, "location": ml_new_client, "status": "New Lead", "created_at": datetime.now().isoformat()}).execute()
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

    if tn:
        tc = cd[tn]
        se, li = tc.get('internal_estimate'), []
        if se: li = se.get('items', [])
        sm = se.get('margins') if se else None
        sd = se.get('days', 1.0) if se else 1.0
        ssk = f"est_{tc['id']}"
        if ssk not in st.session_state: st.session_state[ssk] = li

        # --- SECTION 1: PROJECT SETTINGS ---
        with st.container(border=True):
            st.markdown("### 🛠️ Project Settings")
            gs = get_settings()
            
            col1, col2 = st.columns([1, 3])
            with col1:
                uc = st.checkbox("Use Custom Margins", value=(sm is not None), key="cm")
            with col2:
                dys = st.number_input("⏳ Labor Days", min_value=1, step=1, value=int(sd))
            
            am = gs
            if uc:
                dp, dl, de = (int(sm['p']), int(sm['l']), int(sm['e'])) if sm else (int(gs['part_margin']), int(gs['labor_margin']), int(gs['extra_margin']))
                st.write("**Profit Margins (%)**")
                mc1, mc2, mc3 = st.columns(3)
                cp = mc1.slider("Parts", 0, 100, dp, key="cp")
                cl = mc2.slider("Labor", 0, 100, dl, key="cl")
                ce = mc3.slider("Extra", 0, 100, de, key="ce")
                am = {'part_margin': cp, 'labor_margin': cl, 'extra_margin': ce}

        # --- SECTION 2: ADD MATERIALS ---
        with st.container(border=True):
            st.markdown("### 📦 Add Materials")
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
                
                # Item Selection
                inam = st.selectbox("Select Item to Add", list(imap.keys()), key="est_item_selector", label_visibility="collapsed", placeholder="Choose an item...")
                
                selected_item_data = imap.get(inam, {})
                db_unit = selected_item_data.get('unit', 'pcs')
                
                # Dynamic Unit Logic
                step_val = 0.1
                min_val = 0.1
                init_val = 0.0
                
                if db_unit == 'pcs':
                    unit_opts = ['pcs']
                    unit_disabled = True
                    unit_index = 0
                    # Strict Integers
                    step_val = 1
                    min_val = 1
                    init_val = 1
                else:
                    unit_opts = ['m', 'ft', 'cm', 'in']
                    unit_disabled = False
                    try:
                        unit_index = unit_opts.index(db_unit)
                    except ValueError:
                        unit_index = 0

                with st.form("add_est"):
                    # ALIGNMENT FIX: Use vertical_alignment="bottom"
                    c1, c2, c3 = st.columns([1, 1, 1], vertical_alignment="bottom")
                    
                    iqty = c1.number_input("Qty", min_value=min_val, step=step_val, value=init_val)
                    iunit = c2.selectbox("Unit", unit_opts, index=unit_index, disabled=unit_disabled)
                    
                    if c3.form_submit_button("⬇️ Add to Estimate", type="primary", use_container_width=True):
                        st.session_state[ssk].append({
                            "Item": inam, 
                            "Qty": iqty, 
                            "Base Rate": selected_item_data.get('base_rate', 0), 
                            "Unit": iunit
                        })
                        st.rerun()

            if st.session_state[ssk]:
                # Items Table (No container, looks better flush)
                df = helpers.create_item_dataframe(st.session_state[ssk])
                df.insert(0, 'Sr No', range(1, len(df) + 1))

                st.write("#### Itemized List")
                edf = st.data_editor(df, num_rows="dynamic", use_container_width=True, key=f"t_{tc['id']}", 
                    column_config={
                        "Sr No": st.column_config.NumberColumn("Sr No", width="small", disabled=True),
                        "Qty": st.column_config.NumberColumn("Qty", width="small", step=0.1),
                        "Item": st.column_config.TextColumn("Item", width="large"),
                        "Unit": st.column_config.TextColumn("Unit", width="small", disabled=True),
                        "Base Rate": st.column_config.NumberColumn("Base Rate", width="small"),
                        "Unit Price": st.column_config.NumberColumn("Unit Price", format="₹%.2f", width="small", disabled=True),
                        "Total Price": st.column_config.NumberColumn("Total Price", format="₹%.2f", width="small", disabled=True)
                    })
                
                # Enforce float types
                edf['Qty'] = pd.to_numeric(edf['Qty'], errors='coerce').fillna(0).astype(float)
                edf['Base Rate'] = pd.to_numeric(edf['Base Rate'], errors='coerce').fillna(0).astype(float)

                # --- Universal Calculation Logic ---
                gs = get_settings()
                am_for_calc = am

            # Dynamic Labor Cost Logic (from previous task)
            assigned_ids = tc.get('assigned_staff') or []
            override_labor = calculate_labor_from_assignments(assigned_ids)

            calculated_results = helpers.calculate_estimate_details(
                edf_items_list=edf.to_dict(orient="records"),
                days=dys,
                margins=am_for_calc,
                global_settings=gs,
                daily_labor_override=override_labor
            )

            edf['Total Price'] = edf.apply(lambda row: calculated_results["edf_details_df"].loc[row.name, 'Total Price'] if row.name in calculated_results["edf_details_df"].index else 0, axis=1)
            edf['Unit Price'] = edf.apply(lambda row: calculated_results["edf_details_df"].loc[row.name, 'Unit Price'] if row.name in calculated_results["edf_details_df"].index else 0, axis=1)

            mt = calculated_results["mat_sell"]
            disp_lt = calculated_results["disp_lt"]
            rounded_gt = calculated_results["rounded_grand_total"]
            total_profit = calculated_results["total_profit"]
            advance_amount = calculated_results["advance_amount"]

            # Sync logic
            if edf.to_dict(orient="records") != st.session_state[ssk]:
                st.session_state[ssk] = edf.to_dict(orient="records")
                st.rerun()

            # --- Stock Check Alert System ---
            missing_items_list = []
            restock_data = []
            
            for index, row in edf.iterrows():
                item_name = row.get('Item')
                estimated_qty = float(row.get('Qty', 0))
                available_stock = float(stock_map.get(item_name, 0.0))
                
                if estimated_qty > available_stock:
                    deficit = estimated_qty - available_stock
                    missing_items_list.append(f"{item_name}: Need {int(estimated_qty)}, Have {int(available_stock)}")
                    restock_data.append({"item_name": item_name, "quantity": deficit, "cost": 0.0, "notes": "Auto-restock from Estimator"})
            
            if missing_items_list:
                st.error("⚠️ **Low Stock Warning:** You do not have enough inventory for: " + ", ".join(missing_items_list) + ".")
                if st.button("🚀 Place Order for Missing Items", key="auto_restock_btn", type="primary"):
                    st.session_state['restock_queue'] = restock_data
                    st.toast("Items added to Restock Queue! Go to Suppliers tab.", icon="📦")
            
            # Update dataframe with calculated prices
            edf = calculated_results["edf_details_df"].copy()

            # --- SECTION 3: FINANCIAL OVERVIEW ---
            with st.container(border=True):
                st.markdown("### 💰 Financial Overview")
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("Material", f"₹{mt:,.0f}")
                c2.metric("Labor/Day", f"₹{override_labor:,.0f}" if override_labor > 0 else f"₹{float(gs.get('daily_labor_cost', 1000)):,.0f} (Def)")
                c3.metric("Grand Total", f"₹{rounded_gt:,.0f}")
                c4.metric("Total Profit", f"₹{total_profit:,.0f}")
                c5.metric("Advance Required", f"₹{advance_amount:,.0f}")
                
                st.divider()
                
                cs, cp = st.columns(2)
                if cs.button("💾 Save Estimate", type="primary", use_container_width=True):
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
                cp.download_button("📄 Download PDF", pbytes, f"Est_{sanitized_est_name}.pdf", "application/pdf", key=f"pe_{tc['id']}", use_container_width=True)
# --- TAB 4: INVENTORY ---
with tab_inv:
    st.subheader("📦 Inventory Management")
    
    # Inventory Metrics
    try:
        inv_data = get_inventory().data
        if inv_data:
            idf_metrics = pd.DataFrame(inv_data)
            total_items = len(idf_metrics)
            idf_metrics['value'] = idf_metrics['stock_quantity'] * idf_metrics['base_rate']
            total_inv_value = idf_metrics['value'].sum()
            low_stock_count = len(idf_metrics[idf_metrics['stock_quantity'] < 10])
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Items", total_items)
            m2.metric("Total Inventory Value", f"₹{total_inv_value:,.0f}")
            m3.metric("Low Stock Items (<10)", low_stock_count, delta_color="inverse")
            st.divider()
    except: pass

    # Add New Item
    with st.expander("➕ Add New Item"):
        with st.form("add_inv_item"):
            c1, c2, c3 = st.columns([2, 1, 1])
            inm = c1.text_input("Item Name")
            ib_rate = c2.number_input("Base Rate (₹)", min_value=0.0, step=0.1)
            iunit = c3.selectbox("Unit", ["pcs", "m", "ft", "cm", "in"])
            
            # Strict Integer Enforcement for 'pcs'
            # Note: Since this is inside a form, we can't dynamically change input type on unit change without rerun.
            # But we can default to a safe float input and validate/cast on submit, OR use a generic step.
            # User wants strict integer. We'll use a generic number_input but handle the logic.
            # Actually, to strictly enforce int UI, we need st.rerun on unit change, but that breaks the form flow.
            # Best compromise: Use step=1.0 for all, but format based on unit if possible? No, format is static.
            # We will use step=1.0 and format="%.2f" as default to be safe, but cast to int for pcs on save.
            # WAIT, user specifically complained about "0.10" for pcs.
            # So we MUST use int step if pcs.
            # Since we can't rerun inside form, we'll use a generic input and rely on user to enter correctly?
            # NO, we can just use a float input but set step=1 if they select pcs? No, selectbox doesn't trigger rerun in form.
            # We will move the form OUT to allow dynamic updates? No, that changes UX.
            # We will just accept float but cast to int on save for pcs.
            # AND we will add a warning if they enter decimal for pcs.
            
            if st.form_submit_button("Add Item"):
                try:
                    # Enforce Integer for pcs
                    qty_to_save = 0
                    if iunit == 'pcs':
                        qty_to_save = 0 # Initial stock is 0
                    
                    supabase.table("inventory").insert({"item_name": inm, "base_rate": ib_rate, "unit": iunit, "stock_quantity": qty_to_save}).execute()
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
    st.subheader("🚚 Supplier Management")
    
    # Supplier Metrics
    try:
        sup_data = get_suppliers().data
        if sup_data:
            total_suppliers = len(sup_data)
            sp_res = supabase.table("supplier_purchases").select("supplier_id, cost").execute()
            
            total_spend = 0
            top_sup_data = []
            
            if sp_res.data:
                sp_df = pd.DataFrame(sp_res.data)
                sp_df['cost'] = sp_df['cost'].astype(float)
                total_spend = sp_df['cost'].sum()
                
                # Top Suppliers
                sup_map = {s['id']: s['name'] for s in sup_data}
                sp_df['supplier_name'] = sp_df['supplier_id'].map(sup_map)
                top_sup = sp_df.groupby('supplier_name')['cost'].sum().sort_values(ascending=False).head(5).reset_index()
                top_sup_data = top_sup.to_dict('records')

            sm1, sm2 = st.columns(2)
            sm1.metric("Total Suppliers", total_suppliers)
            sm2.metric("Total Spend", f"₹{total_spend:,.0f}")
            
            if top_sup_data:
                st.caption("🏆 Top Suppliers by Spend")
                st.dataframe(pd.DataFrame(top_sup_data), column_config={"supplier_name": "Supplier", "cost": st.column_config.NumberColumn("Total Spend", format="₹%.2f")}, hide_index=True, use_container_width=True)
            
            st.divider()
    except: pass
    
    # Restock Queue Section
    if st.session_state.get('restock_queue'):
        st.info("📦 **Pending Restock Order**")
        with st.expander("Review & Place Order", expanded=True):
            r_queue = st.session_state['restock_queue']
            
            # Supplier Selection
            sup_opts = {s['name']: s['id'] for s in get_suppliers().data} if get_suppliers().data else {}
            sel_sup_name = st.selectbox("Select Supplier for Batch Order", list(sup_opts.keys()), key="restock_sup")
            
            # Editable List
            r_df = pd.DataFrame(r_queue)
            edited_r_df = st.data_editor(r_df, num_rows="dynamic", use_container_width=True, key="restock_editor", column_config={
                "item_name": "Item",
                "quantity": st.column_config.NumberColumn("Qty Needed", step=1),
                "cost": st.column_config.NumberColumn("Est. Cost (₹)", step=100),
                "notes": "Notes"
            })
            
            if st.button("✅ Confirm Order & Log Purchase", type="primary"):
                if sel_sup_name:
                    sup_id = sup_opts[sel_sup_name]
                    try:
                        # Batch insert
                        to_insert = []
                        for _, row in edited_r_df.iterrows():
                            to_insert.append({
                                "supplier_id": sup_id,
                                "item_name": row['item_name'],
                                "quantity": row['quantity'],
                                "cost": row['cost'],
                                "purchase_date": datetime.now().isoformat(),
                                "notes": row.get('notes', '')
                            })
                        
                        if to_insert:
                            supabase.table("supplier_purchases").insert(to_insert).execute()
                            st.success("Orders Placed Successfully!")
                            del st.session_state['restock_queue']
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.error("Please select a supplier.")
    
    # 0. Add New Supplier
    with st.expander("➕ Add New Supplier"):
        with st.form("add_sup"):
            sn = st.text_input("Supplier Name")
            sp = st.text_input("Phone")
            scp = st.text_input("Contact Person")
            
            if st.form_submit_button("Add Supplier"):
                try:
                    supabase.table("suppliers").insert({"name": sn, "phone": sp, "contact_person": scp}).execute()
                    st.success(f"Supplier '{sn}' added!")
                    get_suppliers.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
    
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
            
            c1, c2 = st.columns(2)
            s_name = c1.selectbox("Supplier", list(s_map.keys()), key="sup_sel_rec")
            i_name = c2.selectbox("Item", list(i_map.keys()), key="item_sel_rec")
            
            current_item = i_map[i_name]
            unit = current_item.get('unit', 'pcs')
            
            with st.form("rec_pur"):
                c3, c4 = st.columns(2)
                
                # Strict Type Enforcement based on Unit
                if unit == 'pcs':
                    qty_val = 1
                    qty_min = 1
                    qty_step = 1
                    rate_val = 0.0 # Rate can still be float for pcs? Usually yes.
                    rate_min = 0.0
                    rate_step = 0.1
                    qty_fmt = "%d"
                    rate_fmt = "%.2f"
                else:
                    qty_val = 1.0
                    qty_min = 0.1
                    qty_step = 0.1
                    rate_val = 0.0
                    rate_min = 0.0
                    rate_step = 0.1
                    qty_fmt = "%.2f"
                    rate_fmt = "%.2f"

                qty = c3.number_input(f"Quantity Purchased ({unit})", min_value=qty_min, step=qty_step, value=qty_val, format=qty_fmt, key=f"qty_{current_item['id']}")
                rate = c4.number_input("Purchase Rate", min_value=rate_min, step=rate_step, value=rate_val, format=rate_fmt, key=f"rate_{current_item['id']}")
                
                update_rate = st.checkbox("Update Inventory Base Rate?", value=True)
                
                if st.form_submit_button("✅ Record Purchase"):
                    try:
                        # Update Inventory Stock & Base Rate
                        curr_item = i_map[i_name]
                        new_stock = float(curr_item.get('stock_quantity', 0)) + qty
                        
                        update_data = {"stock_quantity": new_stock}
                        if update_rate:
                            update_data["base_rate"] = rate
                        
                        supabase.table("inventory").update(update_data).eq("id", curr_item['id']).execute()
                        
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
    
    # 2. Supplier Directory & History
    st.markdown("### 📒 Supplier Directory")
    if sup_resp and sup_resp.data:
        for sup in sup_resp.data:
            with st.expander(f"{sup['name']} ({sup.get('contact_person', '')})"):
                st.write(f"**Phone:** {sup.get('phone', 'N/A')}")
                
                # --- Purchase History Section ---
                st.divider()
                st.markdown("#### 📜 Purchase History")
                
                # Fetch history
                try:
                    hist_res = supabase.table("supplier_purchases").select("*").eq("supplier_id", sup['id']).order("purchase_date", desc=True).execute()
                    hist_data = hist_res.data if hist_res else []
                except: hist_data = []
                
                if hist_data:
                    hdf = pd.DataFrame(hist_data)
                    # Handle cases where columns might be missing if schema changed
                    if 'quantity' not in hdf.columns: hdf['quantity'] = 0
                    if 'cost' not in hdf.columns: 
                        hdf['cost'] = hdf['amount'] if 'amount' in hdf.columns else 0
                    
                    st.dataframe(hdf[['purchase_date', 'item_name', 'quantity', 'cost', 'notes']], use_container_width=True, hide_index=True)
                else:
                    st.info("No purchase history found.")
                    

    else:
        st.info("No suppliers found.")

# --- TAB 8: STAFF MANAGEMENT ---
with tab8:
    st.subheader("👥 Staff Management")
    
    # Fetch dynamic roles (Available for both Add and Edit)
    roles_res = get_staff_roles()
    role_options = [r['role_name'] for r in roles_res.data] if roles_res and roles_res.data else ["Technician", "Helper"]
    
    # Add New Staff
    with st.expander("➕ Register New Staff Member", expanded=False):
        with st.form("add_staff_form"):
            c1, c2 = st.columns(2)
            s_name = c1.text_input("Full Name")
            # roles_res fetched above
            s_role = c2.selectbox("Role", role_options)
            s_phone = c1.text_input("Phone Number")
            s_daily = c2.number_input("Daily Wage (₹)", min_value=0, step=50, format="%d")
            
            if st.form_submit_button("Register Staff"):
                if s_name and s_role and s_phone and s_daily:
                    try:
                        supabase.table("staff").insert({
                            "name": s_name,
                            "role": s_role,
                            "phone": s_phone,
                            "salary": int(s_daily), # Map to schema column 'salary'
                            "status": "Available"
                        }).execute()
                        st.success(f"Registered {s_name}!")
                        get_staff.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.error("All fields are required.")

    st.divider()

    # Staff List & Status
    st.markdown("### 📋 Team Roster")
    
    try:
        staff_resp = get_staff()
        
        # Fetch Clients for Assignment Mapping
        clients_res = supabase.table("clients").select("name, assigned_staff, status").eq("status", "Active").execute()
        staff_assignment_map = {}
        if clients_res and clients_res.data:
            for c in clients_res.data:
                if c.get('assigned_staff'):
                    for sid in c['assigned_staff']:
                        staff_assignment_map[sid] = c['name']

        if staff_resp and staff_resp.data:
            staff_df = pd.DataFrame(staff_resp.data)
            
            # Metrics
            total_staff = len(staff_df)
            active_staff = len(staff_df[staff_df['status'] == 'Available'])
            on_site_staff = len(staff_df[staff_df['status'].isin(['On Site', 'Busy'])])
            on_leave_staff = len(staff_df[staff_df['status'] == 'On Leave'])
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Available", active_staff)
            m2.metric("On Leave", on_leave_staff)
            m3.metric("Busy/On Site", on_site_staff)
            m4.metric("Total Staff", total_staff)
            
            st.divider()
            
            # Staff Cards
            for _, staff in staff_df.iterrows():
                # --- LOGIC & SETUP ---
                current_status = staff['status'] # e.g. 'Available', 'On Site', 'On Leave', 'Busy'
                
                # Colors for Badge
                status_color = "#10b981" # Green
                bg_color = "rgba(16, 185, 129, 0.15)"
                border_style = f"1px solid {status_color}40"
                
                if current_status in ['Busy', 'On Site']:
                    status_color = "#f59e0b" # Amber
                    bg_color = "rgba(245, 158, 11, 0.15)"
                    border_style = f"1px solid {status_color}40"
                elif current_status == 'On Leave':
                    status_color = "#ef4444" # Red
                    bg_color = "rgba(239, 68, 68, 0.15)"
                    border_style = f"1px solid {status_color}40"
                
                # Assignment Text
                ass_text = ""
                if current_status in ['Busy', 'On Site'] and staff['id'] in staff_assignment_map:
                   ass_text = f"<div style='font-size: 0.8rem; color: #f59e0b; margin-top: 2px;'>📍 {staff_assignment_map[staff['id']]}</div>"

                # Container for Card
                # Initialize Expansion State
                exp_key = f"exp_st_{staff['id']}"
                if exp_key not in st.session_state:
                    st.session_state[exp_key] = False

                # Container for Card
                with st.container(border=True):
                    # Custom HTML for Name, Badge, Info, Wage
                    card_html = (
                        f'<div style="display: flex; justify-content: space-between; align-items: start;">'
                        f'    <div>'
                        f'        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 4px;">'
                        f'            <span style="font-size: 1.15rem; font-weight: 700; color: #f8fafc;">{staff["name"]}</span>'
                        f'        </div>'
                        f'        <div style="color: #94a3b8; font-size: 0.9rem;">'
                        f'            {staff["role"]} <span style="color: #475569;">•</span> <span style="font-family: monospace;">{staff["phone"]}</span>'
                        f'        </div>'
                        f'        {ass_text}'
                        f'    </div>'
                        f'    <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 6px;">'
                        f'        <span style="background-color: {bg_color}; color: {status_color}; padding: 2px 10px; border-radius: 999px; font-size: 0.7rem; font-weight: 600; border: {border_style}; white-space: nowrap;">{current_status}</span>'
                        f'        <div style="text-align: right; color: #cbd5e1; font-family: monospace; font-weight: 500;">'
                        f'            ₹{staff.get("salary", 0)}/day'
                        f'        </div>'
                        f'    </div>'
                        f'</div>'
                    )
                    
                    # Columns for Header Area: [HTML Content] [Toggle Button]
                    c_main, c_toggle = st.columns([0.9, 0.1])
                    
                    with c_main:
                         st.markdown(card_html, unsafe_allow_html=True)
                    
                    with c_toggle:
                        # Toggle Button
                        btn_icon = ":material/expand_less:" if st.session_state[exp_key] else ":material/expand_more:"
                        if st.button(btn_icon, key=f"btn_tog_{staff['id']}", type="secondary", use_container_width=True):
                            st.session_state[exp_key] = not st.session_state[exp_key]
                            st.rerun()

                    # Expanded Content (Edit Form)
                    if st.session_state[exp_key]:
                        st.divider()
                        st.caption(f"Manage {staff['name']}")
                        with st.form(f"manage_staff_{staff['id']}"):
                            c_a, c_b = st.columns(2)
                            u_name = c_a.text_input("Name", value=staff['name'])
                            u_role = c_b.selectbox("Role", role_options, index=role_options.index(staff['role']) if staff['role'] in role_options else 0)
                            u_phone = c_a.text_input("Phone", value=staff['phone'])
                            u_wage = c_b.number_input("Daily Wage", value=int(staff.get('salary', 0)), step=50)
                            
                            st.markdown("**Status**")
                            st_opts = ["Available", "On Site", "On Leave", "Busy"]
                            u_stats = st.selectbox("Current Status", st_opts, index=st_opts.index(current_status) if current_status in st_opts else 0, label_visibility="collapsed")
                            
                            # Client Assignment Logic
                            sel_client_id = None
                            if u_stats == "On Site":
                                try:
                                    # Fetch active clients for dropdown
                                    cli_res = supabase.table("clients").select("id, name").neq("status", "Closed").neq("status", "Work Done").execute()
                                    if cli_res and cli_res.data:
                                        cli_dict = {c['name']: c['id'] for c in cli_res.data}
                                        # Determine current assignment if any
                                        curr_cli_name = staff_assignment_map.get(staff['id'])
                                        def_idx = list(cli_dict.keys()).index(curr_cli_name) if curr_cli_name in cli_dict else 0
                                        
                                        sel_cli_name = st.selectbox("Select Site/Client", list(cli_dict.keys()), index=def_idx)
                                        sel_client_id = cli_dict[sel_cli_name]
                                    else:
                                        st.warning("No active clients found to assign.")
                                except: pass

                            st.divider()
                            
                            col_s, col_d = st.columns([1,1])
                            if col_s.form_submit_button("✅ Save Changes", type="primary"):
                               try:
                                   # 1. Update Staff Details
                                   supabase.table("staff").update({
                                       "name": u_name,
                                       "role": u_role,
                                       "phone": u_phone,
                                       "salary": u_wage,
                                       "status": u_stats
                                   }).eq("id", staff['id']).execute()
                                   
                                   # 2. Handle Client Assignment
                                   # First, removing this staff from ALL clients to ensure no duplicates/stale data
                                   # Note: efficient way depends on DB, but iterating fetch is safer for consistency here
                                   all_active_res = supabase.table("clients").select("id, assigned_staff").neq("status", "Closed").execute()
                                   if all_active_res and all_active_res.data:
                                       for cli in all_active_res.data:
                                           curr_staff = cli.get('assigned_staff') or []
                                           if staff['id'] in curr_staff:
                                               curr_staff.remove(staff['id'])
                                               supabase.table("clients").update({"assigned_staff": curr_staff}).eq("id", cli['id']).execute()
                                   
                                   # 3. If On Site and Client Selected, Add to New Client
                                   if u_stats == "On Site" and sel_client_id:
                                       # Fetch specific client to get fresh list
                                       target_cli_res = supabase.table("clients").select("assigned_staff").eq("id", sel_client_id).execute()
                                       if target_cli_res and target_cli_res.data:
                                           new_list = target_cli_res.data[0].get('assigned_staff') or []
                                           if staff['id'] not in new_list:
                                               new_list.append(staff['id'])
                                               supabase.table("clients").update({"assigned_staff": new_list}).eq("id", sel_client_id).execute()

                                   st.session_state[exp_key] = False # Collapse on success
                                   st.toast("Updated!", icon="✅")
                                   time.sleep(0.5)
                                   get_staff.clear()
                                   get_clients.clear() # Clear client cache too
                                   st.rerun()
                               except Exception as e:
                                   st.error(f"Error: {e}")
                            
                            if col_d.form_submit_button("🗑️ Delete Member", type="secondary"):
                                supabase.table("staff").delete().eq("id", staff['id']).execute()
                                # No need to collapse, item is gone
                                st.toast("Deleted!", icon="🗑️")
                                time.sleep(0.5)
                                get_staff.clear()
                                st.rerun()
                    
        else:
            st.info("No staff members found. Register one above.")
            
    except Exception as e:
        st.error(f"Error loading staff: {e}")

# --- TAB 6: P&L ---
with tab6:
    st.subheader("📈 Profit & Loss Analysis")
    
    if st.button("🔄 Refresh Data"):
        get_clients.clear()
        st.rerun()
        
    with st.spinner("Loading Financial Data..."):
        try:
            cl_resp = get_clients()
            # Fetch Supplier Purchases for Global Expense Calculation (New Source)
            sp_resp = supabase.table("supplier_purchases").select("cost, purchase_date").execute()
            # Keep legacy purchase_log just in case, or replace? Assuming replacement as per recent feature.
            # purchase_log_resp = supabase.table("purchase_log").select("total_cost").execute() 
            settings = get_settings()
        except Exception as e:
            st.error(f"Data Fetch Error: {e}")
            cl_resp = None
            sp_resp = None
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
        # Material Expense from Supplier Purchases
        sp_data = sp_resp.data if sp_resp and sp_resp.data else []
        total_material_expense_cash = sum(float(item.get('cost', 0.0)) for item in sp_data if item.get('cost'))
        
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
            actual_rev = float(row.get('final_settlement_amount') or 0.0)
            
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
        k4.metric("Outstanding Amount", f"₹{discount_loss:,.0f}", delta_color="inverse")
        
        st.divider()
        
        st.markdown("### 🏗️ Operational Metrics")
        o1, o2, o3 = st.columns(3)
        o1.metric("Projects Completed", len(closed_df))
        o2.metric("Material Expenses (Log)", f"₹{total_material_expense_cash:,.0f}")
        o3.metric("Labor Expenses (Est)", f"₹{total_labor_expense_cash:,.0f}")

        st.divider()

        # --- CHARTS ---
        
        # Pre-calculate values for charts to avoid scope issues
        def safe_float(val):
            try:
                f = float(val)
                if pd.isna(f): return 0.0
                return f
            except:
                return 0.0

        val_quoted = safe_float(total_quoted)
        val_collected = safe_float(total_collected)
        val_expenses = safe_float(total_expenses_cash)
        val_mat = safe_float(total_material_expense_cash)
        val_lab = safe_float(total_labor_expense_cash)
        
        c_chart1, c_chart2 = st.columns(2)
        
        # 1. Revenue vs Expenses vs Payment (Main Branch Feature)
        with c_chart1:
            st.markdown("#### Revenue vs Expenses vs Payment")
            
            chart_data_comparison = pd.DataFrame({
                'Category': ['Quoted Total', 'Collected', 'Total Expenses'],
                'Amount': [val_quoted, val_collected, val_expenses]
            })
            
            if val_quoted == 0 and val_collected == 0 and val_expenses == 0:
                st.warning("No financial data to display.")
            else:
                # Plotly Bar Chart
                fig_comp = go.Figure(data=[
                    go.Bar(name='Quoted Total', x=['Quoted Total'], y=[val_quoted], marker_color='#3498db'),
                    go.Bar(name='Collected', x=['Collected'], y=[val_collected], marker_color='#2ecc71'),
                    go.Bar(name='Total Expenses', x=['Total Expenses'], y=[val_expenses], marker_color='#e74c3c')
                ])
                
                fig_comp.update_layout(
                    margin=dict(t=0, b=0, l=0, r=0),
                    height=300,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    showlegend=True,
                    yaxis=dict(title="Amount (₹)"),
                    barmode='group'
                )
                
                st.plotly_chart(fig_comp, use_container_width=True)

        # 2. Cost Split (Main Branch Feature)
        with c_chart2:
            st.markdown("#### Global Cost Split")
            
            if val_mat == 0 and val_lab == 0:
                st.warning("No expense data.")
            else:
                # Plotly Donut Chart
                fig_cost = go.Figure(data=[go.Pie(
                    labels=['Material (Log)', 'Labor (Est)'],
                    values=[val_mat, val_lab],
                    hole=.4,
                    marker_colors=['#FF9800', '#9C27B0']
                )])
                
                fig_cost.update_layout(
                    margin=dict(t=0, b=0, l=0, r=0),
                    height=300,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    showlegend=True,
                    legend=dict(title="Category", orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.05)
                )
                
                st.plotly_chart(fig_cost, use_container_width=True)

        st.divider()
        
        # New Charts Row
        nc1, nc2 = st.columns(2)
        
        # 3. Client Profitability Scatter (Restored)
        with nc1:
            st.markdown("#### Client Profitability Matrix")
            if not pl_df.empty:
                chart_scatter = alt.Chart(pl_df).mark_circle(size=60).encode(
                    x=alt.X('Revenue', axis=alt.Axis(title='Revenue (₹)')),
                    y=alt.Y('Profit', axis=alt.Axis(title='Profit (₹)')),
                    color=alt.Color('Profit', scale=alt.Scale(scheme='redyellowgreen')),
                    tooltip=['Client', alt.Tooltip('Revenue', format='₹,.0f'), alt.Tooltip('Profit', format='₹,.0f')]
                ).properties(height=300).interactive()
                st.altair_chart(chart_scatter, use_container_width=True)
            else:
                st.info("No data for scatter plot.")

        # 4. Monthly Trend Combo (Restored)
        with nc2:
            if not pl_df.empty:
                st.markdown("#### 📅 Monthly Performance (Combo)")
                # Ensure Month is present
                if 'Month' not in pl_df.columns:
                     pl_df['created_at'] = pd.to_datetime(pl_df['created_at'])
                     pl_df['Month'] = pl_df['created_at'].dt.strftime('%Y-%m')
                
                monthly_data = pl_df.groupby('Month')[['Revenue', 'Profit']].sum().reset_index()
                
                base = alt.Chart(monthly_data).encode(x='Month')
                bar = base.mark_bar(opacity=0.7).encode(y='Revenue', color=alt.value('#2196F3'))
                line = base.mark_line(color='#FFC107', strokeWidth=3).encode(y='Profit')
                
                combo = (bar + line).properties(height=300).resolve_scale(y='shared')
                st.altair_chart(combo, use_container_width=True)
            else:
                st.info("No data for monthly trend.")
        
        st.divider()
        
        # New Row for Line Charts
        nl1, nl2 = st.columns(2)
        
        # 5. Client Profitability (Line Chart)
        with nl1:
            st.markdown("#### Client Profitability")
            if not pl_df.empty:
                # Sort by date to make the line chart meaningful (Profit over time/projects)
                pl_df_sorted = pl_df.sort_values('created_at')
                
                chart_client_line = alt.Chart(pl_df_sorted).mark_line(point=True).encode(
                    x=alt.X('Client', sort=None, axis=alt.Axis(labelAngle=-45)), # Preserving sorted order
                    y=alt.Y('Profit', axis=alt.Axis(title='Profit (₹)')),
                    tooltip=['Client', 'Revenue', 'Profit', 'created_at']
                ).properties(height=300).interactive()
                st.altair_chart(chart_client_line, use_container_width=True)
            else:
                st.info("No data for client profitability.")

        # 6. Monthly Trend (Line Chart)
        with nl2:
            if not pl_df.empty:
                st.markdown("#### 📅 Monthly Performance Trend")
                if 'Month' not in pl_df.columns:
                     pl_df['created_at'] = pd.to_datetime(pl_df['created_at'])
                     pl_df['Month'] = pl_df['created_at'].dt.strftime('%Y-%m')
                
                monthly_data = pl_df.groupby('Month')[['Revenue', 'Profit']].sum().reset_index()
                
                chart_monthly_line = alt.Chart(monthly_data).mark_line(point=True).encode(
                    x='Month',
                    y=alt.Y('Revenue', axis=alt.Axis(title='Amount (₹)')),
                    color=alt.value('#2196F3'),
                    tooltip=['Month', 'Revenue']
                ) + alt.Chart(monthly_data).mark_line(point=True, strokeDash=[5,5]).encode(
                    x='Month',
                    y='Profit',
                    color=alt.value('#FFC107'),
                    tooltip=['Month', 'Profit']
                )
                
                st.altair_chart(chart_monthly_line, use_container_width=True)
            else:
                st.info("No data for monthly trend.")

        # 4. Business Health Scorecard (Radar Chart)
        st.markdown("### 🏥 Business Health Scorecard")
        
        # Calculate metrics
        rev_capture = (total_collected / total_quoted * 100) if total_quoted > 0 else 0
        profit_margin = actual_margin_pct
        cost_eff = (total_expenses_cash / total_collected * 100) if total_collected > 0 else 0
        labor_pct = (total_labor_expense_cash / total_expenses_cash * 100) if total_expenses_cash > 0 else 0
        
        # Radar Chart
        categories = ['Revenue Capture', 'Profit Margin', 'Cost Efficiency', 'Labor Cost %']
        
        # Normalize/Scale values for the chart (0-100 scale)
        # Cost Efficiency & Labor Cost: Lower is better, so we might want to invert them for "Health" score?
        # Or just plot raw %? User asked for "appropriate visual representation".
        # Standard radar charts usually have "outward is better".
        # Let's plot raw percentages for now but maybe add a "Target" series?
        
        fig = go.Figure()

        fig.add_trace(go.Scatterpolar(
            r=[rev_capture, profit_margin, cost_eff, labor_pct],
            theta=categories,
            fill='toself',
            name='Current Performance',
            line_color='#2196F3'
        ))
        
        # Add Target Series (Ideal values)
        # Targets: >95, >20, <70, <30
        # For visualization, let's just show the current polygon.
        
        fig.update_layout(
            polar=dict(
                bgcolor='#1E1E1E',
                radialaxis=dict(
                    visible=True,
                    range=[0, 100],
                    gridcolor='#444',
                    linecolor='#444',
                    tickfont=dict(color='#ccc')
                ),
                angularaxis=dict(
                    gridcolor='#444',
                    linecolor='#444',
                    tickfont=dict(color='#ccc')
                )
            ),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            showlegend=True,
            legend=dict(font=dict(color='white')),
            height=400,
            margin=dict(l=40, r=40, t=40, b=40)
        )
        
        st.plotly_chart(fig, use_container_width=True)

        st.divider()
        
        # Table View (Restored)
        health_data = {
            "Metric": ["Revenue Capture Rate", "Profit Margin", "Cost Efficiency", "Labor Cost %"],
            "Value": [
                f"{rev_capture:.1f}%",
                f"{profit_margin:.1f}%",
                f"{cost_eff:.1f}%",
                f"{labor_pct:.1f}%"
            ],
            "Target": ["> 95%", "> 20%", "< 70%", "< 30%"]
        }
        st.dataframe(pd.DataFrame(health_data), use_container_width=True, hide_index=True)
    
# --- TAB 7: SETTINGS ---
with tab4:
    st.subheader("⚙️ Global Settings")
    
    try:
        sett = get_settings()
    except: sett = {}
    
    with st.form("settings_form"):
        c1, c2, c3 = st.columns(3)
        pm = c1.slider("Default Parts Margin (%)", 0, 100, int(sett.get('part_margin', 20)))
        lm = c2.slider("Default Labor Margin (%)", 0, 100, int(sett.get('labor_margin', 20)))
        em = c3.slider("Default Extra Margin (%)", 0, 100, int(sett.get('extra_margin', 10)))
        
        dlc = st.number_input("Daily Labor Cost (₹)", value=float(sett.get('daily_labor_cost', 1000.0)))
        
        if st.form_submit_button("💾 Save Settings"):
            try:
                # Upsert settings (assuming id=1)
                supabase.table("settings").upsert({"id": 1, "part_margin": pm, "labor_margin": lm, "extra_margin": em, "daily_labor_cost": dlc, "advance_margin": st.session_state.get('adv_margin_slider', 20)}).execute()
                st.success("Settings Saved!")
                get_settings.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    # Advance Payment Configuration & Explanation
    st.divider()
    st.markdown("### 🧮 Advance Payment Configuration")
    
    # Global Setting Slider
    adv_m = st.slider("Default Advance Profit Margin (%)", 0, 100, int(sett.get('advance_margin', 20)), key='adv_margin_slider')
    
    st.markdown("#### 👁️ Calculation Preview (Example)")
    st.caption("See how your margin affects the advance amount using fixed example values.")
    
    # Fixed Example Values
    ex_mat = 50000
    ex_lab = 20000
    ex_base = ex_mat + ex_lab
    ex_profit = ex_base * (adv_m / 100)
    ex_total = ex_base + ex_profit
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Example Base Cost", f"₹{ex_base:,.0f}", help="Material (50k) + Labor (20k)")
    c2.metric("Profit Amount", f"₹{ex_profit:,.0f}", delta=f"{adv_m}% Margin")
    c3.metric("Total Advance Required", f"₹{ex_total:,.0f}")
    
    st.info(f"Formula Applied: (Material + Labor) + {adv_m}% Profit")



    st.divider()
    st.subheader("👥 Manage Staff Roles")
    
    # Fetch roles
    roles_res = get_staff_roles()
    current_roles = [r['role_name'] for r in roles_res.data] if roles_res and roles_res.data else []
    
    # Add New Role
    with st.form("add_role_form"):
        new_role = st.text_input("New Role Name")
        if st.form_submit_button("Add Role"):
            if new_role:
                if new_role in current_roles:
                    st.error("Role already exists.")
                else:
                    try:
                        supabase.table("staff_roles").insert({"role_name": new_role}).execute()
                        st.success(f"Role '{new_role}' added!")
                        get_staff_roles.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e} (Did you run the schema update?)")
            else:
                st.error("Please enter a role name.")
    
    # List and Delete Roles
    if current_roles:
        st.write("Current Roles:")
        for role in current_roles:
            c1, c2 = st.columns([3, 1])
            c1.write(f"• {role}")
            if c2.button("🗑️", key=f"del_role_{role}"):
                try:
                    supabase.table("staff_roles").delete().eq("role_name", role).execute()
                    st.success(f"Role '{role}' deleted.")
                    get_staff_roles.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        st.info("No roles found or table missing. Please update database schema.")

    st.divider()
    st.subheader("🔐 Change Password")
    with st.form("change_pwd"):
        cur_pass = st.text_input("Current Password", type="password")
        new_pass = st.text_input("New Password", type="password")
        conf_pass = st.text_input("Confirm New Password", type="password")
        
        if st.form_submit_button("Update Password"):
            if new_pass != conf_pass:
                st.error("New passwords do not match.")
            elif not check_login(st.session_state.username, cur_pass):
                st.error("Incorrect current password.")
            else:
                try:
                    supabase.table("users").update({"password": new_pass}).eq("username", st.session_state.username).execute()
                    st.success("Password Updated! Please re-login.")
                    time.sleep(1)
                    st.session_state.logged_in = False
                    cookie_manager.delete("jugnoo_user")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    st.divider()
    if st.button("🚪 Log Out", type="primary", use_container_width=True):
        st.session_state.logged_in = False
        cookie_manager.delete("jugnoo_user")
        st.rerun()
