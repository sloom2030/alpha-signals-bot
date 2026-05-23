import asyncio
import aiohttp
import logging
import time
from telegram import Bot
from telegram.constants import ParseMode
from aiohttp import web

BOT_TOKEN = "8735462840:AAF5uJI6w5ZVUjxqy58rpawLJP4X_9v51A8"
CHANNEL_ID = -1003924776124
SCAN_INTERVAL_MINUTES = 15

MIN_PRICE_CHANGE_1H = 1.5
MIN_PRICE_CHANGE_4H = 3.0
MIN_PRICE_CHANGE_24H = 3.0
MAX_PRICE_CHANGE_24H = 60.0
COOLDOWN_HOURS = 6

BLACKLIST = ["BUSD", "USDC", "DAI", "TUSD", "FDUSD", "USDP", "WBTC", "BETH"]
BINANCE_BASE = "https://api.binance.us/api/v3"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(message)s")
log = logging.getLogger("AlphaBot")
sent_tokens = {}

async def get_ticker_24h(session):
   try:
       async with session.get(f"{BINANCE_BASE}/ticker/24hr", timeout=aiohttp.ClientTimeout(total=15)) as r:
           if r.status == 200:
               data = await r.json()
               log.info(f"✅ Binance رجع {len(data)} عملة")
               return data
           else:
               log.error(f"Binance status: {r.status}")
   except Exception as e:
       log.error(f"Ticker error: {e}")
   return []

async def get_klines(session, symbol, interval="1h", limit=6):
   try:
       params = {"symbol": symbol, "interval": interval, "limit": limit}
       async with session.get(f"{BINANCE_BASE}/klines", params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
           if r.status == 200:
               return await r.json()
   except:
       pass
   return []

async def analyze_candles(session, symbol):
   klines_1h = await get_klines(session, symbol, "1h", 6)
   klines_4h = await get_klines(session, symbol, "4h", 4)

   if len(klines_1h) < 4 or len(klines_4h) < 2:
       return None

   last_close = float(klines_1h[-1][4])
   prev_close = float(klines_1h[-2][4])
   vol_last = float(klines_1h[-1][5])
   vol_prev = float(klines_1h[-2][5])

   price_change_1h = ((last_close - prev_close) / prev_close) * 100
   vol_surge = vol_last / vol_prev if vol_prev > 0 else 0

   open_4h = float(klines_4h[-1][1])
   close_4h = float(klines_4h[-1][4])
   price_change_4h = ((close_4h - open_4h) / open_4h) * 100

   highs = [float(k[2]) for k in klines_1h[:-1]]
   prev_high = max(highs) if highs else last_close
   is_breakout = last_close > prev_high

   return {
       "price_change_1h": price_change_1h,
       "price_change_4h": price_change_4h,
       "vol_surge": vol_surge,
       "is_breakout": is_breakout,
   }

def estimate_potential(change_1h, change_4h, vol_surge, is_breakout):
   score = 0
   if vol_surge >= 5: score += 3
   elif vol_surge >= 3: score += 2
   elif vol_surge >= 2: score += 1
   if is_breakout: score += 2
   if change_1h >= 8: score += 3
   elif change_1h >= 5: score += 2
   elif change_1h >= 3: score += 1
   if change_4h >= 10: score += 2
   elif change_4h >= 5: score += 1

   if score >= 8: return score, 25, 80, "🔥🔥🔥 قوي جداً"
   elif score >= 6: return score, 15, 40, "🔥🔥 قوي"
   elif score >= 4: return score, 8, 20, "🔥 متوسط"
   else: return score, 3, 10, "⚡ ضعيف"

def is_blacklisted(symbol):
   clean = symbol.replace("USDT", "")
   return any(bl == clean for bl in BLACKLIST)

async def send_signal(bot, data):
   sym = data["symbol"]
   change_1h = data["change_1h"]
   change_4h = data["change_4h"]
   change_24h = data["change_24h"]
   volume = data["volume"]
   vol_surge = data["vol_surge"]
   is_breakout = data["is_breakout"]
   price = data["price"]
   score = data["score"]
   target_low = data["target_low"]
   target_high = data["target_high"]
   strength = data["strength"]

   reasons = []
   if vol_surge >= 2: reasons.append(f"📊 انفجار الحجم x{vol_surge:.1f}")
   if is_breakout: reasons.append("📈 كسر مستوى مقاومة")
   if change_1h >= 3: reasons.append(f"⚡ زخم قوي +{change_1h:.1f}% في ساعة")
   if change_4h >= 5: reasons.append(f"🚀 اتجاه صاعد +{change_4h:.1f}% في 4h")
   reasons_text = "\n".join(reasons) if reasons else "📌 تحليل متعدد المؤشرات"

   msg = f"""🚨 <b>إشارة Alpha | {sym}</b>

💰 السعر: <code>{price}</code> USDT
📊 التغير: 1h <b>{change_1h:+.1f}%</b> | 4h <b>{change_4h:+.1f}%</b> | 24h <b>{change_24h:+.1f}%</b>
💧 الحجم: <b>{volume/1_000_000:.2f}M$</b>
🔄 انفجار الحجم: <b>x{vol_surge:.1f}</b>

🎯 <b>التحليل:</b>
{reasons_text}

📈 <b>التوقع خلال الساعات القادمة:</b>
الهدف: <b>+{target_low}% ~ +{target_high}%</b>
القوة: {strength} (نقاط: {score}/10)

⚠️ <i>ليست نصي
