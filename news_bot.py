import requests
import os
import json
from datetime import datetime, timedelta

# --- CONFIGURATION ---
NSE_URL = "https://www.nseindia.com/api/corporate-announcements?index=equities"
# Base URL for NSE Documents
PDF_BASE_URL = "https://nsearchives.nseindia.com/corporate/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive"
}

# SECRETS
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# KEYWORDS (Expanded)
WATCHLIST = [
    "Resignation", "Appointment", "Dividend", "Bonus", 
    "Order", "Awarded", "Buyback", "Acquisition", "Merger",
    "Press Release", "Earnings", "Result"
]

def send_telegram_alert(msg):
    if not BOT_TOKEN or not CHAT_ID: return
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "HTML", # Changed to HTML for cleaner links
        "disable_web_page_preview": True
    }
    requests.post(url, json=payload)

def get_nse_data():
    try:
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=HEADERS) 
        response = session.get(NSE_URL, headers=HEADERS)
        return response.json()
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def check_for_fresh_news():
    print(f"🚀 Scanning NSE for Deep Intel... [{datetime.now().strftime('%H:%M:%S')}]")
    data = get_nse_data()
    
    now = datetime.now()
    time_threshold = now - timedelta(minutes=15) 
    
    alert_count = 0
    
    for item in data:
        raw_date = item.get('an_dt') 
        try:
            news_time = datetime.strptime(raw_date, "%d-%b-%Y %H:%M:%S")
        except: continue
            
        if news_time > time_threshold:
            symbol = item.get('symbol')
            category = item.get('desc') # e.g., "Acquisition"
            headline = item.get('subject') # e.g., "Acquires 100% Stake in XYZ"
            
            # Construct PDF Link
            attachment = item.get('attchmntText')
            pdf_link = f"{PDF_BASE_URL}{attachment}" if attachment else "https://www.nseindia.com"
            
            # Combine Category + Headline for search
            full_text = f"{category} {headline}"
            
            if any(k.lower() in full_text.lower() for k in WATCHLIST):
                
                # HTML Formatted Message
                alert_msg = (
                    f"<b>🚨 {symbol}</b> | {category}\n\n"
                    f"📰 <b>{headline}</b>\n\n"
                    f"🔗 <a href='{pdf_link}'>Read Official Document (PDF)</a>\n"
                    f"🕒 <i>{raw_date}</i>"
                )
                
                print(f"Sent Alert: {symbol}")
                send_telegram_alert(alert_msg)
                alert_count += 1

    if alert_count == 0:
        print("✅ No urgent news found.")

if __name__ == "__main__":
    check_for_fresh_news()
