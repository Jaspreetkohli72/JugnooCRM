from supabase import create_client
import streamlit as st

try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
    
    res = supabase.table("staff").select("*").limit(1).execute()
    print("Table 'staff' exists.")
except Exception as e:
    print(f"Table 'staff' does not exist or error: {e}")
