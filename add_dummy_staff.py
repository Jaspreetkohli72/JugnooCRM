from supabase import create_client
import streamlit as st

try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
    
    supabase.table("staff").insert({
        "name": "Test Staff 1",
        "role": "Technician",
        "phone": "1234567890",
        "salary": 15000,
        "status": "Active"
    }).execute()
    print("Dummy staff added.")
except Exception as e:
    print(f"Error: {e}")
