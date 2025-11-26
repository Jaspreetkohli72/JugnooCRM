import os
from supabase import create_client, Client
from utils.auth import hash_password

# Load environment variables
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

def main():
    print("Fetching users...")
    res = supabase.table("users").select("id, username, password").execute()
    if res.data:
        for user in res.data:
            # Check if the password is already hashed
            if not user["password"].startswith("$2b$"):
                print(f"Hashing password for user: {user['username']}")
                hashed_pw = hash_password(user["password"])
                supabase.table("users").update({"password": hashed_pw}).eq("id", user["id"]).execute()
            else:
                print(f"Password for user {user['username']} is already hashed.")
    print("Password hashing complete.")

if __name__ == "__main__":
    main()
