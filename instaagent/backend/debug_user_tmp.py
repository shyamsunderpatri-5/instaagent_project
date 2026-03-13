
import sys
import os
from dotenv import load_dotenv
from postgrest import APIResponse

# Add backend to path
sys.path.append(os.getcwd())

from app.db.supabase import get_supabase

def debug_user(email):
    supabase = get_supabase()
    print(f"Checking user: {email}")
    try:
        result = supabase.table("users").select("*").eq("email", email.lower()).execute()
        if not result.data:
            print("User not found.")
            # Let's see some users to be sure
            all_users = supabase.table("users").select("email").limit(5).execute()
            print("Recent users:", [u["email"] for u in all_users.data])
            return
        
        user = result.data[0]
        print(f"User found: {user['id']}")
        print(f"Email: {user['email']}")
        print(f"Is Active: {user.get('is_active')}")
        print(f"Plan: {user.get('plan')}")
        print(f"Created At: {user.get('created_at')}")
        print(f"Onboarding Done: {user.get('onboarding_done')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        debug_user(sys.argv[1])
    else:
        print("Usage: python debug_user.py <email>")
