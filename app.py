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
st.sidebar.write(f"👤 **{st.session_state.username}**")
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    cookie_manager.delete("jugnoo_user")
    st.rerun()

if not supabase: st.stop()

tab1, tab2, tab3, tab4 = st.tabs(["📋 Dashboard", "➕ New Client", "🧮 Estimator", "⚙️ Settings"])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.subheader("Active Projects")
    response = run_query(supabase.table("clients").select("*").order("created_at", desc=True))
    
    if response and response.data:
        df = pd.DataFrame(response.data)
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
                with st.form("edit_details"):
                    nn, np, na = st.text_input("Name", value=client['name']), st.text_input("Phone", value=client.get('phone', '')), st.text_area("Address", value=client.get('address', ''))
                    if st.form_submit_button("💾 Save Changes"):
                        res = run_query(supabase.table("clients").update({"name": nn, "phone": np, "address": na}).eq("id", client['id']))
                        if res and res.data: st.success("Updated!"); time.sleep(0.5); st.rerun()
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
                    total_base_cost = (pd.to_numeric(edited_est['Base Rate'].fillna(0)) * pd.to_numeric(edited_est['Qty'].fillna(0))).sum() + labor_actual_cost
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
                    if client.get('status') == "Work Done":
                        pdf_internal = create_internal_pdf(client['name'], edited_est.to_dict(orient="records"), s_days, labor_actual_cost, labor_charged_display, rounded_grand_total, total_profit)
                        c_pdf2.download_button("💼 Internal Report", pdf_internal, f"Internal_{client['name']}.pdf", "application/pdf", key=f"pdf_i_{client['id']}")
                    else: c_pdf2.info("Mark status as 'Work Done' for Internal Report.")
                else: st.warning("Estimate Empty")

# --- TAB 2: NEW CLIENT ---
with tab2:
    st.subheader("Add New Client")
    with st.form("new_client"):
        c1, c2 = st.columns(2)
        nm, ph = c1.text_input("Client Name"), c2.text_input("Phone")
        ad = st.text_area("Address")
        if st.form_submit_button("Create Client", type="primary"):
            res = run_query(supabase.table("clients").insert({"name": nm, "phone": ph, "address": ad, "status": "Estimate Given", "created_at": datetime.now().isoformat()}))
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