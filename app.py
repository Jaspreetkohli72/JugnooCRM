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
st.set_page_config(page_title="Jugnoo CRM", page_icon="🏗️", layout="wide")

st.markdown("""
    <style>
    /* Force Dark Theme & Remove White Bars */
    .stApp { background-color: #0E1117 !important; }
    header[data-testid="stHeader"] { background-color: #0E1117 !important; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    
    /* Dark Metrics */
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
    st.title("🔒 Jugnoo CRM")
    time.sleep(0.1)
    cookie_user = cookie_manager.get(cookie="jugnoo_user")
    
    if cookie_user:
        st.session_state.logged_in = True
        st.session_state.username = cookie_user
        return 

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
                    st.success("Success!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Invalid Credentials")
    st.stop()

login_section()

# ---------------------------
# 3. HELPERS
# ---------------------------
def run_query(query_func):
    try:
        return query_func.execute()
    except Exception as e:
        st.error(f"Database Error: {e}")
        return None

def get_settings():
    """Fetches Global Settings (ID=1). Default are whole numbers now."""
    defaults = {"part_margin": 15.0, "labor_margin": 20.0, "extra_margin": 5.0, "daily_labor_cost": 1000.0}
    try:
        response = run_query(supabase.table("settings").select("*").eq("id", 1))
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
    # Labor Total here INCLUDES the hidden rounding profit
    pdf.cell(130, 10, f"Labor / Installation ({labor_days} Days)", 1)
    pdf.cell(60, 10, f"{labor_total:.2f}", 1)
    pdf.ln()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(130, 10, "Grand Total", 1)
    pdf.cell(60, 10, f"{grand_total:.2f}", 1)
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
        cols = [c for c in ['name', 'status', 'start_date', 'phone', 'address'] if c in df.columns]
        st.dataframe(df[cols], use_container_width=True, hide_index=True)
        st.divider()
        
        client_map = {c['name']: c for c in response.data}
        sel_name = st.selectbox("Select Client to Manage", list(client_map.keys()), index=None, key="dash_sel")
        
        if sel_name:
            client = client_map[sel_name]
            st.markdown("### 🛠️ Manage Client")
            c1, c2 = st.columns([1.5, 1])
            
            with c1:
                st.write("**Edit Details**")
                # GPS BUTTON (No Toggle)
                gps_dash = get_geolocation(component_key=f"gps_dash_{client['id']}")
                if gps_dash:
                    lat = gps_dash['coords']['latitude']
                    lng = gps_dash['coords']['longitude']
                    st.session_state[f"loc_{client['id']}"] = f"http://googleusercontent.com/maps.google.com/?q={lat},{lng}"
                    st.toast("📍 Location Updated!")

                with st.form("edit_details"):
                    nn = st.text_input("Name", value=client['name'])
                    np = st.text_input("Phone", value=client.get('phone', ''))
                    na = st.text_area("Address", value=client.get('address', ''))
                    curr_loc = st.session_state.get(f"loc_{client['id']}", client.get('location', ''))
                    nl = st.text_input("Maps Link", value=curr_loc)
                    if st.form_submit_button("💾 Save Changes"):
                        res = run_query(supabase.table("clients").update({
                            "name": nn, "phone": np, "address": na, "location": nl
                        }).eq("id", client['id']))
                        if res and res.data:
                            st.success("Updated!")
                            time.sleep(0.5)
                            st.rerun()
                if client.get('location'):
                    st.link_button("🚀 Navigate to Site", client['location'])

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
                    if res and res.data:
                        st.success("Status Saved!")
                        time.sleep(0.5)
                        st.rerun()

            if client.get('internal_estimate'):
                st.divider()
                st.subheader("📄 Estimate Overview")
                est_data = client['internal_estimate']
                s_items = est_data.get('items', []) if isinstance(est_data, dict) else (est_data if isinstance(est_data, list) else [])
                s_days = est_data.get('days', 1.0) if isinstance(est_data, dict) else 1.0
                
                if s_items:
                    idf = pd.DataFrame(s_items)
                    if "Total Price" not in idf.columns and "Total (Internal)" in idf.columns: idf["Total Price"] = idf["Total (Internal)"]
                    
                    if "Total Price" in idf.columns:
                        st.dataframe(idf, use_container_width=True)
                        gs = get_settings()
                        
                        # ROUNDING LOGIC
                        mat = idf['Total Price'].sum()
                        raw_lab = float(s_days) * float(gs.get('daily_labor_cost', 1000))
                        raw_grand = mat + raw_lab
                        
                        # Round UP to nearest 100
                        rounded_grand = math.ceil(raw_grand / 100) * 100
                        rounding_delta = rounded_grand - raw_grand
                        
                        # Hide delta in Labor
                        displayed_labor = raw_lab + rounding_delta
                        
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Material", f"₹{mat:,.0f}")
                        m2.metric("Labor (Adjusted)", f"₹{displayed_labor:,.0f}", help=f"Includes Rounding (+₹{rounding_delta:.0f})")
                        m3.metric("Grand Total", f"₹{rounded_grand:,.0f}")
                        
                        pdf_bytes = create_pdf(client['name'], s_items, s_days, displayed_labor, rounded_grand)
                        st.download_button("📄 Download PDF", pdf_bytes, f"Est_{client['name']}.pdf", "application/pdf", key=f"pdf_dash_{client['id']}")
                else:
                    st.warning("Empty estimate.")

# --- TAB 2: NEW CLIENT ---
with tab2:
    st.subheader("Add New Client")
    # GPS BUTTON (No Toggle)
    gps_new = get_geolocation(component_key="gps_new")
    if gps_new:
        lat = gps_new['coords']['latitude']
        lng = gps_new['coords']['longitude']
        st.session_state['new_loc_val'] = f"http://googleusercontent.com/maps.google.com/?q={lat},{lng}"
        st.toast("📍 Captured!")

    with st.form("new_client"):
        c1, c2 = st.columns(2)
        nm = c1.text_input("Client Name")
        ph = c2.text_input("Phone")
        ad = st.text_area("Address")
        lo = st.text_input("Google Maps Link", value=st.session_state.get('new_loc_val', ""))
        
        if st.form_submit_button("Create Client", type="primary"):
            res = run_query(supabase.table("clients").insert({
                "name": nm, "phone": ph, "address": ad, "location": lo,
                "status": "Estimate Given", "created_at": datetime.now().isoformat()
            }))
            if res and res.data:
                st.success(f"Client {nm} Added!")
                if 'new_loc_val' in st.session_state: del st.session_state['new_loc_val']
                time.sleep(1)
                st.rerun()
            else:
                st.error("Save Failed.")

# --- TAB 3: ESTIMATOR ---
with tab3:
    st.subheader("Estimator Engine")
    ac = run_query(supabase.table("clients").select("id, name, internal_estimate").neq("status", "Closed"))
    cd = {c['name']: c for c in ac.data} if ac and ac.data else {}
    tn = st.selectbox("Select Client", list(cd.keys()), key="est_sel")
    
    if tn:
        tc = cd[tn]
        se = tc.get('internal_estimate')
        li = se.get('items', []) if isinstance(se, dict) else (se if isinstance(se, list) else [])
        sm = se.get('margins') if isinstance(se, dict) else None
        sd = se.get('days', 1.0) if isinstance(se, dict) else 1.0
        ssk = f"est_{tc['id']}"
        if ssk not in st.session_state: st.session_state[ssk] = li

        st.divider()
        gs = get_settings()
        uc = st.checkbox("🛠️ Use Custom Margins", value=(sm is not None), key="cm")
        
        if uc:
            dp = int(sm['p']) if sm else int(gs['part_margin'])
            dl = int(sm['l']) if sm else int(gs['labor_margin'])
            de = int(sm['e']) if sm else int(gs['extra_margin'])
            mc1, mc2, mc3 = st.columns(3)
            cp = mc1.slider("Part %", 0, 100, dp, key="cp")
            cl = mc2.slider("Labor %", 0, 100, dl, key="cl")
            ce = mc3.slider("Extra %", 0, 100, de, key="ce")
            am = {'part_margin': cp, 'labor_margin': cl, 'extra_margin': ce}
        else:
            am = gs
            
        dys = st.slider("⏳ Days", 0.5, 30.0, float(sd), 0.5)

        st.divider()
        inv = run_query(supabase.table("inventory").select("*"))
        if inv and inv.data:
            imap = {i['item_name']: i['base_rate'] for i in inv.data}
            with st.form("add_est"):
                c1, c2, c3 = st.columns([3, 2, 1])
                inam = c1.selectbox("Item", list(imap.keys()))
                iqty = c2.number_input("Qty", 1.0, step=0.5)
                if st.form_submit_button("⬇️ Add"):
                    st.session_state[ssk].append({"Item": inam, "Qty": iqty, "Base Rate": imap[inam]})
                    st.rerun()

        if st.session_state[ssk]:
            mm = 1 + (am['part_margin']/100) + (am['labor_margin']/100) + (am['extra_margin']/100)
            df = pd.DataFrame(st.session_state[ssk])
            if "Qty" not in df.columns: df["Qty"] = 1.0
            if "Base Rate" not in df.columns: df["Base Rate"] = 0.0
            
            df["Unit Price (Calc)"] = df["Base Rate"] * mm
            df["Total Price"] = df["Unit Price (Calc)"] * df["Qty"]
            
            st.write("#### Items")
            edf = st.data_editor(df, num_rows="dynamic", use_container_width=True, key=f"t_{tc['id']}",
                column_config={"Item": st.column_config.TextColumn(disabled=True), "Base Rate": st.column_config.NumberColumn(disabled=True, format="₹%.2f"), "Total Price": st.column_config.NumberColumn(disabled=True, format="₹%.2f")})
            
            cit = edf.to_dict(orient="records")
            mt = edf["Total Price"].sum()
            
            # ROUNDING LOGIC (Estimator View)
            raw_lt = dys * float(gs.get('daily_labor_cost', 1000))
            raw_gt = mt + raw_lt
            rounded_gt = math.ceil(raw_gt / 100) * 100
            r_delta = rounded_gt - raw_gt
            disp_lt = raw_lt + r_delta
            
            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("Material", f"₹{mt:,.0f}")
            c2.metric("Labor", f"₹{disp_lt:,.0f}", help=f"Raw: ₹{raw_lt:.0f} + Rounding: ₹{r_delta:.0f}")
            c3.metric("Grand Total", f"₹{rounded_gt:,.0f}")
            
            cs, cp = st.columns(2)
            if cs.button("💾 Save", type="primary"):
                sobj = {"items": cit, "days": dys, "margins": {'p': am['part_margin'], 'l': am['labor_margin'], 'e': am['extra_margin']} if uc else None}
                res = run_query(supabase.table("clients").update({"internal_estimate": sobj}).eq("id", tc['id']))
                if res and res.data: st.toast("Saved!", icon="✅")
            
            pbytes = create_pdf(tc['name'], cit, dys, disp_lt, rounded_gt)
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
        
        if st.form_submit_button("Update Settings"):
            res = run_query(supabase.table("settings").upsert({
                "id": 1, "part_margin": p, "labor_margin": l, "extra_margin": e, "daily_labor_cost": lc
            }))
            if res and res.data:
                st.success("Saved!")
                st.cache_resource.clear()
                time.sleep(1)
                st.rerun()
            
    st.divider()
    st.subheader("Inventory")
    with st.form("inv_new"):
        c1, c2 = st.columns([2, 1])
        ni = c1.text_input("Item Name")
        nr = c2.number_input("Rate", min_value=0.0)
        if st.form_submit_button("Add Item"):
            res = run_query(supabase.table("inventory").insert({"item_name": ni, "base_rate": nr}))
            if res and res.data:
                st.success("Added")
                st.rerun()
            else:
                st.error("Failed to add item.")
    
    inv = run_query(supabase.table("inventory").select("*").order("item_name"))
    if inv and inv.data: st.dataframe(pd.DataFrame(inv.data), use_container_width=True)
    
    st.divider()
    with st.form("pwd_chg"):
        st.subheader("User Profile")
        np = st.text_input("New Password", type="password")
        if st.form_submit_button("Update Password"):
            res = run_query(supabase.table("users").update({"password": np}).eq("username", st.session_state.username))
            if res and res.data:
                st.success("Updated!")