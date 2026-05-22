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
MIN_PRICE_CHANGE_1H = 5.0
MIN_PRICE_CHANGE_24H = 5.0
COOLDOWN_HOURS = 4
BLACKLIST_KEYWORDS = ["elon", "doge2", "moon", "safe", "inu", "baby", "pepe2", "shib2"]
COINGECKO_BASE = "https://api.coingecko.com/api/v3"

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("AlphaBot")
sent_tokens = {}

def calculate_signal_strength(price_change_1h, volume_mcap_ratio, volume_usd, market_cap):
    score = 0
    if price_change_1h >= 15:
        score += 40
    elif price_change_1h >= 10:
        score += 30
    elif price_change_1h >= 5:
        score += 20
    
    if volume_mcap_ratio >= 0.5:
        score += 30
    elif volume_mcap_ratio >= 0.3:
        score += 20
    elif volume_mcap_ratio >= 0.15:
        score += 10
    
    if volume_usd >= 500000:
        score += 20
    elif volume_usd >= 200000:
        score += 15
    elif volume_usd >= 50000:
        score += 10
    
    if market_cap <= 500000:
        score += 15
    elif market_cap <= 2000000:
        score += 10
    
    if score >= 80:
        return "🔥 STRONG", "احتمال +30% في الساعة القادمة"
    elif score >= 50:
        return "⚡ MEDIUM", "احتمال +20% في الساعة القادمة"
    else:
        return "📊 WEAK", "احتمال +10% في الساعة القادمة"

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
        log.error(f"Error: {e}")
    return []

def is_blacklisted(name):
    name_lower = name.lower()
    return any(keyword in name_lower for keyword in BLACKLIST_KEYWORDS)

async def send_signal(bot, token_name, price_change_1h, price_change_24h, market_cap, volume_usd, volume_mcap_ratio, strength, prediction):
    message = (
        f"🚀 <b>ALPHA SIGNAL - {token_name}</b>\n\n"
        f"<b>أسباب الإشارة:</b> 📋\n"
        f"حجم التداول: {volume_usd/1000:.0f}K$\n"
        f"ماركت كاب: {market_cap/1000000:.2f}M$\n"
        f"ارتفاع 1h: {price_change_1h:.1f}% ⚡\n"
        f"ارتفاع 24h: {price_change_24h:.1f}% 📈\n"
        f"ضغط شراء قوي: {volume_mcap_ratio*100:.0f}% 🔥\n\n"
        f"<b>💪 قوة الإشارة: {strength}</b>\n"
        f"<b>{prediction}</b>\n\n"
        f"⚠️ ليست نصيحة استثمارية\n"
        f"#AlphaSignals #LowCap"
    )
    try:
        await bot.send_message(chat_id=CHANNEL_ID, text=message, parse_mode=ParseMode.HTML)
        log.info(f"✅ Signal sent: {token_name}")
    except Exception as e:
        log.error(f"Error sending signal: {e}")

async def scan_market(session, bot):
    log.info("🔍 Scanning market...")
    coins = await fetch_coingecko_data(session)
    
    for coin in coins:
        try:
            symbol = coin.get("symbol", "").upper()
            name = coin.get("name", "")
            market_cap = coin.get("market_cap")
            volume_24h = coin.get("total_volume")
            price_change_1h = coin.get("price_change_percentage_1h_in_currency")
            price_change_24h = coin.get("price_change_percentage_24h_in_currency")
            
            if not symbol or not name:
                continue
            
            if market_cap is None or volume_24h is None:
                continue
            
            if price_change_1h is None or price_change_1h is False:
                price_change_1h = 0
            if price_change_24h is None or price_change_24h is False:
                price_change_24h = 0
            
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
            
            if price_change_24h < MIN_PRICE_CHANGE_24H:
                continue
            
            strength, prediction = calculate_signal_strength(price_change_1h, volume_mcap_ratio, volume_24h, market_cap)
            
            current_time = time.time()
            if symbol in sent_tokens:
                if current_time - sent_tokens[symbol] < COOLDOWN_HOURS * 3600:
                    continue
            
            await send_signal(bot, symbol, price_change_1h, price_change_24h, market_cap, volume_24h, volume_mcap_ratio, strength, prediction)
            sent_tokens[symbol] = current_time
            await asyncio.sleep(1)
        
        except Exception as e:
            log.error(f"Error processing coin: {e}")
            continue

async def main():
    bot = Bot(token=BOT_TOKEN)
    log.info("✅ Bot started!")
    
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                await scan_market(session, bot)
                log.info(f"✅ Scan complete - waiting {SCAN_INTERVAL_MINUTES} minutes...")
                await asyncio.sleep(SCAN_INTERVAL_MINUTES * 60)
            except Exception as e:
                log.error(f"Main loop error: {e}")
                await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
