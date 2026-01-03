import requests
import os
import json
from datetime import datetime, timedelta

# --- CONFIGURATION ---
NSE_URL = "https://www.nseindia.com/api/corporate-announcements?index=equities"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive"
}

# SECRETS FROM GITHUB
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# KEYWORDS TO TRACK
WATCHLIST = [
    "Resignation", "Appointment", "Dividend", "Bonus", 
    "Order", "Awarded", "Buyback", "Acquisition", "Merger"
]

def send_telegram_alert(msg):
    """Sends the message to your phone."""
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ Telegram keys missing!")
        return
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown"
    }
    requests.post(url, json=payload)

def get_nse_data():
    try:
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=HEADERS) 
        response = session.get(NSE_URL, headers=HEADERS)
        return response.json()
    except Exception as e:
        print(f"❌ Error fetching NSE data: {e}")
        return []

def check_for_fresh_news():
    print(f"🚀 Scanning Exchange... [{datetime.now().strftime('%H:%M:%S')}]")
    data = get_nse_data()
    
    # Time Logic: Look back 15 mins
    now = datetime.now()
    time_threshold = now - timedelta(minutes=15) 
    
    alert_count = 0
    
    for item in data:
        raw_date = item.get('an_dt') 
        try:
            # Parse NSE Date format
            news_time = datetime.strptime(raw_date, "%d-%b-%Y %H:%M:%S")
        except:
            continue
            
        if news_time > time_threshold:
            symbol = item.get('symbol')
            desc = item.get('desc')
            
            # Check for Keywords
            if any(k.lower() in desc.lower() for k in WATCHLIST):
                
                # Format Message
                alert_msg = (
                    f"🚨 **{symbol}**\n"
                    f"📝 {desc}\n"
                    f"🕒 `{raw_date}`"
                )
                
                print(f"Sending Alert for {symbol}...")
                send_telegram_alert(alert_msg)
                alert_count += 1

    if alert_count == 0:
        print("✅ No urgent news found.")
    else:
        print(f"✅ Sent {alert_count} alerts.")

if __name__ == "__main__":
    check_for_fresh_news()
