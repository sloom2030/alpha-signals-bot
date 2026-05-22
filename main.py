import asyncio
import aiohttp
import logging
import time
from telegram import Bot
from telegram.constants import ParseMode

BOT_TOKEN = "8735462840:AAF5uJI6w5ZVUjxqy58rpawLJP4X_9v51A8"
CHANNEL_ID = -1003924776124

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("AlphaBot")

async def main():
    bot = Bot(token=BOT_TOKEN)
    log.info("✅ Bot started!")
    
    message = "🚀 <b>ALPHA BOT ONLINE</b>\n\nالبوت يعمل الآن ويفحص السوق كل 15 دقيقة\n\n⚠️ تحديث قريب"
    
    try:
        await bot.send_message(chat_id=CHANNEL_ID, text=message, parse_mode=ParseMode.HTML)
        log.info("✅ Test message sent")
    except Exception as e:
        log.error(f"Error: {e}")
    
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
