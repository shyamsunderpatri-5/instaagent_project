# backend/scripts/telegram_polling.py
import os
import sys
import asyncio
import logging
import httpx

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.services.telegram_bot import handle_message, handle_callback_query
from app.services.telegram_service import delete_webhook

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("telegram_polling")

async def poll_updates():
    token = settings.TELEGRAM_BOT_TOKEN
    if not token or ":" not in token:
        logger.error("❌ Invalid TELEGRAM_BOT_TOKEN in .env")
        return

    logger.info("🚀 Starting Telegram Polling mode...")
    
    # 1. Delete existing webhook so polling works
    try:
        await delete_webhook()
        logger.info("✅ Existing webhook cleared")
    except Exception as e:
        logger.warning("Could not clear webhook (might not be set): %s", e)

    url = f"https://api.telegram.org/bot{token}/getUpdates"
    offset = 0

    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            try:
                params = {"offset": offset, "timeout": 20}
                resp = await client.get(url, params=params)
                
                if resp.status_code != 200:
                    logger.error("Error from Telegram: %s", resp.text)
                    await asyncio.sleep(5)
                    continue

                data = resp.json()
                if not data.get("ok"):
                    logger.error("Telegram error: %s", data)
                    await asyncio.sleep(5)
                    continue

                for update in data.get("result", []):
                    update_id = update["update_id"]
                    offset = update_id + 1
                    
                    logger.info("📦 Update received: %s", update)
                    
                    if "message" in update:
                        msg = update["message"]
                        chat_id = msg.get("chat", {}).get("id")
                        if chat_id:
                            logger.info("📩 Message from %s", chat_id)
                            await handle_message(chat_id, msg)
                    
                    elif "callback_query" in update:
                        cb = update["callback_query"]
                        logger.info("🔘 Callback from %s", cb.get("from", {}).get("id"))
                        await handle_callback_query(cb)

            except Exception as e:
                logger.error("Polling error: %s", e)
                await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(poll_updates())
    except KeyboardInterrupt:
        logger.info("👋 Polling stopped")
