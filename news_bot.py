import requests
import os
import json
from datetime import datetime, timedelta

# --- CONFIGURATION ---
NSE_URL = "https://www.nseindia.com/api/corporate-announcements?index=equities"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive"
}

# 1. TELEGRAM SETUP (We will add this next)
# BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
# CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

WATCHLIST = ["Resignation", "Appointment", "Dividend", "Bonus", "Order", "Awarded", "Buyback"]

def get_nse_data():
    try:
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=HEADERS) # Visit home to get cookies
        response = session.get(NSE_URL, headers=HEADERS)
        return response.json()
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        return []

def check_for_fresh_news():
    print(f"🚀 Checking NSE for News... [{datetime.now().strftime('%H:%M:%S')}]")
    data = get_nse_data()
    
    # Get current time and time 10 mins ago
    now = datetime.now()
    time_threshold = now - timedelta(minutes=15) # Look back 15 mins to be safe
    
    found_news = False
    
    for item in data:
        # NSE Date Format: "03-Jan-2026 16:08:45"
        raw_date = item.get('an_dt') 
        try:
            news_time = datetime.strptime(raw_date, "%d-%b-%Y %H:%M:%S")
        except:
            continue
            
        # If news is NEWER than 15 mins ago
        if news_time > time_threshold:
            symbol = item.get('symbol')
            desc = item.get('desc')
            
            # Check Keywords
            if any(k.lower() in desc.lower() for k in WATCHLIST):
                alert_msg = f"🚨 **{symbol}**: {desc} \n🕒 {raw_date}"
                print(alert_msg)
                
                # TODO: SEND TO TELEGRAM HERE
                # requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={alert_msg}")
                
                found_news = True

    if not found_news:
        print("✅ No urgent news in the last 15 minutes.")

if __name__ == "__main__":
    check_for_fresh_news()
