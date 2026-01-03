import os
import requests
import google.generativeai as genai
from GoogleNews import GoogleNews
from datetime import datetime

# --- CONFIGURATION ---
# Targets: We look for rumors in these specific sectors/companies
TARGETS = [
    "Adani", "Tata", "Reliance", "Vedanta", "Zomato", "Paytm", 
    "Merger", "Acquisition", "Stake Sale", "IPO"
]

# The "Gossip" Dictionary
# We only care if the news contains these specific speculative words
RUMOR_KEYWORDS = [
    "sources say", "reportedly", "in talks", "likely to", 
    "considering", "mulling", "exclusive", "potential deal",
    "unconfirmed", "buzz"
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

def get_ai_opinion(headline):
    """Asks Gemini: Is this a juicy rumor or just noise?"""
    if not GEMINI_KEY: return "AI Unavailable"
    
    # We use the fast model for gossips
    models = ['gemini-1.5-flash', 'gemini-pro']
    
    prompt = (
        f"Analyze this rumor headline: '{headline}'\n"
        "1. CREDIBILITY: [High/Low/Speculation]\n"
        "2. IF TRUE, IMPACT: [Bullish/Bearish]\n"
        "Keep it very short."
    )
    
    for m in models:
        try:
            model = genai.GenerativeModel(m)
            response = model.generate_content(prompt)
            return response.text.strip()
        except: continue
    return "AI Analysis Failed"

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML", "disable_web_page_preview": True}
    requests.post(url, json=payload)

def hunt_for_gossip():
    print(f"🕵️‍♂️ Gossip Hunter Active... [{datetime.now().strftime('%H:%M')}]")
    
    googlenews = GoogleNews(period='4h') # Look back only 4 hours
    googlenews.set_lang('en')
    googlenews.set_encode('utf-8')
    
    seen_links = set()
    
    # search for combined queries like "Adani sources say"
    for target in TARGETS:
        # Construct a search query that forces rumor keywords
        # Example: "Tata sources say" OR "Tata reportedly"
        search_query = f"{target} India"
        googlenews.search(search_query)
        results = googlenews.result()
        googlenews.clear()
        
        for item in results:
            title = item.get('title', '')
            link = item.get('link', '')
            
            # 1. FILTER: Must contain a Rumor Keyword
            is_gossip = any(k.lower() in title.lower() for k in RUMOR_KEYWORDS)
            
            if is_gossip and link not in seen_links:
                seen_links.add(link)
                
                print(f"👀 Spot: {title}")
                
                # 2. ANALYZE: Ask AI how spicy this is
                ai_take = get_ai_opinion(title)
                
                msg = (
                    f"🤫 <b>GOSSIP DETECTED</b> | {target}\n\n"
                    f"🗣️ <i>{title}</i>\n\n"
                    f"🔮 <b>AI READ:</b>\n<pre>{ai_take}</pre>\n\n"
                    f"🔗 <a href='{link}'>Source</a>"
                )
                
                send_telegram(msg)

if __name__ == "__main__":
    hunt_for_gossip()
