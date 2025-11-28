import os
import sys
import random
import json
from datetime import datetime
from supabase import create_client, Client

# Add parent directory to path to import helpers if needed, 
# but for this standalone script we might just use raw supabase calls.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load secrets (hacky way since we are not in streamlit context)
# We'll assume the user has the secrets in .streamlit/secrets.toml
# and we can parse it or just use the environment variables if set.
# Actually, for this environment, I'll try to read the secrets file directly.

import toml

def get_supabase_client():
    try:
        secrets = toml.load(os.path.join(os.path.dirname(__file__), '..', '.streamlit', 'secrets.toml'))
        url = secrets['SUPABASE_URL']
        key = secrets['SUPABASE_KEY']
        return create_client(url, key)
    except Exception as e:
        print(f"Error loading secrets: {e}")
        return None

def seed_estimates():
    supabase = get_supabase_client()
    if not supabase:
        return

    print("Fetching clients...")
    response = supabase.table("clients").select("*").execute()
    clients = response.data

    # Fetch inventory for random items
    inv_response = supabase.table("inventory").select("*").execute()
    inventory_items = inv_response.data
    
    if not inventory_items:
        print("No inventory items found. Cannot create estimates.")
        return

    updated_count = 0
    for client in clients:
        # Check if estimate exists and has items
        has_estimate = False
        if client.get('internal_estimate'):
            est = client['internal_estimate']
            if isinstance(est, str):
                try:
                    est = json.loads(est)
                except:
                    pass
            if isinstance(est, dict) and est.get('items') and len(est['items']) > 0:
                has_estimate = True
        
        if not has_estimate:
            print(f"Creating demo estimate for client: {client['name']}")
            
            # Generate random items
            num_items = random.randint(3, 6)
            demo_items = []
            for _ in range(num_items):
                item = random.choice(inventory_items)
                qty = random.randint(1, 10)
                demo_items.append({
                    "Item": item['item_name'],
                    "Qty": float(qty),
                    "Unit": item['unit'],
                    "Base Rate": float(item['base_rate']),
                    "Unit Price": 0, # Will be calculated by app
                    "Total Price": 0 # Will be calculated by app
                })
            
            # Create estimate object
            # We leave prices 0 so the app's calculator can handle them, 
            # or we could calculate them here. 
            # For simplicity, let's just save the items and let the app handle calc on load,
            # OR better, let's provide a basic structure.
            
            estimate_data = {
                "items": demo_items,
                "days": random.randint(2, 10),
                "margins": {
                    "p": 15, # Part margin
                    "l": 15, # Labor margin
                    "e": 10  # Extra margin
                }
            }
            
            try:
                supabase.table("clients").update({"internal_estimate": estimate_data}).eq("id", client['id']).execute()
                updated_count += 1
                print(f"  -> Saved estimate with {num_items} items.")
            except Exception as e:
                print(f"  -> Failed to update: {e}")
    
    print(f"\nDone! Updated {updated_count} clients with demo estimates.")

if __name__ == "__main__":
    seed_estimates()
