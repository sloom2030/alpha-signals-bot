import asyncio
import aiohttp
import logging
import time
from telegram import Bot
from telegram.constants import ParseMode
from aiohttp import web

# ============ الإعدادات ============
BOT_TOKEN = "8735462840:AAF5uJI6w5ZVUjxqy58rpawLJP4X_9v51A8"
CHANNEL_ID = -1003924776124
SCAN_INTERVAL_MINUTES = 15

# فلاتر العملات
MIN_VOLUME_USDT = 50_000
MAX_VOLUME_USDT = 50_000_000
MIN_PRICE_CHANGE_1H = 1.5
MIN_PRICE_CHANGE_4H = 3.0
MIN_PRICE_CHANGE_24H = 3.0
MAX_PRICE_CHANGE_24H = 60.0
MIN_TRADES_COUNT = 50
COOLDOWN_HOURS = 6

BLACKLIST = ["USDT", "BUSD", "USDC", "DAI", "TUSD", "FDUSD", "USDP", "WBTC", "BETH"]

BINANCE_BASE = "https://api.binance.com/api/v3"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(message)s")
log = logging.getLogger("AlphaBot")
sent_tokens = {}

async def get_ticker_24h(session):
   try:
       async with session.get(f"{BINANCE_BASE}/ticker/24hr", timeout=aiohttp.ClientTimeout(total=15)) as r:
           if r.status == 200:
               return await r.json()
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

   if vol_surge >= 5:
       score += 3
   elif vol_surge >= 3:
       score += 2
   elif vol_surge >= 2:
       score += 1

   if is_breakout:
       score += 2

   if change_1h >= 8:
       score += 3
   elif change_1h >= 5:
       score += 2
   elif change_1h >= 3:
       score += 1

   if change_4h >= 10:
       score += 2
   elif change_4h >= 5:
       score += 1

   if score >= 8:
       return score, 25, 80, "🔥🔥🔥 قوي جداً"
   elif score >= 6:
       return score, 15, 40, "🔥🔥 قوي"
   elif score >= 4:
       return score, 8, 20, "🔥 متوسط"
   else:
       return score, 3, 10, "⚡ ضعيف"

def is_blacklisted(symbol):
   return any(bl in symbol for bl in BLACKLIST)

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
   if vol_surge >= 2:
       reasons.append(f"📊 انفجار الحجم x{vol_surge:.1f}")
   if is_breakout:
       reasons.append("📈 كسر مستوى مقاومة")
   if change_1h >= 3:
       reasons.append(f"⚡ زخم قوي +{change_1h:.1f}% في ساعة")
   if change_4h >= 5:
       reasons.append(f"🚀 اتجاه صاعد +{change_4h:.1f}% في 4h")

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

⚠ <i>ليست نصيحة مالية - تداول بمسؤولية</i>
#AlphaSignals #{sym.replace('USDT', '')}"""

   try:
       await bot.send_message(chat_id=CHANNEL_ID, text=msg, parse_mode=ParseMode.HTML)
       log.info(f"✅ إشارة أُرسلت: {sym}")
   except Exception as e:
       log.error(f"خطأ في الإرسال: {e}")

async def scan_market(session, bot):
   log.info("🔍 بدء المسح...")
   tickers = await get_ticker_24h(session)

   usdt_pairs = [
       t for t in tickers
       if t["symbol"].endswith("USDT")
       and not is_blacklisted(t["symbol"])
       and float(t["quoteVolume"]) >= MIN_VOLUME_USDT
       and float(t["quoteVolume"]) <= MAX_VOLUME_USDT
       and float(t["count"]) >= MIN_TRADES_COUNT
   ]

   log.info(f"📋 عملات مرشحة: {len(usdt_pairs)}")
   signals_sent = 0

   for ticker in usdt_pairs:
       try:
           symbol = ticker["symbol"]
           change_24h = float(ticker["priceChangePercent"])
           volume = float(ticker["quoteVolume"])
           price = float(ticker["lastPrice"])

           if change_24h > MAX_PRICE_CHANGE_24H or change_24h < MIN_PRICE_CHANGE_24H:
               continue

           ct = time.time()
           if symbol in sent_tokens and ct - sent_tokens[symbol] < COOLDOWN_HOURS * 3600:
               continue

           analysis = await analyze_candles(session, symbol)
           if not analysis:
               continue

           change_1h = analysis["price_change_1h"]
           change_4h = analysis["price_change_4h"]
           vol_surge = analysis["vol_surge"]
           is_breakout = analysis["is_breakout"]

           if change_1h < MIN_PRICE_CHANGE_1H:
               continue
           if change_4h < MIN_PRICE_CHANGE_4H:
               continue
           if vol_surge < 1.5:
               continue

           score, target_low, target_high, strength = estimate_potential(
               change_1h, change_4h, vol_surge, is_breakout
           )

           if score < 2:
               continue

           await send_signal(bot, {
               "symbol": symbol,
               "change_1h": change_1h,
               "change_4h": change_4h,
               "change_24h": change_24h,
               "volume": volume,
               "vol_surge": vol_surge,
               "is_breakout": is_breakout,
               "price": price,
               "score": score,
               "target_low": target_low,
               "target_high": target_high,
               "strength": strength,
           })

           sent_tokens[symbol] = ct
           signals_sent += 1
           await asyncio.sleep(2)

       except Exception as e:
           log.error(f"خطأ في {ticker.get('symbol', '?')}: {e}")
           continue

   log.info(f"✅ انتهى المسح - إشارات أُرسلت: {signals_sent}")

async def health(request):
   return web.Response(text="AlphaBot Running ✅")

async def main():
   bot = Bot(token=BOT_TOKEN)
   log.info("✅ AlphaBot بدأ!")

   app = web.Application()
   app.router.add_get("/", health)
   runner = web.AppRunner(app)
   await runner.setup()
   site = web.TCPSite(runner, "0.0.0.0", 10000)
   await site.start()
   log.info("🌐 Web server شغال على port 10000")

   async with aiohttp.ClientSession() as session:
       while True:
           try:
               await scan_market(session, bot)
               log.info(f"⏳ انتظار {SCAN_INTERVAL_MINUTES} دقيقة...")
               await asyncio.sleep(SCAN_INTERVAL_MINUTES * 60)
           except Exception as e:
               log.error(f"خطأ رئيسي: {e}")
               await asyncio.sleep(60)

if __name__ == "__main__":
   asyncio.run(main())
