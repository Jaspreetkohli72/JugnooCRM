import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime, timedelta
import time
import math
from fpdf import FPDF
from streamlit_js_eval import get_geolocation
import extra_streamlit_components as stx

# ---------------------------
# 1. SETUP & CONNECTION
# ---------------------------
st.set_page_config(page_title="Jugnoo", page_icon="🏗️", layout="wide")

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
# 2. AUTHENTICATION
# ---------------------------
def get_manager():
    return stx.CookieManager(key="auth_cookie_manager")

cookie_manager = get_manager()

def check_login(username, password):
    try:
        res = supabase.table("users").select("*").eq("username", username).eq("password", password).execute()
        return len(res.data) > 0
    except:
        return False

def login_section():
    st.title("🔒 Jugnoo")
    time.sleep(0.1)
    cookie_user = cookie_manager.get(cookie="jugnoo_user")
    if cookie_user:
        st.session_state.logged_in = True
        st.session_state.username = cookie_user
        return 
    if st.session_state.get('logged_in'): return

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
                    st.success("Success!")
                    st.rerun()
                else:
                    st.error("Invalid Credentials")
    st.stop()

login_section()

# ---------------------------
# 3. HELPER FUNCTIONS
# ---------------------------
def run_query(query_func):
    try:
        return query_func.execute()
    except Exception as e:
        st.error(f"Database Error: {e}")
        return None

def get_settings():
    defaults = {"part_margin": 15.0, "labor_margin": 20.0, "extra_margin": 5.0, "daily_labor_cost": 1000.0}
    try:
        response = run_query(supabase.table("settings").select("*").eq("id", 1))
        if response and response.data:
            db_data = response.data[0]
            return {k: db_data.get(k, v) for k, v in defaults.items()}
    except:
        pass
    return defaults

# --- PROFESSIONAL PDF GENERATOR ---
def create_pdf(client_name, items, labor_days, labor_total, grand_total, advance_amount):
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font("Arial", 'B', 20)
    pdf.cell(0, 10, "Jugnoo", ln=True, align='L')
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(0, 6, "Smart Automation Solutions", ln=True, align='L')
    pdf.line(10, 28, 200, 28)
    pdf.ln(15)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, f"Estimate For: {client_name}", ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 8, f"Date: {datetime.now().strftime('%d-%b-%Y')}", ln=True)
    pdf.ln(5)
    
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(100, 10, "Description", 1, 0, 'L', 1)
    pdf.cell(15, 10, "Qty", 1, 0, 'C', 1)
    pdf.cell(15, 10, "Unit", 1, 0, 'C', 1)
    pdf.cell(60, 10, "Amount (INR)", 1, 1, 'R', 1)
    
    pdf.set_font("Arial", '', 10)
    for item in items:
        pdf.cell(100, 8, str(item.get('Item', '')), 1)
        pdf.cell(15, 8, str(item.get('Qty', 0)), 1, 0, 'C')
        pdf.cell(15, 8, str(item.get('Unit', '')), 1, 0, 'C')
        pdf.cell(60, 8, f"{item.get('Total Price', 0):,.2f}", 1, 1, 'R')
        
    pdf.set_font("Arial", '', 10)
    pdf.cell(130, 8, f"Labor / Installation ({labor_days} Days)", 1, 0, 'R')
    pdf.cell(60, 8, f"{labor_total:,.2f}", 1, 1, 'R')
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(130, 10, "Grand Total", 1, 0, 'R')
    pdf.cell(60, 10, f"Rs. {grand_total:,.2f}", 1, 1, 'R')
    
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 10)
    pdf.multi_cell(0, 5, f"Advance Payment Required: Rs. {advance_amount:,.2f}")
    pdf.ln(5)
    pdf.set_font("Arial", 'I', 8)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 5, "NOTE: This is an estimate only. Final rates may vary based on actual site conditions and market fluctuations. Valid for 7 days.")
    
    return pdf.output(dest='S').encode('latin-1')

def create_internal_pdf(client_name, items, labor_days, labor_cost, labor_charged, grand_total, total_profit):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "INTERNAL PROFIT REPORT (CONFIDENTIAL)", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 10, f"Client: {client_name} | Date: {datetime.now().strftime('%Y-%m-%d')}", ln=True)
    pdf.ln(5)

    pdf.set_fill_color(220, 220, 220)
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(70, 8, "Item Description", 1, 0, 'L', 1)
    pdf.cell(15, 8, "Qty", 1, 0, 'C', 1)
    pdf.cell(35, 8, "Base Rate", 1, 0, 'R', 1)
    pdf.cell(35, 8, "Sold At", 1, 0, 'R', 1)
    pdf.cell(35, 8, "Profit", 1, 1, 'R', 1)

    pdf.set_font("Arial", '', 9)
    for item in items:
        qty = float(item.get('Qty', 0))
        base = float(item.get('Base Rate', 0))
        total_sell = float(item.get('Total Price', 0))
        unit_sell = total_sell / qty if qty > 0 else 0
        row_profit = total_sell - (base * qty)
        
        pdf.cell(70, 8, str(item.get('Item', ''))[:35], 1)
        pdf.cell(15, 8, str(qty), 1, 0, 'C')
        pdf.cell(35, 8, f"{base:,.2f}", 1, 0, 'R')
        pdf.cell(35, 8, f"{unit_sell:,.2f}", 1, 0, 'R')
        pdf.set_text_color(0, 150, 0); pdf.cell(35, 8, f"{row_profit:,.2f}", 1, 1, 'R'); pdf.set_text_color(0, 0, 0)

    labor_profit = labor_charged - labor_cost
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(120, 8, f"Labor ({labor_days} Days)", 1, 0, 'R')
    pdf.cell(35, 8, f"Cost: {labor_cost:,.2f}", 1, 0, 'R')
    pdf.cell(35, 8, f"Chrg: {labor_charged:,.2f}", 1, 1, 'R')

    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(120, 10, "TOTAL REVENUE:", 1, 0, 'R')
    pdf.cell(70, 10, f"Rs. {grand_total:,.2f}", 1, 1, 'R')
    pdf.cell(120, 10, "NET PROFIT:", 1, 0, 'R')
    pdf.set_text_color(0, 150, 0); pdf.cell(70, 10, f"Rs. {total_profit:,.2f}", 1, 1, 'R')

    return pdf.output(dest='S').encode('latin-1')

# ---------------------------
# 4. MAIN UI
# ---------------------------


if not supabase: st.stop()

# Top Bar
top_c1, top_c2 = st.columns([10, 2])
top_c1.write(f"👤 Logged in as: **{st.session_state.username}**")
if top_c2.button("Log Out", type="secondary"):
    st.session_state.logged_in = False
    cookie_manager.delete("jugnoo_user")
    st.rerun()
st.divider()

tab1, tab2, tab3, tab5, tab4 = st.tabs(["📋 Dashboard", "➕ New Client", "🧮 Estimator", "🚚 Suppliers", "⚙️ Settings"])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.subheader("Client Projects")
    
    status_filter = st.radio(
        "Filter by Status",
        ('All', 'Active', 'Inactive'),
        horizontal=True,
        key="status_filter_radio"
    )

    response = run_query(supabase.table("clients").select("*").order("created_at", desc=True))
    
    if response and response.data:
        df = pd.DataFrame(response.data)

        # Define active and inactive statuses
        active_statuses = ["Estimate Given", "Order Received", "Work In Progress"]
        inactive_statuses = ["Work Done", "Closed"]
        
        # Apply filter based on radio button selection
        if status_filter == 'Active':
            df = df[df['status'].isin(active_statuses)]
        elif status_filter == 'Inactive':
            df = df[df['status'].isin(inactive_statuses)]

        st.dataframe(df[[c for c in ['name', 'status', 'start_date', 'phone', 'address'] if c in df.columns]], use_container_width=True, hide_index=True)
        st.divider()
        
        client_map = {c['name']: c for c in response.data}
        sel_name = st.selectbox("Select Client to Manage", list(client_map.keys()), index=None, key="dash_sel")
        
        if sel_name:
            client = client_map[sel_name]
            st.markdown("### 🛠️ Manage Client")
            c1, c2 = st.columns([1.5, 1])
            with c1:
                st.write("**Edit Details**")
                loc = get_geolocation(component_key=f"geo_tab1_{client['id']}")
                gmaps = ""
                if loc:
                    st.write(f"Detected: {loc['coords']['latitude']}, {loc['coords']['longitude']}")
                    if st.button("Paste Location", key=f"paste_loc_tab1_{client['id']}"):
                        gmaps = f"http://googleusercontent.com/maps.google.com/?q={loc['coords']['latitude']},{loc['coords']['longitude']}"
                        st.session_state[f"loc_in_dash_{client['id']}"] = gmaps
                
                with st.form("edit_details"):
                    nn, np, na = st.text_input("Name", value=client['name']), st.text_input("Phone", value=client.get('phone', '')), st.text_area("Address", value=client.get('address', ''))
                    maps_link_key = f"loc_in_dash_{client['id']}"
                    current_maps_link = client.get('location', '') # Changed from maps_link to location
                    if maps_link_key in st.session_state:
                        current_maps_link = st.session_state[maps_link_key]
                    ml = st.text_input("Maps Link", value=current_maps_link, key=maps_link_key)
                    if client.get('location'):
                        st.link_button("🚀 Open Location in Maps", url=client['location'], use_container_width=True)

                    if st.form_submit_button("💾 Save Changes"):
                        res = run_query(supabase.table("clients").update({"name": nn, "phone": np, "address": na, "location": ml}).eq("id", client['id'])) # Changed from maps_link to location
            with c2:
                st.write("**Project Status**")
                opts = ["Estimate Given", "Order Received", "Work In Progress", "Work Done", "Closed"]
                try: idx = opts.index(client.get('status'))
                except: idx = 0
                n_stat = st.selectbox("Status", opts, index=idx, key=f"st_{client['id']}")
                s_date = None
                if n_stat in ["Order Received", "Work In Progress", "Work Done"]:
                    d_str = client.get('start_date')
                    def_d = datetime.strptime(d_str, '%Y-%m-%d').date() if d_str else datetime.now().date()
                    s_date = st.date_input("📅 Start Date", value=def_d)
                if st.button("Update Status", key=f"btn_{client['id']}"):
                    upd = {"status": n_stat}
                    if s_date: upd["start_date"] = s_date.isoformat()
                    res = run_query(supabase.table("clients").update(upd).eq("id", client['id']))
                    if res and res.data: st.success("Status Saved!"); time.sleep(0.5); st.rerun()

            st.expander("Danger Zone").button("Delete Client", type="secondary", use_container_width=True, on_click=lambda: run_query(supabase.table("clients").delete().eq("id", client['id'])), key=f"del_{client['id']}")
            if st.session_state.get(f"del_{client['id']}"): # Check if button was clicked
                st.success("Client Deleted!"); time.sleep(1); st.rerun()

            if client.get('internal_estimate'):
                st.divider()
                st.subheader("📄 Manage Estimate")
                est_data = client['internal_estimate']
                s_items, s_days = est_data.get('items', []), est_data.get('days', 1.0)
                
                ssk_dash = f"dash_est_{client['id']}"
                if ssk_dash not in st.session_state:
                    st.session_state[ssk_dash] = s_items

                if st.session_state[ssk_dash]:
                    idf = pd.DataFrame(st.session_state[ssk_dash])
                    for col in ["Qty", "Item", "Unit", "Base Rate", "Total Price", "Unit Price"]:
                        if col not in idf.columns: idf[col] = "" if col in ["Item", "Unit"] else 0.0
                    
                    column_order = ['Qty', 'Item', 'Unit', 'Base Rate', 'Unit Price', 'Total Price']
                    idf = idf.reindex(columns=column_order, fill_value="")

                    edited_est = st.data_editor(idf, num_rows="dynamic", use_container_width=True, key=f"de_{client['id']}",
                                                column_config={
                                                    "Qty": st.column_config.NumberColumn("Qty", width="small", step=1),
                                                    "Item": st.column_config.TextColumn("Item", width="large"),
                                                    "Unit": st.column_config.SelectboxColumn("Unit", options=["pcs", "m", "cm", "in", "ft"], width="small", required=True),
                                                    "Base Rate": st.column_config.NumberColumn("Base Rate", width="small"),
                                                    "Unit Price": st.column_config.NumberColumn("Unit Price", format="₹%.2f", width="small", disabled=True),
                                                    "Total Price": st.column_config.NumberColumn("Total Price", width="small", disabled=True)
                                                })

                    # --- Universal Calculation Logic ---
                    s_margins = est_data.get('margins')
                    gs = get_settings()
                    am = s_margins if s_margins else gs
                    
                    CONVERSIONS = {'pcs': 1.0, 'each': 1.0, 'm': 1.0, 'cm': 0.01, 'ft': 0.3048, 'in': 0.0254}
                    mm = 1 + (am.get('part_margin', 0)/100) + (am.get('labor_margin', 0)/100) + (am.get('extra_margin', 0)/100)

                    def calc_total(row):
                        try:
                            qty = float(row.get('Qty', 0))
                            base = float(row.get('Base Rate', 0))
                            unit = row.get('Unit', 'pcs')
                            factor = CONVERSIONS.get(unit, 1.0)
                            
                            if unit in ['m', 'cm', 'ft', 'in']:
                                return base * (qty * factor) * mm
                            else:
                                return base * qty * mm
                        except (ValueError, TypeError):
                            return 0.0

                    edited_est['Total Price'] = edited_est.apply(calc_total, axis=1)
                    edited_est['Unit Price'] = edited_est['Total Price'] / edited_est['Qty'].replace(0, 1)

                    if edited_est.to_dict(orient="records") != st.session_state[ssk_dash]:
                        st.session_state[ssk_dash] = edited_est.to_dict(orient="records")
                        st.rerun()

                    mat_sell = edited_est['Total Price'].sum()
                    daily_cost = float(gs.get('daily_labor_cost', 1000))
                    labor_actual_cost = float(s_days) * daily_cost
                    # Calculate total base cost considering unit conversions
                    def calculate_item_base_cost(row):
                        qty = float(row.get('Qty', 0))
                        base_rate = float(row.get('Base Rate', 0))
                        unit = row.get('Unit', 'pcs')
                        factor = CONVERSIONS.get(unit, 1.0)
                        return base_rate * qty * factor

                    total_material_base_cost = edited_est.apply(calculate_item_base_cost, axis=1).sum()
                    total_base_cost = total_material_base_cost + labor_actual_cost
                    raw_grand_total = mat_sell + labor_actual_cost
                    rounded_grand_total = math.ceil(raw_grand_total / 100) * 100
                    total_profit = rounded_grand_total - total_base_cost
                    advance_amount = math.ceil((total_base_cost + (total_profit * 0.10)) / 100) * 100
                    labor_charged_display = labor_actual_cost + (rounded_grand_total - raw_grand_total)
                    
                    m1, m2, m3, m4, m5 = st.columns(5)
                    m1.metric("Material Total", f"₹{mat_sell:,.0f}"); m2.metric("Labor", f"₹{labor_charged_display:,.0f}"); m3.metric("Grand Total", f"₹{rounded_grand_total:,.0f}"); m4.metric("Total Profit", f"₹{total_profit:,.0f}"); m5.metric("Advance Required", f"₹{advance_amount:,.0f}")
                    
                    if st.button("💾 Save Changes", key=f"sv_{client['id']}"):
                        df_to_save = edited_est.copy()
                        for col in ['Qty', 'Base Rate', 'Total Price', "Unit Price"]:
                            df_to_save[col] = pd.to_numeric(df_to_save[col].fillna(0))
                        for col in ['Item', 'Unit']: df_to_save[col] = df_to_save[col].fillna("")
                        new_json = {"items": df_to_save.to_dict(orient="records"), "days": s_days, "margins": est_data.get('margins')}
                        run_query(supabase.table("clients").update({"internal_estimate": new_json}).eq("id", client['id']))
                        st.toast("Saved!", icon="✅")
                    
                    st.write("#### 📥 Download Bills")
                    c_pdf1, c_pdf2 = st.columns(2)
                    pdf_client = create_pdf(client['name'], edited_est.to_dict(orient="records"), s_days, labor_charged_display, rounded_grand_total, advance_amount)
                    c_pdf1.download_button("📄 Client Invoice", pdf_client, f"Invoice_{client['name']}.pdf", "application/pdf", key=f"pdf_c_{client['id']}")
                    st.write("#### Internal Profit Analysis")
                    if client.get('status') == "Work Done":
                        df_profit = edited_est.copy()
                        df_profit['Qty'] = pd.to_numeric(df_profit['Qty'].fillna(0))
                        df_profit['Base Rate'] = pd.to_numeric(df_profit['Base Rate'].fillna(0))
                        df_profit['Total Price'] = pd.to_numeric(df_profit['Total Price'].fillna(0))
                        
                        df_profit['Total Sell Price'] = df_profit['Total Price'] # Use existing Total Price as Total Sell Price
                        
                        def calculate_profit_row(row):
                            qty = float(row.get('Qty', 0))
                            base_rate = float(row.get('Base Rate', 0))
                            unit = row.get('Unit', 'pcs')
                            total_sell = float(row.get('Total Sell Price', 0)) # Use Total Sell Price here
                            
                            factor = CONVERSIONS.get(unit, 1.0)
                            total_cost = base_rate * qty * factor
                            return total_sell - total_cost

                        df_profit['Row Profit'] = df_profit.apply(calculate_profit_row, axis=1)
                        
                        # Apply formatting
                        df_profit['Base Rate'] = df_profit['Base Rate'].round(2)
                        df_profit['Total Sell Price'] = df_profit['Total Sell Price'].round(2)
                        df_profit['Row Profit'] = df_profit['Row Profit'].round(2)

                        st.dataframe(df_profit[['Item', 'Qty', 'Unit', 'Base Rate', 'Total Sell Price', 'Row Profit']], use_container_width=True, hide_index=True)
                        st.metric("Net Profit (from Grand Total)", f"₹{total_profit:,.0f}")
                    else: 
                        st.info("Mark status as 'Work Done' to view Internal Profit Analysis.")

                else: st.warning("Estimate Empty")

# --- TAB 2: NEW CLIENT ---
with tab2:
    st.subheader("Add New Client")
    
    loc_new_client = get_geolocation(component_key="geo_tab2_new_client")
    gmaps_new_client = ""
    if loc_new_client:
        st.write(f"Detected: {loc_new_client['coords']['latitude']}, {loc_new_client['coords']['longitude']}")
        if st.button("Paste Location to Form", key="paste_loc_tab2_new_client"):
            gmaps_new_client = f"http://googleusercontent.com/maps.google.com/?q={loc_new_client['coords']['latitude']},{loc_new_client['coords']['longitude']}"
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
            res = run_query(supabase.table("clients").insert({"name": nm, "phone": ph, "address": ad, "location": ml_new_client, "status": "Estimate Given", "created_at": datetime.now().isoformat()})) # Changed from maps_link to location
            if res and res.data: st.success(f"Client {nm} Added!"); time.sleep(1); st.rerun()
            else: st.error("Save Failed.")

# --- TAB 3: ESTIMATOR ---
with tab3:
    st.subheader("Estimator Engine")
    ac = run_query(supabase.table("clients").select("id, name, internal_estimate").neq("status", "Closed"))
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
        inv = run_query(supabase.table("inventory").select("*"))
        if inv and inv.data:
            imap = {i['item_name']: i for i in inv.data}
            with st.form("add_est"):
                c1, c2, c3 = st.columns([3, 1, 1])
                inam = c1.selectbox("Item", list(imap.keys()))
                iqty = c2.number_input("Qty", 1.0, step=1.0)
                unit_options = ["pcs", "m", "ft", "cm", "in"]
                default_unit = imap.get(inam, {}).get('unit', 'pcs')
                unit_index = unit_options.index(default_unit) if default_unit in unit_options else 0
                iunit = c3.selectbox("Unit", unit_options, index=unit_index)
                if st.form_submit_button("⬇️ Add"):
                    selected_item = imap.get(inam, {})
                    st.session_state[ssk].append({"Item": inam, "Qty": iqty, "Base Rate": selected_item.get('base_rate', 0), "Unit": iunit})
                    st.rerun()

        if st.session_state[ssk]:
            df = pd.DataFrame(st.session_state[ssk])
            for col in ["Qty", "Base Rate", "Unit", "Item", "Total Price", "Unit Price"]:
                if col not in df.columns: df[col] = "" if col in ["Item", "Unit"] else 0.0
            
            column_order = ['Qty', 'Item', 'Unit', 'Base Rate', 'Unit Price', 'Total Price']
            df = df.reindex(columns=column_order, fill_value="")

            st.write("#### Items")
            edf = st.data_editor(df, num_rows="dynamic", use_container_width=True, key=f"t_{tc['id']}", 
                column_config={
                    "Qty": st.column_config.NumberColumn("Qty", width="small", step=1),
                    "Item": st.column_config.TextColumn("Item", width="large"),
                    "Unit": st.column_config.SelectboxColumn("Unit", options=["pcs", "m", "ft", "cm", "in"], width="small", required=True),
                    "Base Rate": st.column_config.NumberColumn("Base Rate", width="small"),
                    "Unit Price": st.column_config.NumberColumn("Unit Price", format="₹%.2f", width="small", disabled=True),
                    "Total Price": st.column_config.NumberColumn("Total Price", width="small", disabled=True)
                })
            
            # --- Universal Calculation Logic ---
            CONVERSIONS = {'pcs': 1.0, 'each': 1.0, 'm': 1.0, 'cm': 0.01, 'ft': 0.3048, 'in': 0.0254}
            mm = 1 + (am.get('part_margin', 0)/100) + (am.get('labor_margin', 0)/100) + (am.get('extra_margin', 0)/100)

            def calc_total(row):
                try:
                    qty = float(row.get('Qty', 0))
                    base = float(row.get('Base Rate', 0))
                    unit = row.get('Unit', 'pcs')
                    factor = CONVERSIONS.get(unit, 1.0)
                    
                    if unit in ['m', 'cm', 'ft', 'in']:
                        return base * (qty * factor) * mm
                    else:
                        return base * qty * mm
                except (ValueError, TypeError):
                    return 0.0

            edf['Total Price'] = edf.apply(calc_total, axis=1)
            edf['Unit Price'] = edf['Total Price'] / edf['Qty'].replace(0, 1)

            # Sync logic
            if edf.to_dict(orient="records") != st.session_state[ssk]:
                st.session_state[ssk] = edf.to_dict(orient="records")
                st.rerun()

            mt = pd.to_numeric(edf["Total Price"]).sum()
            daily_cost = float(gs.get('daily_labor_cost', 1000))
            raw_lt = dys * daily_cost
            
            total_base_cost = (pd.to_numeric(edf["Base Rate"]) * pd.to_numeric(edf["Qty"])).sum() + raw_lt
            raw_gt = mt + raw_lt
            rounded_gt = math.ceil(raw_gt / 100) * 100
            total_profit = rounded_gt - total_base_cost
            advance_amount = math.ceil((total_base_cost + (total_profit * 0.10)) / 100) * 100
            disp_lt = raw_lt + (rounded_gt - raw_gt)
            
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
                sobj = {"items": cit, "days": dys, "margins": {'p': am['part_margin'], 'l': am['labor_margin'], 'e': am['extra_margin']} if uc else None}
                res = run_query(supabase.table("clients").update({"internal_estimate": sobj}).eq("id", tc['id']))
                if res and res.data: st.toast("Saved!", icon="✅")
            
            pbytes = create_pdf(tc['name'], edf.to_dict(orient="records"), dys, disp_lt, rounded_gt, advance_amount)
            cp.download_button("📄 Download PDF", pbytes, f"Est_{tc['name']}.pdf", "application/pdf", key=f"pe_{tc['id']}")

# --- TAB 4: SETTINGS ---
with tab4:
    st.subheader("Global Defaults")
    s = get_settings()
    with st.form("glob_set"):
        c1, c2, c3 = st.columns(3)
        p = c1.slider("Part %", 0, 100, int(s.get('part_margin', 15.0)))
        l = c2.slider("Labor %", 0, 100, int(s.get('labor_margin', 20.0)))
        e = c3.slider("Extra %", 0, 100, int(s.get('extra_margin', 5.0)))
        
        lc = st.number_input("Daily Labor (₹)", value=float(s.get('daily_labor_cost', 1000.0)), step=100.0)

        total_markup = p + l + e
        gross_margin = (total_markup / (100 + total_markup)) * 100 if (100 + total_markup) != 0 else 0
        
        st.info(f"Total Markup Applied: {total_markup}%  |  Actual Gross Margin: {gross_margin:.1f}%")

        if st.form_submit_button("Update Settings"):
            run_query(supabase.table("settings").upsert({"id": 1, "part_margin": p, "labor_margin": l, "extra_margin": e, "daily_labor_cost": lc}))
            st.success("Saved!"); st.cache_resource.clear(); time.sleep(1); st.rerun()
            
    st.divider()
    st.subheader("Inventory (Editable)")
    with st.form("inv_add"):
        c1, c2, c3 = st.columns([2, 1, 1])
        new_item, rate = c1.text_input("Item Name"), c2.number_input("Rate", min_value=0.0)
        unit = c3.selectbox("Unit", ['pcs', 'm', 'ft', 'cm', 'in'])
        if st.form_submit_button("Add Item"):
            if run_query(supabase.table("inventory").insert({"item_name": new_item, "base_rate": rate, "unit": unit})):
                st.success("Added"); st.rerun()
    
    inv_resp = run_query(supabase.table("inventory").select("*").order("item_name"))
    if inv_resp and inv_resp.data:
        inv_df = pd.DataFrame(inv_resp.data)
        if 'unit' not in inv_df.columns: inv_df['unit'] = "pcs"
        edited_inv = st.data_editor(inv_df, num_rows="dynamic", key="inv_table_edit",
                                    column_config={
                                        "id": None, # Hide the 'id' column
                                        "item_name": st.column_config.Column("Item Name", width="medium"),
                                        "base_rate": st.column_config.NumberColumn("Rate", width="small"),
                                        "unit": st.column_config.SelectboxColumn("Unit", options=['pcs', 'm', 'ft', 'cm', 'in'], width="small", required=True)
                                    })
        
        if st.button("💾 Save Inventory Changes"):
            df_to_save = edited_inv.copy()
            df_to_save['base_rate'] = pd.to_numeric(df_to_save['base_rate'].fillna(0))
            df_to_save['item_name'] = df_to_save['item_name'].fillna("")
            df_to_save['unit'] = df_to_save['unit'].fillna("")
            recs = df_to_save.to_dict(orient="records")
            errors = 0
            for row in recs:
                if row.get('item_name'):
                   if not run_query(supabase.table("inventory").upsert(row)): errors += 1
            if errors == 0: st.success("Inventory Updated!"); time.sleep(0.5); st.rerun()
            else: st.warning("Some items failed to save.")
    
    st.divider()
    with st.form("pwd_chg"):
        st.subheader("User Profile")
        np = st.text_input("New Password", type="password")
        if st.form_submit_button("Update Password"):
            run_query(supabase.table("users").update({"password": np}).eq("username", st.session_state.username)); st.success("Updated!")

# --- TAB 5: SUPPLIERS ---
with tab5:
    st.header("🚚 Supplier & Purchase Management")

    col_purchase, col_manage = st.columns([2, 1])

    with col_manage:
        st.subheader("Directory")
        with st.form("add_supplier_form"):
            s_name = st.text_input("Supplier Name")
            s_contact = st.text_input("Contact Person")
            s_phone = st.text_input("Phone")
            if st.form_submit_button("Add New Supplier", type="primary"):
                if s_name:
                    res = run_query(supabase.table("suppliers").insert({"name": s_name, "contact_person": s_contact, "phone": s_phone}))
                    if res and res.data:
                        st.success(f"Supplier {s_name} added!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Failed to add supplier.")
                else:
                    st.warning("Supplier Name cannot be empty.")
        
        # Moved existing suppliers table outside columns
    
    # Existing Suppliers section (full width)
                    # Existing Suppliers table will be moved outside columns    with col_purchase:
        st.subheader("Record Purchase")
        # Fetch suppliers and inventory items
        supplier_resp_p = run_query(supabase.table("suppliers").select("id, name").order("name"))
        inventory_resp_p = run_query(supabase.table("inventory").select("item_name, base_rate").order("item_name"))

        supplier_options = {s['name']: s['id'] for s in supplier_resp_p.data} if supplier_resp_p and supplier_resp_p.data else {}
        inventory_options = {i['item_name']: i for i in inventory_resp_p.data} if inventory_resp_p and inventory_resp_p.data else {}

        if not supplier_options:
            st.warning("Please add suppliers first in the right column.")
        if not inventory_options:
            st.warning("Please add inventory items in the Settings tab.")

        if supplier_options and inventory_options:
            selected_supplier_name = st.selectbox("Select Supplier", list(supplier_options.keys()))
            selected_item_name = st.selectbox("Select Item", list(inventory_options.keys()))

            # Pre-fill rate with current base_rate from inventory if available
            default_rate = inventory_options.get(selected_item_name, {}).get('base_rate', 0.0)
            purchase_rate = st.number_input("Buying Rate", min_value=0.0, value=float(default_rate), step=0.01)
            purchase_qty = st.number_input("Quantity", min_value=0.0, value=1.0, step=1.0, format="%.2f")
            update_inventory_base_rate = st.checkbox("Update Inventory Base Rate?", value=True)

            if st.button("✅ Record Transaction", type="primary"):
                if selected_supplier_name and selected_item_name and purchase_qty > 0:
                    supplier_id = supplier_options[selected_supplier_name]
                    total_cost = purchase_rate * purchase_qty

                    # Insert into purchase_log
                    res_purchase = run_query(supabase.table("purchase_log").insert({
                        "supplier_id": supplier_id,
                        "item_name": selected_item_name,
                        "qty": purchase_qty,
                        "rate": purchase_rate,
                        "total_cost": total_cost
                    }))

                    if res_purchase and res_purchase.data:
                        if update_inventory_base_rate:
                            # Update inventory base_rate
                            res_inventory = run_query(supabase.table("inventory").update({"base_rate": purchase_rate}).eq("item_name", selected_item_name))
                            if res_inventory and res_inventory.data:
                                st.success("Purchase Recorded & Inventory Updated!")
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error("Purchase Recorded, but failed to update Inventory Base Rate.")
                        else:
                            st.success("Purchase Recorded!")
                            time.sleep(0.5)
                            st.rerun()
                    else:
                        st.error("Failed to record purchase.")
                else:
                    st.warning("Please fill all required fields and ensure quantity is greater than zero.")

    # Existing Suppliers section (full width)
    st.write("---")
    st.subheader("Existing Suppliers")
    supplier_resp = run_query(supabase.table("suppliers").select("*").order("name"))
    if supplier_resp and supplier_resp.data:
        df_suppliers = pd.DataFrame(supplier_resp.data)
        
        edited_suppliers = st.data_editor(df_suppliers, num_rows="dynamic", use_container_width=True, key="sup_editor",
                                            column_config={
                                                "id": None,  # Hides the ID column to save space
                                                "name": st.column_config.TextColumn("Supplier Name", width="large", required=True),
                                                "contact_person": st.column_config.TextColumn("Contact Person", width="medium"),
                                                "phone": st.column_config.TextColumn("Phone", width="medium")
                                            })
        
        if st.button("💾 Save Changes", key="save_sup_changes"):
            df_to_save = edited_suppliers.copy()
            # Ensure 'id' is preserved for upsert, handle newly added rows with no ID
            df_to_save['id'] = df_to_save['id'].replace({None: math.nan}).fillna(0).astype(int) # Set new rows ID to 0 for upsert
            df_to_save['name'] = df_to_save['name'].fillna("")
            
            recs_to_upsert = df_to_save.to_dict(orient="records")
            
            errors_occurred = False
            for record in recs_to_upsert:
                if record.get("name"): # Ensure name is not empty for upsert
                    if record.get("id") == 0: # New row
                        del record['id'] # Supabase handles id generation for new records
                        res = run_query(supabase.table("suppliers").insert(record))
                    else: # Existing row
                        res = run_query(supabase.table("suppliers").upsert(record))
                    
                    if not (res and res.data):
                        errors_occurred = True
                        st.error(f"Failed to save supplier: {record.get('name')}")
                else:
                    errors_occurred = True
                    st.warning(f"Skipped saving a row with empty supplier name.")

            if not errors_occurred:
                st.success("Suppliers Updated!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.warning("Some supplier changes could not be saved.")
    else:
        st.info("No suppliers found.")

    st.write("---") # Add a divider here after the existing suppliers table and before recent history.

    st.divider()
    st.subheader("Recent History")
    
    purchase_log_resp = None
    try:
        purchase_log_resp = run_query(supabase.table("purchase_log").select("*").order("created_at", desc=True).limit(50))
    except Exception as e:
        st.info("Purchase History not active yet.")
        # Optional: log the actual error for debugging
        # st.error(f"Error fetching purchase log: {e}")

    supplier_resp_history = run_query(supabase.table("suppliers").select("id, name"))

    if purchase_log_resp and purchase_log_resp.data and supplier_resp_history and supplier_resp_history.data:
        df_purchases = pd.DataFrame(purchase_log_resp.data)
        df_suppliers_history = pd.DataFrame(supplier_resp_history.data).rename(columns={'name': 'supplier_name'})
        
        # Merge to get supplier name
        df_merged = pd.merge(df_purchases, df_suppliers_history, left_on='supplier_id', right_on='id', how='left')
        
        # Select and reorder columns for display
        display_cols = ['created_at', 'supplier_name', 'item_name', 'qty', 'rate', 'total_cost']
        df_merged['created_at'] = pd.to_datetime(df_merged['created_at']).dt.strftime('%Y-%m-%d %H:%M')
        df_merged['rate'] = df_merged['rate'].round(2)
        df_merged['total_cost'] = df_merged['total_cost'].round(2)

        st.dataframe(df_merged[display_cols], use_container_width=True, hide_index=True)
    else:
        if purchase_log_resp is not None: # Only show this if the query didn't fail, but returned no data
            st.info("No purchases recorded yet.")
