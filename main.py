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

def is_blacklisted(name):
    return any(kw in name.lower() for kw in BLACKLIST)

def predict_volume(vol):
    return vol * 2.0 if vol < 500000 else vol * 1.5

def predict_change(change, mcap):
    return change * 1.5 if mcap < 5000000 else change * 1.2

async def send_signal(bot, symbol, price, change_1h, mcap, volume, change_24h):
    try:
        pred_vol = predict_volume(volume)
        pred_change = predict_change(change_1h, mcap)
        vol_inc = ((pred_vol / volume - 1) * 100)
        msg = f"🚀 <b>{symbol}</b>\n\nالسعر: ${price:.8f}\nارتفاع 1h: {change_1h:.1f}%\nماركت: ${mcap:,.0f}\nحجم: ${volume:,.0f}\n\n📈 متوقع: {pred_change:.1f}%\n💰 حجم متوقع: ${pred_vol:,.0f}\n📊 زيادة: {vol_inc:.1f}%\n\n⚠️ ليست نصيحة"
        await bot.send_message(chat_id=CHANNEL_ID, text=msg, parse_mode=ParseMode.HTML)
        log.info(f"✅ {symbol}")
    except Exception as e:
        log.error(f"Send error: {e}")

async def fetch_coins(session):
    try:
        params = {"vs_currency": "usd", "order": "market_cap_asc", "per_page": 250}
        async with session.get("https://api.coingecko.com/api/v3/coins/markets", params=params, timeout=10) as resp:
            if resp.status == 200:
                return await resp.json()
    except Exception as e:
        log.error(f"Fetch error: {e}")
    return []

async def scan_market(session, bot):
    log.info("🔍 Scanning...")
    coins = await fetch_coins(session)
    for coin in coins:
        try:
            symbol = str(coin.get("symbol", "")).upper()
            name = str(coin.get("name", ""))
            if not symbol or is_blacklisted(name):
                continue
            mcap = float(coin.get("market_cap") or 0)
            volume = float(coin.get("total_volume") or 0)
            price = float(coin.get("current_price") or 0)
            change_1h = float(coin.get("price_change_percentage_1h_in_currency") or 0)
            change_24h = float(coin.get("price_change_percentage_24h_in_currency") or 0)
            if mcap <= 0 or volume <= 0 or price <= 0:
                continue
            if not (100000 <= mcap <= 20000000):
                continue
            if volume < 50000 or change_1h < 3.0:
                continue
            if symbol not in sent_tokens:
                await send_signal(bot, symbol, price, change_1h, mcap, volume, change_24h)
                sent_tokens[symbol] = time.time()
                await asyncio.sleep(2)
        except Exception as e:
            continue

async def main():
    bot = Bot(token=BOT_TOKEN)
    log.info("✅ Bot started!")
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                await scan_market(session, bot)
                log.info("✅ Done - waiting 15 min...")
                await asyncio.sleep(900)
            except Exception as e:
                log.error(f"Error: {e}")
                await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
