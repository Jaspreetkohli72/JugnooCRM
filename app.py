import streamlit as st
from supabase import create_client
from utils import helpers, auth

from datetime import datetime, timedelta
import time
import pandas as pd
import math
from supabase.client import F


from streamlit_js_eval import get_geolocation
import altair as alt
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
        res = supabase.table("users").select("password").eq("username", username).execute()
        if res and res.data:
            hashed_password = res.data[0]['password']
            return auth.verify_password(password, hashed_password)
        return False
    except Exception as e:
        st.error(f"Database Error: {e}")
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


def get_settings():
    defaults = {"part_margin": 15.0, "labor_margin": 20.0, "extra_margin": 5.0, "daily_labor_cost": 1000.0}
    try:
        response = supabase.table("settings").select("*").eq("id", 1).execute()
        if response and response.data:
            db_data = response.data[0]
            return {k: db_data.get(k, v) for k, v in defaults.items()}
    except Exception as e:
        st.error(f"Database Error: {e}")
        pass
    return defaults

# --- PROFESSIONAL PDF GENERATOR ---
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

tab1, tab2, tab3, tab5, tab6, tab4 = st.tabs(["📋 Dashboard", "➕ New Client", "🧮 Estimator", "🚚 Suppliers", "📈 P&L", "⚙️ Settings"])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.subheader("Client Projects")
    
    status_filter = st.radio(
        "Filter by Status",
        ('All', 'Active', 'Inactive'),
        horizontal=True,
        key="status_filter_radio"
    )

    with st.spinner("Loading Dashboard..."):
        try:
            response = supabase.table("clients").select("*").order("created_at", desc=True).execute()
        except Exception as e:
            st.error(f"Database Error: {e}")
            response = None
    
        if response and response.data:
            df = pd.DataFrame(response.data)
    
            active_clients_df = df[df['status'].isin(helpers.ACTIVE_STATUSES)]
            inactive_clients_df = df[df['status'].isin(helpers.INACTIVE_STATUSES)]
    
            col1, col2 = st.columns(2)
            col1.metric("Active Clients", len(active_clients_df))
            col2.metric("Inactive Clients", len(inactive_clients_df))
    
            # Apply filter based on radio button selection
            if status_filter == 'Active':
                df_display = active_clients_df
            elif status_filter == 'Inactive':
                df_display = inactive_clients_df
            else:
                df_display = df
    
            st.dataframe(df_display[[c for c in ['name', 'status', 'start_date', 'phone', 'address'] if c in df.columns]], use_container_width=True, hide_index=True)
            st.divider()
    
            with st.expander("🛠️ Manage Client"):
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
                                try:
                                    res = supabase.table("clients").update({"name": nn, "phone": np, "address": na, "location": ml}).eq("id", client['id']).execute()
                                except Exception as e:
                                    st.error(f"Database Error: {e}")
                                    res = None
                    with c2:
                        st.write("**Project Status**")
                        opts = helpers.ACTIVE_STATUSES + helpers.INACTIVE_STATUSES
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
                            try:
                                res = supabase.table("clients").update(upd).eq("id", client['id']).execute()
                                if res and res.data: st.success("Status Saved!"); time.sleep(0.5); st.rerun()
                            except Exception as e:
                                st.error(f"Database Error: {e}")
    
                    st.expander("Danger Zone").button("Delete Client", type="secondary", use_container_width=True, on_click=lambda: (
                        supabase.table("clients").delete().eq("id", client['id']).execute()
                    ), key=f"del_{client['id']}")
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
                            idf = helpers.create_item_dataframe(st.session_state[ssk_dash])
    
                            edited_est = st.data_editor(idf, num_rows="dynamic", use_container_width=True, key=f"de_{client['id']}",
                                                        column_config={
                                                            "Qty": st.column_config.NumberColumn("Qty", width="small", step=1),
                                                            "Item": st.column_config.TextColumn("Item", width="large"),
                                                            "Unit": st.column_config.SelectboxColumn("Unit", options=["pcs", "m", "cm", "in", "ft"], width="small", required=True),
                                                            "Base Rate": st.column_config.NumberColumn("Base Rate", width="small"),
                                                            "Unit Price": st.column_config.NumberColumn("Unit Price", format="₹%.2f", width="small", disabled=True),
                                                            "Total Price": st.column_config.NumberColumn("Total Price", width="small", disabled=True)
                                                        })
    
                            # --- Refactored Calculation Logic ---
                            gs = get_settings()
                            # Ensure am is correctly set from stored margins or global settings
                            am = est_data.get('margins') if est_data.get('margins') else gs
                            # If custom margins are stored as {'p': val, 'l': val, 'e': val}, convert to full names
                            if am and 'p' in am:
                                am_for_calc = {
                                    'part_margin': am.get('p', 0),
                                    'labor_margin': am.get('l', 0),
                                    'extra_margin': am.get('e', 0)
                                }
                            else:
                                am_for_calc = am # Use directly if already in full form or global settings
                            
                            # Call the centralized function
                            calculated_results = calculate_estimate_details(
                                edf_items_list=edited_est.to_dict(orient="records"),
                                days=s_days,
                                margins=am_for_calc,
                                global_settings=gs
                            )
    
                            mat_sell = calculated_results["mat_sell"]
                            labor_actual_cost = calculated_results["labor_actual_cost"]
                            rounded_grand_total = calculated_results["rounded_grand_total"]
                            total_profit = calculated_results["total_profit"]
                            advance_amount = calculated_results["advance_amount"]
                            labor_charged_display = calculated_results["disp_lt"]
                            edited_est_with_prices = calculated_results["edf_details_df"]
                            
                            m1, m2, m3, m4, m5 = st.columns(5)
                            m1.metric("Material Total", f"₹{mat_sell:,.0f}"); m2.metric("Labor", f"₹{labor_charged_display:,.0f}"); m3.metric("Grand Total", f"₹{rounded_grand_total:,.0f}"); m4.metric("Total Profit", f"₹{total_profit:,.0f}"); m5.metric("Advance Required", f"₹{advance_amount:,.0f}")
                            
                            if st.button("💾 Save Changes", key=f"sv_{client['id']}"):
                                df_to_save = edited_est_with_prices.copy() # Use the DataFrame with updated prices
                                for col in ['Qty', 'Base Rate', 'Total Price', "Unit Price"]:
                                    df_to_save[col] = pd.to_numeric(df_to_save[col].fillna(0))
                                for col in ['Item', 'Unit']: df_to_save[col] = df_to_save[col].fillna("")
                                new_json = {"items": df_to_save.to_dict(orient="records"), "days": s_days, "margins": est_data.get('margins')} # Save original margins structure
                                try:
                                    supabase.table("clients").update({"internal_estimate": new_json}).eq("id", client['id']).execute()
                                    st.toast("Saved!", icon="✅")
                                except Exception as e:
                                    st.error(f"Database Error: {e}")
                            
                            st.write("#### 📥 Download Bills")
                            c_pdf1, c_pdf2 = st.columns(2)
                            pdf_client = create_pdf(client['name'], edited_est_with_prices.to_dict(orient="records"), s_days, labor_charged_display, rounded_grand_total, advance_amount)
                            c_pdf1.download_button("📄 Client Invoice", pdf_client, f"Invoice_{client['name']}.pdf", "application/pdf", key=f"pdf_c_{client['id']}")
                            st.write("#### Internal Profit Analysis")
                            if client.get('status') == "Work Done":
                                df_profit = edited_est_with_prices.copy()
                                df_profit['Qty'] = pd.to_numeric(df_profit['Qty'].fillna(0))
                                df_profit['Base Rate'] = pd.to_numeric(df_profit['Base Rate'].fillna(0))
                                df_profit['Total Price'] = pd.to_numeric(df_profit['Total Price'].fillna(0))
                                
                                df_profit['Total Sell Price'] = df_profit['Total Price'] # Use existing Total Price as Total Sell Price
                                
                                # Use calculate_estimate_details result for profit details if possible, or recalculate
                                # For now, keeping the original detailed profit calculation here, ensuring it uses edited_est_with_prices
                                df_profit['Row Profit'] = df_profit.apply(helpers.calculate_profit_row, axis=1)
                                
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
            try:
                res = supabase.table("clients").insert({"name": nm, "phone": ph, "address": ad, "location": ml_new_client, "status": "Estimate Given", "created_at": datetime.now().isoformat()}).execute()
                if res and res.data: st.success(f"Client {nm} Added!"); time.sleep(1); st.rerun()
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
            inv_all_items_response = supabase.table("inventory").select("item_name, stock_quantity").execute()
        except Exception as e:
            st.error(f"Database Error: {e}")
            inv_all_items_response = None
        stock_map = {}
        if inv_all_items_response and inv_all_items_response.data:
            stock_map = {item['item_name']: item.get('stock_quantity', 0.0) for item in inv_all_items_response.data}
            
        try:
            inv = supabase.table("inventory").select("*").execute()
        except Exception as e:
            st.error(f"Database Error: {e}")
            inv = None
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
            df = helpers.create_item_dataframe(st.session_state[ssk])

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

            mm = 1 + (am.get('part_margin', 0)/100) + (am.get('labor_margin', 0)/100) + (am.get('extra_margin', 0)/100)

            def calc_total(row):
                try:
                    qty = float(row.get('Qty', 0))
                    base = float(row.get('Base Rate', 0))
                    unit = row.get('Unit', 'pcs')
                    factor = helpers.CONVERSIONS.get(unit, 1.0)
                    
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
                try:
                    res = supabase.table("clients").update({"internal_estimate": sobj}).eq("id", tc['id']).execute()
                    if res and res.data: st.toast("Saved!", icon="✅")
                except Exception as e:
                    st.error(f"Database Error: {e}")
            
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
            try:
                supabase.table("settings").upsert({"id": 1, "part_margin": p, "labor_margin": l, "extra_margin": e, "daily_labor_cost": lc}).execute()
                st.success("Saved!"); st.cache_resource.clear(); time.sleep(1); st.rerun()
            except Exception as e:
                st.error(f"Database Error: {e}")
            
    st.divider()
    st.subheader("Inventory (Editable)")
    with st.form("inv_add"):
        c1, c2, c3 = st.columns([2, 1, 1])
        new_item, rate = c1.text_input("Item Name"), c2.number_input("Rate", min_value=0.0)
        unit = c3.selectbox("Unit", ['pcs', 'm', 'ft', 'cm', 'in'])
        if st.form_submit_button("Add Item"):
            try:
                supabase.table("inventory").insert({"item_name": new_item, "base_rate": rate, "unit": unit}).execute()
                st.success("Added"); st.rerun()
            except Exception as e:
                st.error(f"Database Error: {e}")
    
    try:
        inv_resp = supabase.table("inventory").select("*").order("item_name").execute()
    except Exception as e:
        st.error(f"Database Error: {e}")
        inv_resp = None
    if inv_resp and inv_resp.data:
        inv_df = pd.DataFrame(inv_resp.data)
        if 'unit' not in inv_df.columns: inv_df['unit'] = "pcs"
        # Ensure 'stock_quantity' column exists and fill NaN with 0 for display and editing
        if 'stock_quantity' not in inv_df.columns:
            inv_df['stock_quantity'] = 0.0
        else:
            inv_df['stock_quantity'] = pd.to_numeric(inv_df['stock_quantity'], errors='coerce').fillna(0.0)

        edited_inv = st.data_editor(inv_df, num_rows="dynamic", key="inv_table_edit",
                                    column_config={
                                        "id": None, # Hide the 'id' column
                                        "item_name": st.column_config.Column("Item Name", width="medium"),
                                        "base_rate": st.column_config.NumberColumn("Rate", width="small"),
                                        "unit": st.column_config.SelectboxColumn("Unit", options=['pcs', 'm', 'ft', 'cm', 'in'], width="small", required=True),
                                        "stock_quantity": st.column_config.NumberColumn("Stock Quantity", width="small", help="Current physical stock of the item.")
                                    })
        
        if st.button("💾 Save Inventory Changes"):
            df_to_save = edited_inv.copy()
            df_to_save['base_rate'] = pd.to_numeric(df_to_save['base_rate'].fillna(0))
            df_to_save['stock_quantity'] = pd.to_numeric(df_to_save['stock_quantity'].fillna(0)) # Add this line
            df_to_save['item_name'] = df_to_save['item_name'].fillna("")
            df_to_save['unit'] = df_to_save['unit'].fillna("")
            recs = df_to_save.to_dict(orient="records")
            errors = 0
            for row in recs:
                if row.get('item_name'):
                    try:
                        supabase.table("inventory").upsert(row).execute()
                    except Exception as e:
                        errors += 1
                        st.error(f"Error saving {row.get('item_name')}: {e}")
            if errors == 0: 
                st.success("Inventory Updated!")
                time.sleep(0.5)
                st.rerun()
            else: 
                st.warning(f"{errors} items failed to save.")
    
    st.divider()
    with st.form("pwd_chg"):
        st.subheader("User Profile")
        op = st.text_input("Old Password", type="password")
        np = st.text_input("New Password", type="password")
        if st.form_submit_button("Update Password"):
            # First, check if the old password is correct
            try:
                res = supabase.table("users").select("password").eq("username", st.session_state.username).execute()
                if res and res.data:
                    current_password = res.data[0]['password']
                    if auth.verify_password(op, current_password):
                        # If old password is correct, update to new password
                        new_hashed_password = auth.hash_password(np)
                        supabase.table("users").update({"password": new_hashed_password}).eq("username", st.session_state.username).execute()
                        st.success("Password updated successfully!")
                    else:
                        st.error("Incorrect old password.")
                else:
                    st.error("Could not verify user.")
            except Exception as e:
                st.error(f"Database Error: {e}")

# --- TAB 5: SUPPLIERS ---
with tab5:
    st.header("🚚 Supplier & Purchase Management")

    # --- Middle Section (Full Width): Existing Suppliers ---
    st.subheader("Existing Suppliers")
    with st.spinner("Loading Suppliers..."):
        try:
            supplier_resp = supabase.table("suppliers").select("*").order("name").execute()
        except Exception as e:
            st.error(f"Database Error: {e}")
            supplier_resp = None
    if supplier_resp and supplier_resp.data:
        df_suppliers = pd.DataFrame(supplier_resp.data)
        edited_suppliers = st.data_editor(df_suppliers, num_rows="dynamic", use_container_width=True, key="sup_editor",
                                            column_config={
                                                "id": None,
                                                "name": st.column_config.TextColumn("Supplier Name", width="large", required=True),
                                                "contact_person": st.column_config.TextColumn("Contact Person", width="medium"),
                                                "phone": st.column_config.TextColumn("Phone", width="medium"),
                                                "gstin": st.column_config.TextColumn("GSTIN", width="medium")
                                            })
        
        if st.button("💾 Save Supplier Changes", key="save_sup_changes"):
            df_to_save = edited_suppliers.copy()
            recs_to_upsert = df_to_save.to_dict(orient="records")
            errors_occurred = False
            for record in recs_to_upsert:
                if record.get("name"):
                    try:
                        res = supabase.table("suppliers").upsert(record).execute()
                        if not (res and res.data):
                            errors_occurred = True
                            st.error(f"Failed to save supplier: {record.get('name')}")
                    except Exception as e:
                        errors_occurred = True
                        st.error(f"Failed to save supplier: {record.get('name')}: {e}")
                else:
                    st.warning("Skipped saving a row with an empty supplier name.")

            if not errors_occurred:
                st.success("Suppliers Updated!")
                time.sleep(0.5); st.rerun()
    else:
        st.info("No suppliers found. Add one using the form above.")

    with st.expander("Record Purchase & Add New Supplier"):
        col_purchase, col_manage = st.columns([2, 1])

        # --- Top Section: Left Column (Record Purchase) ---
        with col_purchase:
            st.subheader("Record Purchase")
            try:
                suppliers_response = supabase.table("suppliers").select("id, name").order("name").execute()
            except Exception as e:
                st.error(f"Database Error: {e}")
                suppliers_response = None
            try:
                inventory_response = supabase.table("inventory").select("item_name, base_rate").order("item_name").execute()
            except Exception as e:
                st.error(f"Database Error: {e}")
                inventory_response = None
    
            supplier_options = {s['name']: s['id'] for s in suppliers_response.data} if suppliers_response and suppliers_response.data else {}
            inventory_options = {i['item_name']: i for i in inventory_response.data} if inventory_response and inventory_response.data else {}
            if not supplier_options:
                st.warning("Please add a supplier in the 'Directory' section first.")
            if not inventory_options:
                st.warning("Please add inventory items in the 'Settings' tab first.")

            if supplier_options and inventory_options:
                selected_supplier_name = st.selectbox("Select Supplier", list(supplier_options.keys()), key="pur_sup_sel")
                selected_item_name = st.selectbox("Select Item", list(inventory_options.keys()), key="pur_item_sel")

                default_rate = inventory_options.get(selected_item_name, {}).get('base_rate', 0.0)
                purchase_rate = st.number_input("Buying Rate", min_value=0.0, value=float(default_rate), step=0.01, key=f"rate_{selected_item_name}")
                purchase_qty = st.number_input("Quantity", min_value=0.0, value=1.0, step=1.0, format="%.2f", key="pur_qty")
                update_inventory_base_rate = st.checkbox("Update Inventory Base Rate?", value=True, key="pur_update_inv")

                if st.button("✅ Record Transaction", type="primary", key="pur_record_btn"):
                    if selected_supplier_name and selected_item_name and purchase_qty > 0:
                        supplier_id = supplier_options[selected_supplier_name]
                        total_cost = purchase_rate * purchase_qty

                        try:
                            res_purchase = supabase.table("purchase_log").insert({
                                "supplier_id": supplier_id,
                                "item_name": selected_item_name,
                                "qty": purchase_qty,
                                "rate": purchase_rate,
                                "total_cost": total_cost
                            }).execute()
                        except Exception as e:
                            st.error(f"Database Error: {e}")
                            res_purchase = None

                        if res_purchase and res_purchase.data:
                            # Perform atomic stock increment
                            try:
                                res_stock_update = supabase.table("inventory").update({"stock_quantity": F("stock_quantity") + purchase_qty}).eq("item_name", selected_item_name).execute()
                            except Exception as e:
                                st.error(f"Database Error: {e}")
                                res_stock_update = None

                            if res_stock_update and res_stock_update.data:
                                if update_inventory_base_rate:
                                    try:
                                        res_inventory = supabase.table("inventory").update({"base_rate": purchase_rate}).eq("item_name", selected_item_name).execute()
                                        if res_inventory and res_inventory.data:
                                            st.success("Purchase Recorded, Stock & Inventory Updated!")
                                            time.sleep(0.5); st.rerun()
                                        else:
                                            st.error("Purchase Recorded, Stock Updated, but failed to update Inventory Base Rate.")
                                    except Exception as e:
                                        st.error(f"Database Error: {e}")
                                else:
                                    st.success("Purchase Recorded & Stock Updated!")
                                    time.sleep(0.5); st.rerun()
                            else:
                                st.error("Purchase Recorded, but failed to update Stock Quantity.")
                        else:
                            st.error("Failed to record purchase.")
                    else:
                        st.warning("Please fill all required fields and ensure quantity is > 0.")
        
        # --- Top Section: Right Column (Add New Supplier) ---
        with col_manage:
            st.subheader("Directory")
            with st.form("add_supplier_form"):
                s_name = st.text_input("Supplier Name")
                s_contact = st.text_input("Contact Person")
                s_phone = st.text_input("Phone")
                s_gstin = st.text_input("GSTIN")
                if st.form_submit_button("Add New Supplier", type="primary"):
                    if s_name:
                        try:
                            res = supabase.table("suppliers").insert({"name": s_name, "contact_person": s_contact, "phone": s_phone, "gstin": s_gstin}).execute()
                            if res and res.data:
                                st.success(f"Supplier {s_name} added!")
                                time.sleep(0.5); st.rerun()
                            else:
                                st.error("Failed to add supplier.")
                        except Exception as e:
                            st.error(f"Database Error: {e}")
                    else:
                        st.warning("Supplier Name cannot be empty.")

    # --- Bottom Section (Full Width): Recent History ---
    st.divider()
    st.subheader("Recent Purchase History")
    try:
        purchase_log_resp = supabase.table("purchase_log").select("*, suppliers(name)").order("created_at", desc=True).limit(50).execute()
    except Exception as e:
        st.error(f"Database Error: {e}")
        purchase_log_resp = None

    if purchase_log_resp and purchase_log_resp.data:
        df_purchases = pd.DataFrame(purchase_log_resp.data)
        
        # The join is now done in the query. We just need to flatten the structure.
        df_purchases['supplier_name'] = df_purchases['suppliers'].apply(lambda x: x['name'] if isinstance(x, dict) else 'N/A')
        
        display_cols = ['created_at', 'supplier_name', 'item_name', 'qty', 'rate', 'total_cost']
        for col in display_cols:
            if col not in df_purchases.columns:
                df_purchases[col] = 'N/A'

        df_purchases['created_at'] = pd.to_datetime(df_purchases['created_at']).dt.strftime('%Y-%m-%d %H:%M')
        df_purchases['rate'] = pd.to_numeric(df_purchases['rate'], errors='coerce').round(2)
        df_purchases['total_cost'] = pd.to_numeric(df_purchases['total_cost'], errors='coerce').round(2)
        
        st.dataframe(df_purchases[display_cols], use_container_width=True, hide_index=True)
    else:
        st.info("No purchases recorded yet.")

# --- TAB 6: PROFIT & LOSS ---
with tab6:
    st.subheader("📈 Profit & Loss Analysis")

    with st.spinner("Loading P&L Data..."):
        try:
            # Fetch Data
            try:
                clients_response = supabase.table("clients").select("status, internal_estimate").execute()
            except Exception as e:
                st.error(f"Database Error: {e}")
                clients_response = None
            try:
                purchase_log_response = supabase.table("purchase_log").select("total_cost").execute()
            except Exception as e:
                st.error(f"Database Error: {e}")
                purchase_log_response = None
            settings = get_settings() # Re-use existing helper function

        if clients_response and clients_response.data and purchase_log_response and purchase_log_response.data and settings:
            all_clients = clients_response.data
            purchase_log_data = purchase_log_response.data
            daily_labor_cost = float(settings.get('daily_labor_cost', 1000.0))

            total_revenue = 0.0
            total_labor_expense = 0.0
            
            # --- Calculate Revenue and Total Labor Expense ---
            for client in all_clients:
                estimate = client.get('internal_estimate')
                if estimate:
                    labor_days = float(estimate.get('days', 0.0))
                    client_labor_cost = labor_days * daily_labor_cost
                    if client.get('status') in ["Work Done", "Closed"]:
                        total_labor_expense += client_labor_cost

                    if client.get('status') in ["Work Done", "Closed"]:
                        items = estimate.get('items', [])
                        
                        material_sell_price_for_client = 0.0
                        for item in items:
                            try:
                                qty = float(item.get('Qty', 0))
                                base_rate = float(item.get('Base Rate', 0))
                                unit = item.get('Unit', 'pcs')
                                client_margins = estimate.get('margins')
                                am_for_client = client_margins if client_margins else settings
                                
                                if client_margins and 'p' in client_margins:
                                    am_for_client = {
                                        'part_margin': client_margins.get('p', 0),
                                        'labor_margin': client_margins.get('l', 0),
                                        'extra_margin': client_margins.get('e', 0)
                                    }

                                mm_for_client = 1 + (am_for_client.get('part_margin', 0)/100) + (am_for_client.get('labor_margin', 0)/100) + (am_for_client.get('extra_margin', 0)/100)

                                factor = helpers.CONVERSIONS.get(unit, 1.0)
                                if unit in ['m', 'cm', 'ft', 'in']:
                                    material_sell_price_for_client += base_rate * (qty * factor) * mm_for_client
                                else:
                                    material_sell_price_for_client += base_rate * qty * mm_for_client
                            except (ValueError, TypeError):
                                pass

                        client_raw_grand_total = material_sell_price_for_client + client_labor_cost
                        client_rounded_grand_total = math.ceil(client_raw_grand_total / 100) * 100
                        total_revenue += client_rounded_grand_total

            total_material_expense = sum(float(log.get('total_cost', 0.0)) for log in purchase_log_data)

            total_expenses = total_labor_expense + total_material_expense
            net_profit = total_revenue - total_expenses
            net_profit_margin_percent = (net_profit / total_revenue * 100) if total_revenue != 0 else 0

            st.write("#### Key Financial Metrics")
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric("Total Revenue", f"₹{total_revenue:,.0f}")
            kpi2.metric("Material Expenses", f"₹{total_material_expense:,.0f}")
            kpi3.metric("Labor Expenses", f"₹{total_labor_expense:,.0f}")
            kpi4.metric("Net Profit", f"₹{net_profit:,.0f}", delta=f"{net_profit_margin_percent:,.1f}% Margin")

            st.divider()

            st.write("#### Financial Overview")
            chart_col1, chart_col2 = st.columns(2)

            with chart_col1:
                st.subheader("Revenue vs Expenses")
                # Data Preparation (Bar Chart) - Explicitly cast to float
                chart_data_bar = pd.DataFrame([
                    {'Category': 'Revenue', 'Amount': float(total_revenue)},
                    {'Category': 'Material Expense', 'Amount': float(total_material_expense)},
                    {'Category': 'Labor Expense', 'Amount': float(total_labor_expense)}
                ])
                bar_chart = alt.Chart(chart_data_bar).mark_bar().encode(
                    x=alt.X('Category:N', axis=alt.Axis(title=None, labels=True)),
                    y=alt.Y('Amount:Q', axis=alt.Axis(title="Amount (₹)", labels=True)),
                    color=alt.Color('Category:N', scale=alt.Scale(domain=['Revenue', 'Material Expense', 'Labor Expense'], range=['#2ecc71', '#e74c3c', '#f1c40f']), legend=None), # Updated range
                    tooltip=['Category:N', alt.Tooltip('Amount:Q', format='₹,.0f')]
                ).properties(
                    title='Total Revenue vs Expenses'
                ).configure_axis(
                    labelAngle=0
                )
                st.altair_chart(bar_chart, use_container_width=True)

            with chart_col2:
                st.subheader("Cost Split")
                # Data Preparation (Pie Chart) - Explicitly cast to float
                chart_data_pie = pd.DataFrame([
                    {'Cost Type': 'Material Cost', 'Amount': float(total_material_expense)},
                    {'Cost Type': 'Labor Cost', 'Amount': float(total_labor_expense)}
                ])
                total_cost_for_pie = float(total_material_expense) + float(total_labor_expense)
                if total_cost_for_pie > 0:
                    pie_chart = alt.Chart(chart_data_pie).mark_arc(innerRadius=50).encode( # Added innerRadius
                        theta=alt.Theta("Amount:Q", stack=True), # Explicitly :Q
                        color=alt.Color("Cost Type:N", scale=alt.Scale(domain=['Material Cost', 'Labor Cost'], range=['#F44336', '#FFC107']), legend=alt.Legend(title="Cost Type")), # Updated range
                        order=alt.Order("Amount", sort="descending"),
                        tooltip=['Cost Type:N', alt.Tooltip('Amount:Q', format="₹,.0f"), alt.Tooltip('Amount:Q', format=".1%", title="Percentage")] # Explicitly :N and :Q
                    ).properties(
                        title='Material vs Labor Cost Split'
                    )
                    st.altair_chart(pie_chart, use_container_width=True)
                else:
                    st.info("No material or labor costs to display in the cost split chart.")

        else:
            st.info("No data available to perform Profit & Loss analysis. Please ensure clients, purchases, and settings are configured.")

    except Exception as e:
        st.error(f"An error occurred during Profit & Loss analysis: {e}")
        st.info("Please ensure the database connection is active and data is correctly formatted.")


