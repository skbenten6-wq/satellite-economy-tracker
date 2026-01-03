import os
import time
import requests
import yfinance as yf
import google.generativeai as genai
from GoogleNews import GoogleNews
from datetime import datetime

# ==========================================
# 1. THE 25-POINT MATRIX
# ==========================================

# GROUP A: LIVE TICKERS (Yahoo Finance)
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

# GROUP B: DATA HUNT (Google News)
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

# AI CONFIG
if GEMINI_KEY:
    try:
        genai.configure(api_key=GEMINI_KEY)
    except: pass

def get_live_market_data():
    """Fetches real-time prices for Group A"""
    data_summary = "📊 **LIVE MARKET DASHBOARD**\n"
    raw_text = "LIVE DATA:\n" # For AI
    
    print("📊 Fetching Live Tickers...")
    
    for name, ticker in LIVE_INDICATORS.items():
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="5d")
            if not hist.empty:
                price = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2]
                change = ((price - prev) / prev) * 100
                
                # Format for Telegram
                icon = "🟢" if change >= 0 else "🔴"
                data_summary += f"{icon} *{name}*: `{price:.2f}` ({change:+.2f}%)\n"
                raw_text += f"{name}: {price:.2f} ({change:+.2f}%)\n"
            else:
                data_summary += f"⚪ *{name}*: N/A\n"
        except:
            data_summary += f"⚪ *{name}*: Error\n"
            
    return data_summary, raw_text

def hunt_for_economic_data():
    """Scrapes news headlines to find the latest Economic Data for Group B"""
    data_summary = "📰 **ECONOMIC NEWS FEED**\n"
    raw_text = "NEWS DATA:\n" # For AI
    
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
            
            # Format for Telegram (Hyperlinked Title)
            data_summary += f"🔹 <a href='{link}'>{indicator_name}</a>\n   └ <i>{title}</i>\n"
            raw_text += f"{indicator_name}: {title}\n"
        else:
            data_summary += f"🔸 {indicator_name}: No recent news.\n"
            
    return data_summary, raw_text

def generate_grand_strategy(full_data_text):
    """Sends the massive 25-point dataset to Gemini 3 Pro"""
    if not GEMINI_KEY: return "⚠️ AI Key Missing"
    
    models = ['gemini-3-pro-preview', 'gemini-2.5-flash']
    
    prompt = (
        "Act as a Chief Economist for a Hedge Fund. "
        "I have gathered 25 critical macro indicators for the Indian Market below.\n"
        "Some are live prices, some are news headlines.\n\n"
        f"{full_data_text}\n\n"
        "TASK:\n"
        "1. Synthesize this data into a 'Market Regime' (e.g., Inflationary Growth, Risk-Off).\n"
        "2. Identify the top 3 Positive Signals and top 3 Negative Risks.\n"
        "3. Provide a Sector Allocation Strategy.\n\n"
        "OUTPUT FORMAT:\n"
        "🌍 **MACRO REGIME:** [Name]\n"
        "✅ **TAILWINDS:** [List Top 3]\n"
        "⚠️ **HEADWINDS:** [List Top 3]\n"
        "🏗️ **SECTOR STRATEGY:** [Sectors to Buy/Avoid]"
    )
    
    for m in models:
        try:
            model = genai.GenerativeModel(m)
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"❌ Error with {m}: {e}") # Print error to GitHub logs
            continue
            
    return "⚠️ AI Analysis Failed (Check GitHub Logs for details)"

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID: return
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID, 
        "text": msg, 
        "parse_mode": "HTML", # Changed to HTML to support news links
        "disable_web_page_preview": True
    }
    requests.post(url, json=payload)

def run_omni_scanner():
    print(f"🚀 Starting Omni-Scanner... [{datetime.now().strftime('%H:%M')}]")
    
    # 1. Get Live Data & Send Immediately
    telegram_live, ai_live = get_live_market_data()
    send_telegram(telegram_live)
    print("✅ Live Data Sent.")
    
    # 2. Get News Data & Send Immediately
    telegram_news, ai_news = hunt_for_economic_data()
    send_telegram(telegram_news)
    print("✅ News Data Sent.")
    
    # 3. Analyze & Send Report
    print("🧠 Analyzing Matrix...")
    full_dossier = ai_live + "\n" + ai_news
    analysis = generate_grand_strategy(full_dossier)
    
    final_msg = (
        f"🏛️ **THE OMNI-SCANNER REPORT**\n"
        f"<i>{datetime.now().strftime('%d %b %Y')}</i>\n\n"
        f"{analysis}\n\n"
        f"🔍 <i>Based on 25-Point Macro Matrix</i>"
    )
    
    send_telegram(final_msg)
    print("✅ AI Report Sent.")

if __name__ == "__main__":
    run_omni_scanner()
