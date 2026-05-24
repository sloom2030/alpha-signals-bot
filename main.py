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
sent_tokens = {}

BLACKLIST = ["elon", "doge2", "moon", "safe", "inu", "baby", "pepe2", "shib2"]
MIN_MCAP = 100000
MAX_MCAP = 20000000
MIN_VOL = 50000
MIN_CHANGE_1H = 3.0

def is_blacklisted(name):
    return any(kw in name.lower() for kw in BLACKLIST)

def predict_volume(current_vol):
    if current_vol < 100000:
        return current_vol * 2.5
    elif current_vol < 500000:
        return current_vol * 2.0
    else:
        return current_vol * 1.5

def predict_price_change(current_change, mcap):
    if mcap < 500000:
        return current_change * 1.8
    elif mcap < 5000000:
        return current_change * 1.5
    else:
        return current_change * 1.2

async def send_signal(bot, symbol, price, change_1h, mcap, volume, change_24h):
    try:
        pred_volume = predict_volume(volume)
        pred_change = predict_price_change(change_1h, mcap)
        vol_increase = ((pred_volume / volume - 1) * 100)
        
        message = (
            f"🚀 <b>ALPHA SIGNAL - {symbol}</b>\n\n"
            f"<b>البيانات الحالية:</b>\n"
            f"السعر: ${price:.8f}\n"
            f"الارتفاع 1h: {change_1h:.1f}%\n"
            f"الارتفاع 24h: {change_24h:.1f}%\n"
            f"ماركت كاب: ${mcap:,.0f}\n"
            f"حجم التداول: ${volume:,.0f}\n\n"
            f"<b>التنبؤ:</b>\n"
            f"📈 ارتفاع متوقع: {pred_change:.1f}%\n"
            f"💰 حجم متوقع: ${pred_volume:,.0f}\n"
            f"📊 زيادة الحجم: {vol_increase:.1f}%\n\n"
            f"⚠️ ليست نصيحة استثمارية\n"
            f"#AlphaSignals #LowCap"
        )
        
        await bot.send_message(chat_id=CHANNEL_ID, text=message, parse_mode=ParseMode.HTML)
        log.info(f"✅ {symbol}")
    except Exception as e:
        log.error(f"Error: {e}")

async def fetch_coins(session):
    try:
        f"السعر: ${price:.8f}\n"

