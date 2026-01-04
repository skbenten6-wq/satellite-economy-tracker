import os
import requests
import yfinance as yf
import pandas_ta as ta
import google.generativeai as genai
from datetime import datetime
from watchlist_manager import load_watchlist
from paper_trader import execute_buy, execute_sell # IMPORT THE LEDGER

# SECRETS
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

if GEMINI_KEY:
    try:
        genai.configure(api_key=GEMINI_KEY)
    except: pass

def get_ai_confirmation(ticker, signal, technicals):
    if not GEMINI_KEY: return "AI Unavailable"
    model = genai.GenerativeModel('gemini-2.5-flash')
    prompt = (f"Technical Signal for {ticker}: {signal}. Data: {technicals}. "
              "Confirm if this is a good trade setup. Keep it very short.")
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except: return "AI Silent"

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def scan_market():
    print(f"🎯 Sniper Scope Active... [{datetime.now().strftime('%H:%M')}]")
    watchlist = load_watchlist() # Load dynamic list
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    for ticker in watchlist:
        try:
            # Clean ticker format
            if not ticker.endswith(".NS"): ticker = f"{ticker}.NS"
            
            df = yf.download(ticker, period="6mo", interval="1d", progress=False)
            if df.empty: continue
            
            # Indicators
            df['RSI'] = ta.rsi(df['Close'], length=14)
            rsi = df['RSI'].iloc[-1].item()
            price = df['Close'].iloc[-1].item()
            
            # --- TRADING LOGIC ---
            
            # 1. BUY SIGNAL (RSI < 30)
            if rsi < 30:
                success, msg = execute_buy(ticker, price, today_str)
                if success:
                    ai_msg = get_ai_confirmation(ticker, "OVERSOLD BUY", f"RSI {rsi}")
                    send_telegram(f"🟢 **PAPER TRADE: BOUGHT {ticker}**\nPrice: {price:.2f}\nReason: RSI {rsi:.2f} (Oversold)\n\n🤖 AI: {ai_msg}")
            
            # 2. SELL SIGNAL (RSI > 70)
            elif rsi > 70:
                success, msg = execute_sell(ticker, price, today_str)
                if success:
                    send_telegram(f"🔴 **PAPER TRADE: SOLD {ticker}**\nPrice: {price:.2f}\nResult: {msg}\nReason: RSI {rsi:.2f} (Overbought)")

        except Exception as e:
            print(f"⚠️ Error {ticker}: {e}")
            continue

if __name__ == "__main__":
    scan_market()
