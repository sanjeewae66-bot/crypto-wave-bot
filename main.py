import requests
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import mplfinance as mpf
import os

TOKEN = "8953307484:AAGLe3UcDueTtlZJ8PepEEjB4Oad588Qw2M"
CHAT_ID = "5703031894"

def get_top_volume_coins(limit=15):
    """Binance 24h market Data වලින් වැඩිම Volume ඇති Top Coins ස්වයංක්‍රීයව ලබා ගැනීම"""
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        res = requests.get(url, timeout=5)
        data = res.json()
        
        ignored = ["USDCUSDT", "FDUSDUSDT", "TUSDUSDT", "USDTUGX", "DAIUSDT", "EURUSDT"]
        usdt_pairs = [
            item for item in data 
            if item['symbol'].endswith('USDT') and item['symbol'] not in ignored
        ]
        
        # Sort by 24h Quote Volume
        sorted_pairs = sorted(usdt_pairs, key=lambda x: float(x['quoteVolume']), reverse=True)
        top_coins = [item['symbol'] for item in sorted_pairs[:limit]]
        return top_coins
    except Exception as e:
        print(f"Market fetch error: {e}")
        return ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT"]

def send_telegram_photo(caption, image_path):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    try:
        with open(image_path, 'rb') as photo_file:
            payload = {"chat_id": CHAT_ID, "caption": caption, "parse_mode": "Markdown"}
            files = {"photo": photo_file}
            requests.post(url, data=payload, files=files, timeout=10)
    except Exception as e:
        print(f"Photo error: {e}")

def get_klines_data(symbol, interval, limit=100):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        res = requests.get(url, timeout=5)
        data = res.json()
        if not isinstance(data, list) or len(data) < 50:
            return None
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'taker_base_vol', 'taker_quote_vol', 'ignore'])
        df['Open'] = df['open'].astype(float)
        df['High'] = df['high'].astype(float)
        df['Low'] = df['low'].astype(float)
        df['Close'] = df['close'].astype(float)
        df['Volume'] = df['volume'].astype(float)
        df.index = pd.to_datetime(df['timestamp'], unit='ms')
        
        typical_price = (df['High'] + df['Low'] + df['Close']) / 3
        df['VWAP'] = (typical_price * df['Volume']).rolling(window=20).sum() / df['Volume'].rolling(window=20).sum()
        df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
        df['Vol_SMA'] = df['Volume'].rolling(window=20).mean()
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        return df[['Open', 'High', 'Low', 'Close', 'Volume', 'VWAP', 'EMA20', 'EMA50', 'Vol_SMA', 'RSI']]
    except Exception as e:
        print(f"Fetch error: {e}")
        return None

def generate_chart(df, symbol, entry, tp, sl, strategy_name):
    try:
        image_path = 'chart.png'
        add_plots = [
            mpf.make_addplot(df['VWAP'], color='purple', width=1.5),
            mpf.make_addplot(df['EMA20'], color='blue', width=1),
            mpf.make_addplot(df['EMA50'], color='orange', width=1),
            mpf.make_addplot([entry]*len(df), color='cyan', linestyle='--'),
            mpf.make_addplot([tp]*len(df), color='lime'),
            mpf.make_addplot([sl]*len(df), color='red')
        ]
        mpf.plot(df.tail(35), type='candle', addplot=add_plots,
                 title=f"{symbol} - {strategy_name}",
                 ylabel='Price ($)', volume=True, style='yahoo', savefig=image_path)
        return image_path
    except Exception as e:
        print(f"Chart gen error: {e}")
        return None

def scan_job():
    # Dynamic Market Scan: Scanning Top 15 Active Volume Coins
    coins_to_scan = get_top_volume_coins(limit=15)
    
    for symbol in coins_to_scan:
        # 1. 5M Scalp Check
        df_5m = get_klines_data(symbol, "5m", 60)
        if df_5m is not None and len(df_5m) >= 2:
            p_curr = df_5m['Close'].iloc[-1]
            vwap = df_5m['VWAP'].iloc[-1]
            vol_curr = df_5m['Volume'].iloc[-1]
            vol_avg = df_5m['Vol_SMA'].iloc[-1]
            rsi = df_5m['RSI'].iloc[-1]
            ema20 = df_5m['EMA20'].iloc[-1]
            ema50 = df_5m['EMA50'].iloc[-1]

            is_vol_spike = vol_curr >= (vol_avg * 1.5)

            if is_vol_spike and (p_curr > vwap) and (ema20 > ema50) and (53 <= rsi <= 68):
                tp = p_curr * 1.012
                sl = p_curr * 0.994
                img = generate_chart(df_5m, symbol, p_curr, tp, sl, "Market Auto-Scan Scalp LONG")
                if img and os.path.exists(img):
                    msg = (f"💥 *[AUTO-SCAN: SCALP LONG]* 💥\n\n"
                           f"🔹 *Pair:* {symbol}\n"
                           f"🔹 *Price:* ${p_curr:,.4f}\n"
                           f"🔹 *Volume Spike:* {vol_curr/vol_avg:.1f}x Avg\n"
                           f"🔹 *RSI:* {rsi:.1f}\n\n"
                           f"🎯 *TP:* ${tp:,.4f}\n"
                           f"🛑 *SL:* ${sl:,.4f}")
                    send_telegram_photo(msg, img)
                    os.remove(img)

            elif is_vol_spike and (p_curr < vwap) and (ema20 < ema50) and (32 <= rsi <= 47):
                tp = p_curr * 0.988
                sl = p_curr * 1.006
                img = generate_chart(df_5m, symbol, p_curr, tp, sl, "Market Auto-Scan Scalp SHORT")
                if img and os.path.exists(img):
                    msg = (f"🔻 *[AUTO-SCAN: SCALP SHORT]* 🔻\n\n"
                           f"🔹 *Pair:* {symbol}\n"
                           f"🔹 *Price:* ${p_curr:,.4f}\n"
                           f"🔹 *Volume Spike:* {vol_curr/vol_avg:.1f}x Avg\n"
                           f"🔹 *RSI:* {rsi:.1f}\n\n"
                           f"🎯 *TP:* ${tp:,.4f}\n"
                           f"🛑 *SL:* ${sl:,.4f}")
                    send_telegram_photo(msg, img)
                    os.remove(img)

        # 2. 1H Swing Check
        df_1h = get_klines_data(symbol, "1h", 70)
        if df_1h is not None and len(df_1h) >= 2:
            p_curr = df_1h['Close'].iloc[-1]
            vwap = df_1h['VWAP'].iloc[-1]
            vol_curr = df_1h['Volume'].iloc[-1]
            vol_avg = df_1h['Vol_SMA'].iloc[-1]
            rsi = df_1h['RSI'].iloc[-1]
            ema20 = df_1h['EMA20'].iloc[-1]
            ema50 = df_1h['EMA50'].iloc[-1]

            if (vol_curr >= vol_avg * 1.3) and (p_curr > vwap) and (ema20 > ema50) and (55 <= rsi <= 70):
                tp = p_curr * 1.03
                sl = p_curr * 0.985
                img = generate_chart(df_1h, symbol, p_curr, tp, sl, "Market Auto-Scan Swing LONG")
                if img and os.path.exists(img):
                    msg = (f"🚀 *[AUTO-SCAN: SWING LONG]* 🚀\n\n"
                           f"🔹 *Pair:* {symbol}\n"
                           f"🔹 *Price:* ${p_curr:,.4f}\n"
                           f"🔹 *RSI:* {rsi:.1f}\n\n"
                           f"🎯 *TP:* ${tp:,.4f}\n"
                           f"🛑 *SL:* ${sl:,.4f}")
                    send_telegram_photo(msg, img)
                    os.remove(img)

if __name__ == "__main__":
    scan_job()
