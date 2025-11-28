import streamlit as st
from supabase import create_client
import toml

# Load secrets directly since we are not running via streamlit run
try:
    secrets = toml.load(".streamlit/secrets.toml")
    url = secrets["SUPABASE_URL"]
    key = secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)

    res = supabase.table("users").select("password").eq("username", "Jaspreet").execute()
    if res and res.data:
        print(f"PASSWORD_FOUND: {res.data[0]['password']}")
    else:
        print("USER_NOT_FOUND")
except Exception as e:
    print(f"ERROR: {e}")
