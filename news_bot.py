import requests
import os
import json
import google.generativeai as genai
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
GEMINI_KEY = os.environ.get("GEMINI_API_KEY") # New Secret

# Configure AI
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')

WATCHLIST = [
    "Resignation", "Appointment", "Dividend", "Bonus", 
    "Order", "Awarded", "Buyback", "Acquisition", "Merger",
    "Press Release", "Earnings", "Result", "Preferential"
]

def analyze_news_with_ai(symbol, category, headline):
    """Asks Gemini to analyze the news impact."""
    if not GEMINI_KEY: return "AI Analysis Unavailable"
    
    prompt = (
        f"Act as a hedge fund analyst. Analyze this news for Indian stock '{symbol}':\n"
        f"Category: {category}\n"
        f"Headline: {headline}\n\n"
        "Output format:\n"
        "IMPACT: [BULLISH/BEARISH/NEUTRAL]\n"
        "REASON: [One short sentence explaining why]"
    )
    
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return "⚠️ AI Analysis Failed"

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
    print(f"🚀 Scanning NSE (V5.0 AI Analyst)... [{datetime.now().strftime('%H:%M:%S')}]")
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
            
            raw_headline = (item.get('caption') or item.get('subject') or item.get('remarks') or category)
            headline = raw_headline.strip() if raw_headline else "Details N/A"
            
            # --- LINK LOGIC ---
            attachment = item.get('attchmntText')
            if item.get('series') in ['SM', 'ST', 'SME', 'SY']:
                pdf_link = f"{URL_SME}{attachment}"
            else:
                pdf_link = f"{URL_CORP}{attachment}"
            safe_link = f"https://www.nseindia.com/get-quotes/equity?symbol={symbol}"

            full_text = f"{category} {headline}"
            
            if any(k.lower() in full_text.lower() for k in WATCHLIST):
                
                # --- AI ANALYSIS STEP ---
                print(f"🧠 Analyzing {symbol}...")
                ai_insight = analyze_news_with_ai(symbol, category, headline)
                
                # Formatting the Insight
                if "BULLISH" in ai_insight.upper():
                    icon = "🟢"
                elif "BEARISH" in ai_insight.upper():
                    icon = "🔴"
                else:
                    icon = "⚪"

                alert_msg = (
                    f"<b>🚨 {symbol}</b> | {category}\n\n"
                    f"📰 <b>{headline}</b>\n\n"
                    f"{icon} <b>AI INSIGHT:</b>\n<pre>{ai_insight}</pre>\n\n"
                    f"🔗 <a href='{pdf_link}'>Try PDF</a> | <a href='{safe_link}'>View on NSE</a>\n"
                    f"🕒 <i>{raw_date}</i>"
                )
                
                print(f"Sent Alert: {symbol}")
                send_telegram_alert(alert_msg)
                alert_count += 1

    if alert_count == 0:
        print("✅ No urgent news found.")

if __name__ == "__main__":
    check_for_fresh_news()
