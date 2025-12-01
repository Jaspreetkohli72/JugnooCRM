
import streamlit as st
from supabase import create_client

try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
    
    res = supabase.table("users").select("username, password").eq("username", "Jaspreet").execute()
    if res and res.data:
        print(f"Password for Jaspreet: {res.data[0]['password']}")
    else:
        print("User Jaspreet not found")
except Exception as e:
    print(f"Error: {e}")
