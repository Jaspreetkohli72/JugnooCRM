from supabase import create_client
import streamlit as st

try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
    
    # Get a single client to check keys
    res = supabase.table("clients").select("*").limit(1).execute()
    if res.data:
        print("Columns:", res.data[0].keys())
        if 'assigned_staff' in res.data[0]:
            print("SUCCESS: assigned_staff column exists.")
        else:
            print("FAILURE: assigned_staff column MISSING.")
    else:
        print("No clients found to check schema.")
except Exception as e:
    print(f"Error: {e}")
