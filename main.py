import asyncio
import aiohttp
import logging
import time
from telegram import Bot

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
        return "🔥 STRONG", "احتمال +30%"
    elif score >= 40:
        return "⚡ MEDIUM", "احتمال +20%"
    else:
        return "📊 WEAK", "احتمال +10%"

def is_blacklisted(name):
    name_lower = name.lower()
    return any(keyword in name_lower for keyword in BLACKLIST_KEYWORDS)

async def send_signal(bot, token_name, price_change, liquidity, mcap, strength, prediction):
    try:
        token_name = str(token_name)
        price_change = str(float(price_change))
        liquidity = str(int(liquidity))
        mcap = str(int(mcap))
        strength = str(strength)
        prediction = str(prediction)
        
        message = f"🚀 SIGNAL - {token_name}\n\nسيولة: {liquidity}$\nماركت: {mcap}$\nارتفاع: {price_change}%\n\n{strength}\n{prediction}"
        await bot.send_message(chat_id=CHANNEL_ID, text=message)
        log.info(f"✅ {token_name}")
    except Exception as e:
        log.error(f"Error: {e}")

async def fetch_dex_tokens(session):
    try:
        async with session.get("https://api.dexscreener.com/latest/dex/tokens", timeout=10) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("tokens", [])
    except:
        pass
    return []

async def scan_market(session, bot):
    log.info("🔍 Scanning...")
    try:
        tokens = await fetch_dex_tokens(session)
        for token in tokens:
            try:
                if not isinstance(token, dict):
                    continue
                symbol = token.get("symbol")
                if not symbol or not isinstance(symbol, str):
                    continue
                symbol = symbol.upper()
                name = token.get("name", "")
                if not isinstance(name, str):
                    name = ""
                if is_blacklisted(name):
                    continue
                mcap = token.get("marketCap")
                if mcap is None or mcap is False:
                    continue
                mcap = float(mcap)
                liquidity = token.get("liquidity")
                if liquidity is None or liquidity is False:
                    continue
                liquidity = float(liquidity)
                price_change = token.get("priceChange1h")
                if price_change is None or price_change is False:
                    continue
                price_change = float(price_change)
                if mcap <= 0 or liquidity <= 0:
                    continue
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
            except:
                continue
    except Exception as e:
        log.error(f"Scan: {e}")

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
                log.error(f"Main: {e}")
                await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())

