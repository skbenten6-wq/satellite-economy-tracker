import os
import time
import requests
import urllib.parse
import yfinance as yf
import google.generativeai as genai
from GoogleNews import GoogleNews
from datetime import datetime

# ==========================================
# 1. THE 25-POINT MATRIX
# ==========================================

LIVE_INDICATORS = {
    "1. USD/INR":       "INR=X",
    "2. US 10Y Yield":  "^TNX",
    "5. Dollar Index":  "DX-Y.NYB",
    "16. India VIX":    "^INDIAVIX",
    "17. Nifty 50":     "^NSEI",     
    "22. Copper":       "HG=F",
    "15. Crude Oil":    "CL=F",
    "Gold":             "GC=F"       
}

DATA_HUNT_QUERIES = [
    "3. US Fed Funds Rate current",
    "4. FII DII activity yesterday India",
    "6. India GST collections latest month",
    "7. India Auto Sales numbers monthly",
    "8. India IIP data latest",
    "9. India Core Sector growth latest",
    "10. India Power consumption demand latest",
    "11. India Bank Credit growth rate",
    "12. India 10-Year G-Sec yield current",
    "13. Indian Railways freight loading data",
    "14. IMD Monsoon forecast India latest",
    "15. Baltic Dry Index current",
    "17. Nifty 50 PE ratio current",
    "18. India Mutual Fund SIP inflows monthly",
    "19. India Fiscal Deficit latest",
    "20. India Current Account Deficit CAD",
    "21. India Forex Reserves latest",
    "23. US Non-Farm Payrolls data",
    "24. Nifty 50 EPS growth earnings",
    "25. RBI Capacity Utilization OBICUS"
]

# SECRETS
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

if GEMINI_KEY:
    try:
        genai.configure(api_key=GEMINI_KEY)
    except: pass

def get_live_market_data():
    """Fetches real-time prices for Group A"""
    data_summary = "📊 <b>LIVE MARKET DASHBOARD</b>\n\n"
    raw_text = "--- LIVE DATA ---\n" 
    
    print("📊 Fetching Live Tickers...")
    
    for name, ticker in LIVE_INDICATORS.items():
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="5d")
            if not hist.empty:
                price = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2]
                change = ((price - prev) / prev) * 100
                
                icon = "🟢" if change >= 0 else "🔴"
                data_summary += f"{icon} <b>{name}</b>: <code>{price:.2f}</code> ({change:+.2f}%)\n"
                raw_text += f"{name}: {price:.2f} ({change:+.2f}%)\n"
            else:
                data_summary += f"⚪ <b>{name}</b>: N/A\n"
                raw_text += f"{name}: N/A\n"
        except:
            data_summary += f"⚪ <b>{name}</b>: Error\n"
            
    return data_summary, raw_text

def hunt_for_economic_data():
    """Scrapes news headlines to find the latest Economic Data for Group B"""
    data_summary = "📰 <b>ECONOMIC NEWS FEED</b>\n\n"
    raw_text = "\n--- NEWS DATA ---\n" 
    
    print("🕵️‍♂️ Hunting for Economic Reports...")
    
    googlenews = GoogleNews(period='7d') 
    
    for query in DATA_HUNT_QUERIES:
        googlenews.clear()
        googlenews.search(query)
        results = googlenews.result()
        
        indicator_name = query.split(' ', 1)[1]
        
        if results:
            top_result = results[0]
            title = top_result['title']
            link = top_result['link']
            
            # Create Backup Search Link
            safe_query = urllib.parse.quote(title)
            search_link = f"https://www.google.com/search?q={safe_query}"
            
            data_summary += (
                f"🔹 <b>{indicator_name}</b>\n"
                f"└ <a href='{link}'>{title}</a>\n"
                f"   🔎 <a href='{search_link}'>Google Search</a>\n\n"
            )
            raw_text += f"{indicator_name}: {title}\n"
        else:
            data_summary += f"🔸 {indicator_name}: No recent news.\n"
            raw_text += f"{indicator_name}: No recent news\n"
            
    return data_summary, raw_text

def generate_grand_strategy(full_data_text):
    """Sends the data to Gemini. Returns (Success_Bool, Content)"""
    if not GEMINI_KEY: return False, "⚠️ AI Key Missing"
    
    # MODELS FROM YOUR SCREENSHOT (Verified)
    models = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-flash-latest']
    
    prompt = (
        "Act as a Chief Economist. Analyze these 25 macro indicators for India:\n\n"
        f"{full_data_text}\n\n"
        "OUTPUT FORMAT:\n"
        "🌍 <b>MACRO REGIME:</b> [Name]\n"
        "✅ <b>TAILWINDS:</b> [Top 3]\n"
        "⚠️ <b>HEADWINDS:</b> [Top 3]\n"
        "🏗️ <b>SECTOR STRATEGY:</b> [Allocations]"
    )
    
    last_error = "Unknown Error"
    
    for m in models:
        for attempt in range(2): 
            try:
                print(f"🧠 Thinking with {m} (Attempt {attempt+1})...")
                model = genai.GenerativeModel(m)
                response = model.generate_content(prompt)
                return True, response.text.strip()
                
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg:
                    print(f"⚠️ Quota Hit ({m}). Cooling 60s...")
                    time.sleep(60) # Increased to 60s
                    continue
                
                print(f"❌ Error ({m}): {error_msg}")
                last_error = error_msg
                break # Move to next model if not 429
            
    return False, f"⚠️ <b>AI Analysis Failed.</b>\nReason: {last_error}"

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID: return
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID, 
        "text": msg, 
        "parse_mode": "HTML", 
        "disable_web_page_preview": True
    }
    requests.post(url, json=payload)

def run_omni_scanner():
    print(f"🚀 Starting Omni-Scanner... [{datetime.now().strftime('%H:%M')}]")
    
    # 1. Gather & Send Raw Data First
    telegram_live, raw_live = get_live_market_data()
    send_telegram(telegram_live)
    
    telegram_news, raw_news = hunt_for_economic_data()
    send_telegram(telegram_news)
    
    # 2. Prepare Dossier
    full_dossier = raw_live + raw_news
    
    # 3. Attempt AI Analysis
    print("🧠 Analyzing Matrix...")
    success, analysis = generate_grand_strategy(full_dossier)
    
    if success:
        # If AI works, send the nice report
        final_msg = (
            f"🏛️ <b>THE OMNI-SCANNER REPORT</b>\n"
            f"<i>{datetime.now().strftime('%d %b %Y')}</i>\n\n"
            f"{analysis}\n\n"
            f"🔍 <i>Based on 25-Point Macro Matrix</i>"
        )
        send_telegram(final_msg)
        print("✅ AI Report Sent.")
    else:
        # IF AI FAILS: Send the error + THE RAW DATA
        print("❌ AI Failed. Sending Raw Data fallback.")
        
        # We wrap the data in <pre> tags so it's easy to copy
        fallback_msg = (
            f"{analysis}\n\n"
            f"📋 <b>RAW DATA SUMMARY (Copy & Paste to AI):</b>\n"
            f"<pre>{full_dossier}</pre>"
        )
        send_telegram(fallback_msg)

if __name__ == "__main__":
    run_omni_scanner()
