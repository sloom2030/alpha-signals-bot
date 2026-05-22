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
MIN_PRICE_CHANGE_1H = 5.0
COOLDOWN_HOURS = 4
BLACKLIST_KEYWORDS = ["elon", "doge2", "moon", "safe", "inu", "baby", "pepe2", "shib2"]

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("AlphaBot")
sent_tokens = {}

def calculate_signal_strength(price_change, liquidity):
    score = 0
    if price_change >= 15:
        score += 40
    elif price_change >= 10:
        score += 30
    elif price_change >= 5:
        score += 20
    
    if liquidity >= 50000:
        score += 30
    elif liquidity >= 20000:
        score += 20
    
    if score >= 70:
        return "🔥 STRONG", "احتمال +30% في الساعة القادمة"
    elif score >= 40:
        return "⚡ MEDIUM", "احتمال +20% في الساعة القادمة"
    else:
        return "📊 WEAK", "احتمال +10% في الساعة القادمة"

def is_blacklisted(name):
    name_lower = name.lower()
    return any(keyword in name_lower for keyword in BLACKLIST_KEYWORDS)

async def send_signal(bot, token_name, price_change, liquidity, mcap, strength, prediction):
    message = (
        f"🚀 <b>ALPHA SIGNAL - {token_name}</b>\n\n"
        f"<b>أسباب الإشارة:</b> 📋\n"
        f"السيولة: ${liquidity:,.0f}\n"
        f"ماركت كاب: ${mcap:,.0f}\n"
        f"الارتفاع الحالي: {price_change:.1f}% ⚡\n\n"
        f"<b>💪 قوة الإشارة: {strength}</b>\n"
        f"<b>{prediction}</b>\n\n"
        f"⚠️ ليست نصيحة استثمارية\n"
        f"#AlphaSignals #LowCap"
    )
    try:
        await bot.send_message(chat_id=CHANNEL_ID, text=message, parse_mode=ParseMode.HTML)
        log.info(f"✅ Signal sent: {token_name}")
    except Exception as e:
        log.error(f"Error: {e}")

async def fetch_dex_tokens(session):
    try:
        url = "https://api.dexscreener.com/latest/dex/tokens"
        async with session.get(url, timeout=10) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("tokens", [])
    except Exception as e:
        log.error(f"Error: {e}")
    return []

async def scan_market(session, bot):
    log.info("🔍 Scanning...")
    tokens = await fetch_dex_tokens(session)
    
    for token in tokens:
        try:
            symbol = token.get("symbol", "").upper()
            name = token.get("name", "")
            
            if not symbol or is_blacklisted(name):
                continue
            
            mcap = float(token.get("marketCap", 0))
            liquidity = float(token.get("liquidity", 0))
            price_change = float(token.get("priceChange1h", 0))
            
            if not (MIN_MARKET_CAP_USD <= mcap <= MAX_MARKET_CAP_USD):
                continue
            if liquidity < MIN_VOLUME_USD:
                continue
            if price_change < MIN_PRICE_CHANGE_1H:
                continue
            
            strength, prediction = calculate_signal_strength(price_change, liquidity)
            
            current_time = time.time()
            if symbol in sent_tokens:
                if current_time - sent_tokens[symbol] < COOLDOWN_HOURS * 3600:
                    continue
            
            await send_signal(bot, symbol, price_change, liquidity, mcap, strength, prediction)
            sent_tokens[symbol] = current_time
            await asyncio.sleep(1)
        
        except Exception as e:
            log.error(f"Error: {e}")

async def main():
    bot = Bot(token=BOT_TOKEN)
    log.info("✅ Bot started!")
    
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                await scan_market(session, bot)
                log.info(f"✅ Done - waiting {SCAN_INTERVAL_MINUTES} minutes...")
                await asyncio.sleep(SCAN_INTERVAL_MINUTES * 60)
            except Exception as e:
                log.error(f"Error: {e}")
                await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
