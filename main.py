import requests
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import mplfinance as mpf
import os

TOKEN = "8953307484:AAGLe3UcDueTtlZJ8PepEEjB4Oad588Qw2M"
CHAT_ID = "5703031894"
COINS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT"]

def send_telegram_photo(caption, image_path):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    try:
        with open(image_path, 'rb') as photo_file:
            payload = {"chat_id": CHAT_ID, "caption": caption, "parse_mode": "Markdown"}
            files = {"photo": photo_file}
            requests.post(url, data=payload, files=files, timeout=10)
    except Exception as e:
        print(f"Photo error: {e}")

def get_klines_data(symbol, interval, limit=50):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        res = requests.get(url, timeout=5)
        data = res.json()
        if not isinstance(data, list) or len(data) < 2:
            return None
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'taker_base_vol', 'taker_quote_vol', 'ignore'])
        df['Open'] = df['open'].astype(float)
        df['High'] = df['high'].astype(float)
        df['Low'] = df['low'].astype(float)
        df['Close'] = df['close'].astype(float)
        df['Volume'] = df['volume'].astype(float)
        df.index = pd.to_datetime(df['timestamp'], unit='ms')
        return df[['Open', 'High', 'Low', 'Close', 'Volume']]
    except Exception as e:
        print(f"Fetch error: {e}")
        return None

def generate_chart(df, symbol, entry, tp, sl, tf_name):
    try:
        image_path = 'chart.png'
        add_plots = [
            mpf.make_addplot([entry]*len(df), color='cyan', linestyle='--'),
            mpf.make_addplot([tp]*len(df), color='lime'),
            mpf.make_addplot([sl]*len(df), color='red')
        ]
        mpf.plot(df, type='candle', addplot=add_plots,
                 title=f"{symbol} {tf_name} Analysis",
                 ylabel='Price ($)', volume=True, style='yahoo', savefig=image_path)
        return image_path
    except Exception as e:
        print(f"Chart gen error: {e}")
        return None

def scan_job():
    for symbol in COINS:
        # 1. Scalp Check (5M)
        df_5m = get_klines_data(symbol, "5m", 40)
        if df_5m is not None and len(df_5m) >= 2:
            p_curr = df_5m['Close'].iloc[-1]
            p_prev = df_5m['Close'].iloc[-2]
            chg_5m = ((p_curr - p_prev) / p_prev) * 100
            
            if abs(chg_5m) >= 0.3:
                status = "⚡ SCALP LONG" if chg_5m > 0 else "🔴 SCALP SHORT"
                tp = p_curr * 1.008 if chg_5m > 0 else p_curr * 0.992
                sl = p_curr * 0.996 if chg_5m > 0 else p_curr * 1.004
                
                img = generate_chart(df_5m, symbol, p_curr, tp, sl, "5M Scalp")
                if img and os.path.exists(img):
                    msg = f"⚡ *[5M SCALP SIGNAL]* ⚡\n\n🔹 *Pair:* {symbol}\n🔹 *Price:* ${p_curr:,.4f}\n🔹 *Status:* {status}\n🎯 *TP:* ${tp:,.4f}\n🛑 *SL:* ${sl:,.4f}\n"
                    send_telegram_photo(msg, img)
                    os.remove(img)

        # 2. Swing Check (1H)
        df_1h = get_klines_data(symbol, "1h", 50)
        if df_1h is not None and len(df_1h) >= 2:
            p_curr = df_1h['Close'].iloc[-1]
            p_prev = df_1h['Close'].iloc[-2]
            chg_1h = ((p_curr - p_prev) / p_prev) * 100
            
            if abs(chg_1h) >= 0.8:
                status = "🚀 Wave 3 Impulse" if chg_1h > 0 else "⚠️ Wave 4 Correction"
                tp = p_curr * 1.025 if chg_1h > 0 else p_curr * 0.975
                sl = p_curr * 0.985 if chg_1h > 0 else p_curr * 1.015
                
                img = generate_chart(df_1h, symbol, p_curr, tp, sl, "1H Swing")
                if img and os.path.exists(img):
                    msg = f"📊 *[1H SWING SIGNAL]* 📊\n\n🔹 *Pair:* {symbol}\n🔹 *Price:* ${p_curr:,.4f}\n🔹 *Status:* {status}\n🎯 *TP:* ${tp:,.4f}\n🛑 *SL:* ${sl:,.4f}\n"
                    send_telegram_photo(msg, img)
                    os.remove(img)

if __name__ == "__main__":
    scan_job()
