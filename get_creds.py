import os
import toml
from supabase import create_client

try:
    secrets = toml.load(os.path.join(os.path.dirname(__file__), '.streamlit', 'secrets.toml'))
    url = secrets['SUPABASE_URL']
    key = secrets['SUPABASE_KEY']
    supabase = create_client(url, key)

    res = supabase.table("users").select("*").execute()
    print("Users found:", res.data)
except Exception as e:
    print(f"Error: {e}")
