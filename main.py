import asyncio
import aiohttp
import logging
import time
from telegram import Bot
from telegram.constants import ParseMode

BOT_TOKEN = "8735462840:AAF5uJI6w5ZVUjxqy58rpawLJP4X_9v51A8"
CHANNEL_ID = -1003924776124

SCAN_INTERVAL_MINUTES = 15
MIN_VOLUME_USD = 50000
MAX_MARKET_CAP_USD = 20000000
MIN_MARKET_CAP_USD = 100000
MIN_VOLUME_MCAP_RATIO = 0.15
MIN_PRICE_CHANGE_1H = 3.0
MIN_PRICE_CHANGE_6H = 5.0
COOLDOWN_HOURS = 4
BLACKLIST_KEYWORDS = ["elon", "doge2", "moon", "safe", "inu", "baby", "pepe2", "shib2"]
COINGECKO_BASE = "https://api.coingecko.com/api/v3"

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("AlphaBot")
sent_tokens = {}

async def fetch_coingecko_data(session):
    try:
        params = {"vs_currency": "usd", "order": "market_cap_desc", "per_page": 250, "sparkline": False, "price_change_percentage": "1h,24h"}
        async with session.get(f"{COINGECKO_BASE}/coins/markets", params=params, timeout=10) as resp:
            if resp.status == 200:
                return await resp.json()
    except:
        pass
    return []

def is_blacklisted(name):
    return any(kw in name.lower() for kw in BLACKLIST_KEYWORDS)

async def send_signal(bot, symbol, p1h, p24h, mcap, vol, ratio):
    msg = f"🚀 <b>{symbol}</b>\n\nحجم: {vol/1000:.0f}K$ | ماركت: {mcap/1000000:.2f}M$\n1h: {p1h:.1f}% | 24h: {p24h:.1f}%\nضغط: {ratio*100:.0f}%\n\n⚠️ ليست نصيحة\n#AlphaSignals"
    try:
        await bot.send_message(chat_id=CHANNEL_ID, text=msg, parse_mode=ParseMode.HTML)
        log.info(f"✅ {symbol}")
    except Exception as e:
        log.error(f"Error: {e}")

async def scan_market(session, bot):
    log.info("🔍 Scanning...")
    coins = await fetch_coingecko_data(session)
    
    for coin in coins:
        try:
            sym = coin.get("symbol", "").upper()
            name = coin.get("name", "")
            mcap = float(coin.get("market_cap") or 0)
            vol = float(coin.get("total_volume") or 0)
            p1h = float(coin.get("price_change_percentage_1h_in_currency") or 0)
            p24h = float(coin.get("price_change_percentage_24h_in_currency") or 0)
            
            if not sym or is_blacklisted(name):
                continue
            if not (MIN_MARKET_CAP_USD <= mcap <= MAX_MARKET_CAP_USD):
                continue
            if vol < MIN_VOLUME_USD:
                continue
            
            ratio = vol / mcap if mcap > 0 else 0
            
            if ratio < MIN_VOLUME_MCAP_RATIO or p1h < MIN_PRICE_CHANGE_1H or p24h < MIN_PRICE_CHANGE_6H:
                continue
            
            ct = time.time()
            if sym in sent_tokens and ct - sent_tokens[sym] < COOLDOWN_HOURS * 3600:
                continue
            
            await send_signal(bot, sym, p1h, p24h, mcap, vol, ratio)
            sent_tokens[sym] = ct
            await asyncio.sleep(1)
        except:
            continue

async def main():
    bot = Bot(token=BOT_TOKEN)
    log.info("✅ Bot started!")
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                await scan_market(session, bot)
                log.info(f"✅ Done - waiting {SCAN_INTERVAL_MINUTES} min...")
                await asyncio.sleep(SCAN_INTERVAL_MINUTES * 60)
            except Exception as e:
                log.error(f"Error: {e}")
                await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
