import os
import time
import json
import requests
import urllib.parse
import yfinance as yf
import google.generativeai as genai
from GoogleNews import GoogleNews
from datetime import datetime
from market_memory import update_global_trend # Must exist in repo

# --- STANDARD SETUP ---
LIVE_INDICATORS = {
    "1. USD/INR": "INR=X", "2. US 10Y Yield": "^TNX", "5. Dollar Index": "DX-Y.NYB",
    "16. India VIX": "^INDIAVIX", "17. Nifty 50": "^NSEI", "22. Copper": "HG=F",
    "15. Crude Oil": "CL=F", "Gold": "GC=F"
}
DATA_HUNT_QUERIES = [
    "3. US Fed Funds Rate current", "4. FII DII activity yesterday India",
    "6. India GST collections latest month", "7. India Auto Sales numbers monthly",
    "8. India IIP data latest", "9. India Core Sector growth latest",
    "10. India Power consumption demand latest", "11. India Bank Credit growth rate",
    "12. India 10-Year G-Sec yield current", "13. Indian Railways freight loading data",
    "14. IMD Monsoon forecast India latest", "15. Baltic Dry Index current",
    "17. Nifty 50 PE ratio current", "18. India Mutual Fund SIP inflows monthly",
    "19. India Fiscal Deficit latest", "20. India Current Account Deficit CAD",
    "21. India Forex Reserves latest", "23. US Non-Farm Payrolls data",
    "24. Nifty 50 EPS growth earnings", "25. RBI Capacity Utilization OBICUS"
]

BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

if GEMINI_KEY:
    try: genai.configure(api_key=GEMINI_KEY)
    except: pass

# --- FUNCTIONS ---
def get_live_market_data():
    data_summary = "📊 <b>LIVE MARKET DASHBOARD</b>\n\n"
    raw_text = "LIVE DATA:\n"
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
            else: data_summary += f"⚪ <b>{name}</b>: N/A\n"
        except: data_summary += f"⚪ <b>{name}</b>: Error\n"
    return data_summary, raw_text

def hunt_for_economic_data():
    data_summary = "📰 <b>ECONOMIC NEWS FEED</b>\n\n"
    raw_text = "\n--- NEWS DATA ---\n"
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
            safe_query = urllib.parse.quote(title)
            search_link = f"https://www.google.com/search?q={safe_query}"
            data_summary += f"🔹 <b>{indicator_name}</b>\n└ <a href='{link}'>{title}</a>\n   🔎 <a href='{search_link}'>Google Search</a>\n\n"
            raw_text += f"{indicator_name}: {title}\n"
        else:
            data_summary += f"🔸 {indicator_name}: No recent news.\n"
            raw_text += f"{indicator_name}: No recent news\n"
    return data_summary, raw_text

def generate_grand_strategy(full_data_text):
    if not GEMINI_KEY: return False, "⚠️ AI Key Missing"
    models = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-flash-latest']
    
    # ASK FOR JSON OUTPUT
    prompt = (
        "Analyze these 25 macro indicators for India:\n"
        f"{full_data_text}\n\n"
        "STEP 1: Determine the overall market trend (BULLISH, BEARISH, or NEUTRAL).\n"
        "STEP 2: Write a strategy report.\n\n"
        "OUTPUT FORMAT (Strict JSON):\n"
        "{\n"
        '  "trend": "BULLISH",\n'
        '  "report": "🌍 **MACRO REGIME:** ... (Full report here)"\n'
        "}"
    )
    
    for m in models:
        for attempt in range(2):
            try:
                model = genai.GenerativeModel(m)
                response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
                data = json.loads(response.text)
                return True, data
            except Exception as e:
                time.sleep(10)
                continue
    return False, {"report": "AI Failed", "trend": "NEUTRAL"}

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML", "disable_web_page_preview": True}
    requests.post(url, json=payload)

# --- SAVE TO GITHUB (THE MEMORY FIX) ---
def commit_memory_to_github():
    """Forces the updated memory file back to the repo"""
    try:
        os.system('git config --global user.email "bot@github.com"')
        os.system('git config --global user.name "Macro Bot"')
        os.system('git add market_memory.json')
        os.system('git commit -m "🧠 Update Market Memory [Skip CI]"')
        os.system('git push')
        print("✅ Memory Saved to GitHub.")
    except Exception as e:
        print(f"⚠️ Memory Save Failed: {e}")

def run_omni_scanner():
    print(f"🚀 Starting Omni-Scanner... [{datetime.now().strftime('%H:%M')}]")
    
    # 1. Gather Data
    t_live, r_live = get_live_market_data()
    send_telegram(t_live)
    t_news, r_news = hunt_for_economic_data()
    send_telegram(t_news)
    
    # 2. Analyze
    full_dossier = r_live + r_news
    success, result = generate_grand_strategy(full_dossier)
    
    # 3. Update Memory & Save
    if success:
        update_global_trend(result["trend"])
        commit_memory_to_github() # <--- NEW STEP
        
        final_msg = (
            f"🏛️ <b>THE OMNI-SCANNER REPORT</b>\n"
            f"<i>{datetime.now().strftime('%d %b %Y')}</i>\n\n"
            f"{result['report']}\n\n"
            f"🧠 <b>Brain Updated:</b> {result['trend']}"
        )
        send_telegram(final_msg)
    else:
        send_telegram(f"❌ Analysis Failed. Raw Data:\n<pre>{full_dossier}</pre>")

if __name__ == "__main__":
    run_omni_scanner()
