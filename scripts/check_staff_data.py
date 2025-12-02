from supabase import create_client
import streamlit as st

try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
    
    res = supabase.table("staff").select("*", count="exact").execute()
    print(f"Staff Count: {len(res.data)}")
    for s in res.data:
        print(f"- {s['name']} ({s['status']})")
except Exception as e:
    print(f"Error: {e}")
