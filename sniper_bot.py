import os
import requests
import yfinance as yf
import pandas_ta as ta
import google.generativeai as genai
from datetime import datetime

# ==========================================
# 1. THE WATCHLIST (Your Hit List)
# ==========================================
WATCHLIST = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", 
    "ICICIBANK.NS", "SBIN.NS", "TATAMOTORS.NS", "ITC.NS",
    "ADANIENT.NS", "COALINDIA.NS", "ZOMATO.NS", "PAYTM.NS"
]

# SECRETS
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

if GEMINI_KEY:
    try:
        genai.configure(api_key=GEMINI_KEY)
    except: pass

def get_ai_confirmation(ticker, signal, technicals):
    """Asks Gemini: The math says BUY, does the chart context agree?"""
    if not GEMINI_KEY: return "AI Confirmation Unavailable"
    
    models = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-flash-latest']
    
    prompt = (
        f"I have a technical signal for {ticker}.\n"
        f"SIGNAL: {signal}\n"
        f"DATA: {technicals}\n\n"
        "Task: Act as a Technical Analyst. Confirm if this is a high-probability setup or a trap.\n"
        "Keep it to 1 sentence."
    )
    
    for m in models:
        try:
            model = genai.GenerativeModel(m)
            response = model.generate_content(prompt)
            return response.text.strip()
        except: continue
    return "AI Silent"

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}
    requests.post(url, json=payload)

def scan_market():
    print(f"🎯 Sniper Scope Active... [{datetime.now().strftime('%H:%M')}]")
    
    alerts_triggered = 0
    
    for ticker in WATCHLIST:
        try:
            # Get 6 months of data
            df = yf.download(ticker, period="6mo", interval="1d", progress=False)
            if df.empty: continue
            
            # --- CALCULATE INDICATORS ---
            # 1. RSI (Relative Strength Index)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            
            # 2. EMAs (Exponential Moving Averages)
            df['EMA_50'] = ta.ema(df['Close'], length=50)
            df['EMA_200'] = ta.ema(df['Close'], length=200)
            
            # 3. Bollinger Bands
            bb = ta.bbands(df['Close'], length=20, std=2)
            df['BB_UPPER'] = bb['BBU_20_2.0']
            df['BB_LOWER'] = bb['BBL_20_2.0']
            
            # Get latest values
            current_price = df['Close'].iloc[-1].item()
            rsi = df['RSI'].iloc[-1].item()
            ema_50 = df['EMA_50'].iloc[-1].item()
            bb_lower = df['BB_LOWER'].iloc[-1].item()
            bb_upper = df['BB_UPPER'].iloc[-1].item()
            
            signal = None
            setup_name = ""
            
            # --- THE SNIPER LOGIC ---
            
            # SETUP 1: OVERSOLD DIVERGENCE (The "Dip Buy")
            if rsi < 30:
                signal = "BUY"
                setup_name = "🌊 OVERSOLD (RSI < 30)"
            
            # SETUP 2: GOLDEN CROSS (The "Big Trend")
            # We look for price crossing ABOVE EMA 50
            elif current_price > ema_50 and df['Close'].iloc[-2].item() < df['EMA_50'].iloc[-2].item():
                signal = "BUY"
                setup_name = "🚀 MOMENTUM BREAKOUT (Price > 50 EMA)"
                
            # SETUP 3: OVERBOUGHT (The "Profit Take")
            elif rsi > 70:
                signal = "SELL/CAUTION"
                setup_name = "🔥 OVERHEATED (RSI > 70)"

            # --- FIRE ALERT ---
            if signal:
                print(f"💥 Target Acquired: {ticker} ({setup_name})")
                
                tech_data = f"Price: {current_price:.2f} | RSI: {rsi:.2f} | EMA50: {ema_50:.2f}"
                ai_take = get_ai_confirmation(ticker, setup_name, tech_data)
                
                clean_ticker = ticker.replace(".NS", "")
                icon = "🟢" if "BUY" in signal else "🔴"
                
                msg = (
                    f"{icon} <b>SNIPER ALERT: {clean_ticker}</b>\n"
                    f"🎯 <b>Setup:</b> {setup_name}\n"
                    f"📊 <b>Price:</b> {current_price:.2f}\n"
                    f"📉 <b>Indicators:</b> RSI {rsi:.2f}\n\n"
                    f"🤖 <b>AI Confirmation:</b>\n<i>{ai_take}</i>"
                )
                
                send_telegram(msg)
                alerts_triggered += 1
                
        except Exception as e:
            print(f"⚠️ Error scanning {ticker}: {e}")
            continue

    if alerts_triggered == 0:
        print("✅ No setups found. Market is choppy.")

if __name__ == "__main__":
    scan_market()
