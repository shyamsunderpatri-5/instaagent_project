import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from app.services.telegram_service import set_webhook, set_my_commands
from app.config import settings

async def setup():
    print("🚀 Starting Webhook Setup...")
    
    # 1. Ask for ngrok URL
    print("\n" + "="*50)
    print("Your ngrok URL should look like: https://xxxx-xxxx.ngrok-free.app")
    print("="*50)
    ngrok_url = input("\n👉 Paste your NGROK URL: ").strip().rstrip('/')
    
    if not ngrok_url.startswith("http"):
        print("❌ Invalid URL. Must start with http:// or https://")
        return

    # 2. Setup Telegram
    tg_webhook_url = f"{ngrok_url}/api/v1/webhooks/telegram"
    print(f"\n[Telegram] Registering webhook: {tg_webhook_url}")
    
    try:
        tg_res = await set_webhook(tg_webhook_url)
        print(f"✅ Telegram Result: {tg_res}")
        
        print("[Telegram] Registering bot commands...")
        cmd_res = await set_my_commands()
        print(f"✅ Commands Result: {cmd_res}")
    except Exception as e:
        print(f"❌ Telegram Setup Failed: {e}")

    # 3. Print Instructions for WhatsApp
    wa_webhook_url = f"{ngrok_url}/api/v1/webhooks/whatsapp"
    ig_webhook_url = f"{ngrok_url}/api/v1/webhooks/instagram"
    
    print("\n" + "="*60)
    print("✨ SUCCESS! Next Steps for Meta (WhatsApp/Instagram):")
    print("="*60)
    print(f"\n1. Go to: Meta App → WhatsApp → Configuration")
    print(f"   - Callback URL: {wa_webhook_url}")
    print(f"   - Verify Token: {settings.WHATSAPP_VERIFY_TOKEN}")
    print(f"   - Fields to Subscribe: 'messages', 'message_deliveries', 'message_reads'")
    
    print(f"\n2. Go to: Meta App → App Settings → Basic")
    print(f"   - Ensure 'App Secret' matches what you have in .env")

    print(f"\n3. Go to: Meta App → Webhooks")
    print(f"   - Select 'Instagram' from dropdown")
    print(f"   - Callback URL: {ig_webhook_url}")
    print(f"   - Verify Token: {settings.INSTAGRAM_VERIFY_TOKEN}")
    print(f"   - Fields: 'comments', 'messages', 'story_insights', 'mentions'")
    
    print("\n" + "="*60)
    print("🎉 All set! Your backend is now connected to the world.")
    print("="*60 + "\n")

if __name__ == "__main__":
    import os
    import sys
    # Add backend to path so we can import app
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    asyncio.run(setup())
