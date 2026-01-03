import os
import requests
import urllib.parse
import google.generativeai as genai
from GoogleNews import GoogleNews
from datetime import datetime

# --- CONFIGURATION ---
TARGETS = [
    "Adani", "Tata", "Reliance", "Vedanta", "Zomato", "Paytm", 
    "Merger", "Acquisition", "Stake Sale", "IPO"
]

# RUMOR KEYWORDS (Triggers)
RUMOR_KEYWORDS = [
    "sources say", "reportedly", "in talks", "likely to", 
    "considering", "mulling", "exclusive", "potential deal",
    "unconfirmed", "buzz", "spotted", "leak"
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

def clean_google_link(link):
    """
    Attempts to fix the broken relative links.
    Google often gives './articles/...' which needs the base URL.
    """
    if not link: return "https://news.google.com"
    
    # Case 1: Relative path starting with ./
    if link.startswith("./"):
        return f"https://news.google.com{link[1:]}"
    
    # Case 2: Just 'articles/...' or 'rss/articles/...'
    if link.startswith("articles/") or link.startswith("rss/"):
        return f"https://news.google.com/{link}"
        
    return link

def get_ai_opinion(headline):
    """Asks Gemini 3 Pro: Is this gossip worth trading?"""
    if not GEMINI_KEY: return "AI Unavailable"
    
    # 1. USE YOUR VERIFIED PREMIUM MODELS
    models_to_try = ['gemini-3-pro-preview', 'gemini-2.5-flash']
    
    prompt = (
        f"Analyze this rumor headline: '{headline}'\n"
        "1. CREDIBILITY: [High/Low/Speculation]\n"
        "2. IF TRUE, IMPACT: [Bullish/Bearish]\n"
        "Keep it very short (max 2 sentences)."
    )
    
    for m in models_to_try:
        try:
            model = genai.GenerativeModel(m)
            response = model.generate_content(prompt)
            return response.text.strip()
        except: continue
            
    return "⚠️ AI Analysis Failed"

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML", "disable_web_page_preview": True}
    requests.post(url, json=payload)

def hunt_for_gossip():
    print(f"🕵️‍♂️ Gossip Hunter Active... [{datetime.now().strftime('%H:%M')}]")
    
    # Look back 4 hours
    googlenews = GoogleNews(period='4h') 
    googlenews.set_lang('en')
    googlenews.set_encode('utf-8')
    
    seen_links = set()
    
    for target in TARGETS:
        search_query = f"{target} India"
        googlenews.search(search_query)
        results = googlenews.result()
        googlenews.clear()
        
        for item in results:
            title = item.get('title', '')
            raw_link = item.get('link', '')
            
            # --- FIX 1: BETTER CLEANER ---
            link = clean_google_link(raw_link)
            
            # --- FIX 2: FALLBACK SEARCH LINK ---
            # This generates a Google Search URL for the title. It 100% works.
            safe_search_url = f"https://www.google.com/search?q={urllib.parse.quote(title)}"
            
            # FILTER: Must contain a Rumor Keyword
            is_gossip = any(k.lower() in title.lower() for k in RUMOR_KEYWORDS)
            
            if is_gossip and link not in seen_links:
                seen_links.add(link)
                
                print(f"👀 Spot: {title}")
                
                ai_take = get_ai_opinion(title)
                
                msg = (
                    f"🤫 <b>GOSSIP DETECTED</b> | {target}\n\n"
                    f"🗣️ <i>{title}</i>\n\n"
                    f"🔮 <b>AI READ:</b>\n<pre>{ai_take}</pre>\n\n"
                    f"🔗 <a href='{link}'>Direct Link</a> | <a href='{safe_search_url}'>🔎 Google Search</a>"
                )
                
                send_telegram(msg)

if __name__ == "__main__":
    hunt_for_gossip()
