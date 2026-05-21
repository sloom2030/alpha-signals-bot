import asyncio
import aiohttp
import logging
import time
from datetime import datetime, timezone
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
BREAKOUT_THRESHOLD = 8.0
MIN_LIQUIDITY_USD = 30000
COOLDOWN_HOURS = 4
BLACKLIST_KEYWORDS = ["elon","doge2","moon","safe","inu","baby","pepe2","shib2"]
COINGECKO_BASE = "https://api.coingecko.com/api/v3"
DEXSCREENER_BASE = "https://api.dexscreener.com/latest/dex"
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("AlphaBot")

def is_blacklisted(name, symbol):
    combined = (name + symbol).lower()
    return any(kw in combined for kw in BLACKLIST_KEYWORDS)

def analyze_coin(coin):
    mcap = coin.get("market_cap") or 0
    volume = coin.get("total_volume") or 0
    change_1h = coin.get("price_change_percentage_1h_in_currency") or 0
    change_24h = coin.get("price_change_percentage_24h") or 0
    name = coin.get("name", "")
    symbol = coin.get("symbol", "").upper()
    if is_blacklisted(name, symbol): return False, 0, ""
    if not (MIN_MARKET_CAP_USD <= mcap <= MAX_MARKET_CAP_USD): return False, 0, ""
    if volume < MIN_VOLUME_USD: return False, 0, ""
    ratio = volume / mcap if mcap else 0
    if change_1h < MIN_PRICE_CHANGE_1H: return False, 0, ""
    if change_24h < MIN_PRICE_CHANGE_6H: return False, 0, ""
    if ratio < MIN_VOLUME_MCAP_RATIO: return False, 0, ""
    score = 5
    reasons = []
    reasons.append(f"📊 حجم التداول: ${volume/1000:.0f}K")
    reasons.append(f"💎 ماركت كاب: ${mcap/1000000:.2f}M")
    reasons.append(f"⚡ ارتفاع 1h: +{change_1h:.1f}%")
    reasons.append(f"📈 ارتفاع 24h: +{change_24h:.1f}%")
    if ratio > 0.5:
        reasons.append(f"🔥 ضغط شراء قوي: {ratio:.0%}")
        score += 3
    if change_1h >= BREAKOUT_THRESHOLD:
        reasons.append("🚀 BREAKOUT قوي!")
        score += 5
    return True, score, "\n".join(reasons)
async def fetch_coins(session):
    url = f"{COINGECKO_BASE}/coins/markets"
    params = {"vs_currency":"usd","order":"volume_desc","per_page":250,"page":1,"price_change_percentage":"1h"}
    try:
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=20)) as r:
            if r.status == 200:
                return await r.json()
    except Exception as e:
        log.error(f"Error: {e}")
    return []

def build_message(coin, reasons):
    name = coin.get("name","")
    symbol = coin.get("symbol","").upper()
    price = coin.get("current_price") or 0
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""
🚀 *ALPHA SIGNAL - {name} (${symbol})*
💵 السعر: `${price:.8f}`
🕐 {now}

📋 *أسباب الإشارة:*
{reasons}

⚠️ ليست نصيحة استثمارية - DYOR
#AlphaSignals #LowCap #{symbol}
""".strip()

class AlphaBot:
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.sent = {}

    def on_cooldown(self, cid):
        last = self.sent.get(cid)
        return last and (time.time()-last) < COOLDOWN_HOURS*3600

    async def send(self, msg):
        try:
            await self.bot.send_message(chat_id=CHANNEL_ID, text=msg, parse_mode=ParseMode.MARKDOWN)
            log.info("Signal sent!")
        except Exception as e:
            log.error(f"Send error: {e}")

    async def run(self):
        log.info("Bot started!")
        await self.send("🤖 *Alpha Signals Bot يعمل الآن!*\n🔍 يسكان السوق كل 15 دقيقة...")
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    coins = await fetch_coins(session)
                    count = 0
                    for coin in coins:
                        cid = coin.get("id","")
                        if self.on_cooldown(cid): continue
                        ok, score, reasons = analyze_coin(coin)
                        if ok and score >= 8:
                            msg = build_message(coin, reasons)
                            await self.send(msg)
                            self.sent[cid] = time.time()
                            count += 1
                            await asyncio.sleep(2)
                    log.info(f"Scan done - {count} signals")
            except Exception as e:
                log.error(f"Scan error: {e}")
            await asyncio.sleep(SCAN_INTERVAL_MINUTES*60)

if __name__ == "__main__":
    asyncio.run(AlphaBot().run())
