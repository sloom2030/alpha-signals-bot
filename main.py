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

async def predict_volume(current_volume):
    """تنبؤ حجم التداول المتوقع"""
    if current_volume < 100000:
        return current_volume * 2.5
    elif current_volume < 500000:
        return current_volume * 2.0
    else:
        return current_volume * 1.5

async def main():
    bot = Bot(token=BOT_TOKEN)
    log.info("✅ Bot started!")
    
    current_volume = 47894000
    predicted_volume = await predict_volume(current_volume)
    
    message = (
        f"🚀 <b>ALPHA BOT ONLINE</b>\n\n"
        f"<b>حجم التداول الحالي:</b> ${current_volume:,}\n"
        f"<b>حجم التداول المتوقع:</b> ${predicted_volume:,.0f}\n"
        f"<b>الزيادة المتوقعة:</b> {((predicted_volume/current_volume - 1) * 100):.1f}%\n\n"
        f"✅ البوت يعمل بنجاح"
    )
    
    try:
        await bot.send_message(chat_id=CHANNEL_ID, text=message, parse_mode=ParseMode.HTML)
        log.info("✅ Message sent")
    except Exception as e:
        log.error(f"Error: {e}")
    
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
