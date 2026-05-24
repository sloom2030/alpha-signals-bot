import asyncio
import aiohttp
import logging
import time
from datetime import datetime, timezone
from telegram import Bot
from telegram.constants import ParseMode

BOT_TOKEN = "8735462840:AAF5uJI6w5ZVUjxqy58rpawLJP4X_9v51A8"
CHANNEL_ID = -1001234567890

SCAN_INTERVAL_MINUTES = 15
MIN_VOLUME_USD = 50000
MAX_MARKET_CAP_USD = 20000000
MIN_MARKET_CAP_USD = 100000
MIN_VOLUME_MCAP_RATIO = 0.15
MIN_PRICE_CHANGE_1H = 3.0
MIN_PRICE_CHANGE_6H = 5.0
BREAKOUT_THRESHOLD = 8.0
MIN_LIQUIDITY_USD = 30000
COOLDOWN_HOURS = 4
BLACKLIST_KEYWORDS = ["elon", "doge2", "moon", "safe", "inu", "baby", "pepe2", "shib2"]
COINGECKO_BASE = "https://api.coingecko.com/api/v3"
DEXSCREENER_BASE = "https://api.dexscreener.com/latest/dex/search"

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("AlphaBot")

sent_tokens = {}

async def fetch_coingecko_data(session):
    try:
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 250,
            "sparkline": False,
            "price_change_percentage": "1h,24h"
        }
        
        url = f"{COINGECKO_BASE}/coins/markets"
        async with session.get(url, params=params, timeout=10) as resp:
            if resp.status == 200:
                return await resp.json()
    except Exception as e:
        log.error(f"CoinGecko Error: {e}")
    return []

async def fetch_dex_data(session, token_symbol):
    try:
        async with session.get(
            f"{DEXSCREENER_BASE}?q={token_symbol}",
            timeout=10
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get("pairs"):
                    return data["pairs"][0]
    except Exception as e:
        log.error(f"DexScreener Error: {e}")
    return None

def is_blacklisted(name):
    name_lower = name.lower()
    return any(keyword in name_lower for keyword in BLACKLIST_KEYWORDS)

async def send_signal(bot, token_name, price_change_1h, price_change_24h, 
                      market_cap, volume_usd, volume_mcap_ratio):
    message = (
        f"🚀 <b>ALPHA SIGNAL - {token_name}</b>\n\n"
        f"<b>أسباب الإشارة:</b> 📋\n"
        f"حجم التداول: {volume_usd/1000:.0f}K$\n"
        f"ماركت كاب: {market_cap/1000000:.2f}M$\n"
        f"ارتفاع 1h: {price_change_1h:.1f}% ⚡\n"
        f"ارتفاع 24h: {price_change_24h:.1f}% 📈\n"
        f"ضغط شراء قوي: {volume_mcap_ratio*100:.0f}% 🔥\n\n"
        f"⚠️ ليست نصيحة استثمارية\n"
        f"#AlphaSignals #LowCap #ZEST"
    )
    
    try:
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=message,
            parse_mode=ParseMode.HTML
        )
        log.info(f"✅ إشارة مرسلة: {token_name}")
    except Exception as e:
        log.error(f"خطأ الإرسال: {e}")

async def scan_market(session, bot):
    log.info("🔍 بدء الفحص...")
    
    coins = await fetch_coingecko_data(session)
    
    for coin in coins:
        try:
            symbol = coin.get("symbol", "").upper()
            name = coin.get("name", "")
            market_cap = coin.get("market_cap") or 0
            volume_24h = coin.get("total_volume") or 0
            price_change_1h = coin.get("price_change_percentage_1h_in_currency") or 0
            price_change_24h = coin.get("price_change_percentage_24h_in_currency") or 0
            
            if is_blacklisted(name):
                continue
            
            if not (MIN_MARKET_CAP_USD <= market_cap <= MAX_MARKET_CAP_USD):
                continue
            
            if volume_24h < MIN_VOLUME_USD:
                continue
            
            volume_mcap_ratio = volume_24h / market_cap if market_cap > 0 else 0
            
            if volume_mcap_ratio < MIN_VOLUME_MCAP_RATIO:
                continue
            
            if price_change_1h < MIN_PRICE_CHANGE_1H:
                continue
            
            if price_change_24h < MIN_PRICE_CHANGE_6H:
                continue
            
            current_time = time.time()
            if symbol in sent_tokens:
                if current_time - sent_tokens[symbol] < COOLDOWN_HOURS * 3600:
                    continue
            
            await send_signal(bot, symbol, price_change_1h, price_change_24h, market_cap, volume_24h, volume_mcap_ratio)
            sent_tokens[symbol] = current_time
            await asyncio.sleep(1)
        
        except Exception as e:
            log.error(f"خطأ في معالجة {symbol}: {e}")
            continue

async def main():
    bot = Bot(token=BOT_TOKEN)
    log.info("✅ البوت بدأ!")
    
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                await scan_market(session, bot)
                log.info(f"✅ الفحص انتهى - انتظار {SCAN_INTERVAL_MINUTES} دقائق...")
                await asyncio.sleep(SCAN_INTERVAL_MINUTES * 60)
            except Exception as e:
                log.error(f"خطأ في الحلقة الرئيسية: {e}")
                await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
