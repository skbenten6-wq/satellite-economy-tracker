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

# GROUP A: LIVE TICKERS (We get these instantly from Yahoo Finance)
LIVE_INDICATORS = {
    "1. USD/INR":       "INR=X",
    "2. US 10Y Yield":  "^TNX",
    "5. Dollar Index":  "DX-Y.NYB",
    "16. India VIX":    "^INDIAVIX",
    "17. Nifty 50":     "^NSEI",     # For Context
    "22. Copper":       "HG=F",
    "15. Crude Oil":    "CL=F",
    "Gold":             "GC=F"       # Added for correlation
}

# GROUP B: DATA HUNT (We search Google News for these values)
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
    data_summary = "--- LIVE MARKET DATA ---\n"
    print("📊 Fetching Live Tickers...")
    
    for name, ticker in LIVE_INDICATORS.items():
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="5d")
            if not hist.empty:
                price = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2]
                change = ((price - prev) / prev) * 100
                data_summary += f"{name}: {price:.2f} ({change:+.2f}%)\n"
        except:
            data_summary += f"{name}: N/A\n"
            
    return data_summary

def hunt_for_economic_data():
    """Scrapes news headlines to find the latest Economic Data for Group B"""
    data_summary = "\n--- ECONOMIC DATA HUNT ---\n"
    print("🕵️‍♂️ Hunting for Economic Reports...")
    
    googlenews = GoogleNews(period='7d') # Look for fresh data
    
    for query in DATA_HUNT_QUERIES:
        googlenews.clear()
        googlenews.search(query)
        results = googlenews.result()
        
        # We take the top 1 most relevant headline for each indicator
        if results:
            top_result = results[0]
            title = top_result['title']
            # data_summary += f"{query.split(' ')[1]} Data: {title}\n"
            # Just keeping the query key for context
            indicator_name = query.split(' ', 1)[1] 
            data_summary += f"Query '{indicator_name}': {title}\n"
        else:
            data_summary += f"{query}: No recent news found.\n"
            
    return data_summary

def generate_grand_strategy(full_data_text):
    """Sends the massive 25-point dataset to Gemini 3 Pro"""
    if not GEMINI_KEY: return "AI Unavailable"
    
    # Priority Order for Models
    models = ['gemini-3-pro-preview', 'gemini-2.5-flash']
    
    prompt = (
        "Act as a Chief Economist for a Hedge Fund. "
        "I have gathered 25 critical macro indicators for the Indian Market below. "
        "Some are live prices, some are news headlines containing the data.\n\n"
        f"{full_data_text}\n\n"
        "TASK:\n"
        "1. Synthesize this data into a 'Market Regime' (e.g., Inflationary Growth, Stagflation, Risk-On, Risk-Off).\n"
        "2. Identify the top 3 strongest positive signals and top 3 negative risks.\n"
        "3. Provide a clear Sector Allocation Strategy (e.g., Overweight Banking, Underweight IT).\n\n"
        "OUTPUT FORMAT:\n"
        "🌍 **MACRO REGIME:** [Name]\n"
        "✅ **TAILWINDS:** [List Top 3]\n"
        "⚠️ **HEADWINDS:** [List Top 3]\n"
        "🏗️ **SECTOR STRATEGY:** [Specific Sectors to Buy/Avoid]"
    )
    
    for m in models:
        try:
            model = genai.GenerativeModel(m)
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            continue
    return "⚠️ AI Analysis Failed"

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID: return
    
    # Telegram has a char limit, so we might need to split massive reports
    # But usually, the summary fits.
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def run_omni_scanner():
    print(f"🚀 Starting Omni-Scanner... [{datetime.now().strftime('%H:%M')}]")
    
    # 1. Get Live Data
    live_data = get_live_market_data()
    
    # 2. Get News Data (This takes time, so be patient)
    news_data = hunt_for_economic_data()
    
    # 3. Combine
    full_dossier = live_data + news_data
    
    # 4. Analyze
    print("🧠 Analyzing Matrix...")
    analysis = generate_grand_strategy(full_dossier)
    
    # 5. Report
    final_msg = (
        f"🏛️ **THE OMNI-SCANNER REPORT**\n"
        f"_{datetime.now().strftime('%d %b %Y')}_\n\n"
        f"{analysis}\n\n"
        f"🔍 *Based on 25-Point Macro Matrix*"
    )
    
    send_telegram(final_msg)
    print("✅ Report Sent.")

if __name__ == "__main__":
    run_omni_scanner()
