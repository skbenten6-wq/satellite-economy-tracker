import requests
import os
import json
from datetime import datetime, timedelta

# --- CONFIGURATION ---
NSE_API = "https://www.nseindia.com/api/corporate-announcements?index=equities"
URL_CORP = "https://nsearchives.nseindia.com/corporate/"
URL_SME = "https://nsearchives.nseindia.com/sme/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive"
}

# SECRETS
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# KEYWORDS
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
        "parse_mode": "HTML", 
        "disable_web_page_preview": True
    }
    requests.post(url, json=payload)

def get_nse_data():
    try:
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=HEADERS) 
        response = session.get(NSE_API, headers=HEADERS)
        return response.json()
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def check_for_fresh_news():
    print(f"🚀 Scanning NSE (V4.0 Safety Net)... [{datetime.now().strftime('%H:%M:%S')}]")
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
            category = item.get('desc') 
            
            # --- FIX 1: HEADLINE (Keep what works) ---
            raw_headline = (
                item.get('caption') or 
                item.get('subject') or 
                item.get('remarks') or 
                category
            )
            headline = raw_headline.strip() if raw_headline else "Details N/A"
            
            # --- FIX 2: THE SAFETY NET LINKS ---
            attachment = item.get('attchmntText')
            
            # Try to detect SME (Small Enterprise)
            # SME symbols are often different or have specific series, 
            # but if we can't be sure, we default to CORP.
            # If this link fails, the user hits "View on NSE"
            if item.get('series') in ['SM', 'ST', 'SME', 'SY']:
                pdf_link = f"{URL_SME}{attachment}"
            else:
                pdf_link = f"{URL_CORP}{attachment}"
                
            # THE GUARANTEED LINK (Company Quote Page)
            # This page always exists and lists recent announcements
            safe_link = f"https://www.nseindia.com/get-quotes/equity?symbol={symbol}"

            # Filter Logic
            full_text = f"{category} {headline}"
            
            if any(k.lower() in full_text.lower() for k in WATCHLIST):
                
                alert_msg = (
                    f"<b>🚨 {symbol}</b> | {category}\n\n"
                    f"📰 <b>{headline}</b>\n\n"
                    f"🔗 <a href='{pdf_link}'>Try PDF</a> | <a href='{safe_link}'>View on NSE (Guaranteed)</a>\n"
                    f"🕒 <i>{raw_date}</i>"
                )
                
                print(f"Sent Alert: {symbol}")
                send_telegram_alert(alert_msg)
                alert_count += 1

    if alert_count == 0:
        print("✅ No urgent news found.")

if __name__ == "__main__":
    check_for_fresh_news()
