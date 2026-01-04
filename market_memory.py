import json
import os
import requests

MEMORY_FILE = "market_memory.json"

# You need to fill these in, or ensure they are set in your Environment Variables
# For simplicity, if the Env Vars exist (Commander has them), we use them.
REPO_OWNER = os.environ.get("REPO_OWNER") 
REPO_NAME = os.environ.get("REPO_NAME")

def load_memory():
    """Tries to fetch the latest Brain from GitHub Cloud first"""
    # 1. Try Cloud Fetch (Real-time)
    if REPO_OWNER and REPO_NAME:
        url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/market_memory.json"
        try:
            # We use a timeout so it doesn't hang if GitHub is slow
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return response.json()
        except:
            pass # If cloud fails, fall back to local file

    # 2. Local Fallback
    if not os.path.exists(MEMORY_FILE):
        return {"global_trend": "NEUTRAL", "stock_sentiment": {}}
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except:
        return {"global_trend": "NEUTRAL", "stock_sentiment": {}}

def update_global_trend(trend):
    """Macro Bot calls this (BULLISH/BEARISH/NEUTRAL)"""
    mem = load_memory() # Load latest
    mem["global_trend"] = trend.upper()
    with open(MEMORY_FILE, "w") as f:
        json.dump(mem, f, indent=4)

def update_stock_sentiment(ticker, sentiment):
    """Satellite/News Bot calls this"""
    mem = load_memory() # Load latest
    if not ticker.endswith(".NS"): ticker += ".NS"
    mem["stock_sentiment"][ticker] = sentiment.upper()
    with open(MEMORY_FILE, "w") as f:
        json.dump(mem, f, indent=4)

def get_confluence_score(ticker):
    mem = load_memory() # Load latest
    if not ticker.endswith(".NS"): ticker += ".NS"
    
    score = 50 
    
    trend = mem.get("global_trend", "NEUTRAL")
    if trend == "BULLISH": score += 20
    elif trend == "BEARISH": score -= 20
    
    stock_sent = mem.get("stock_sentiment", {}).get(ticker, "NEUTRAL")
    if stock_sent == "POSITIVE": score += 30
    elif stock_sent == "NEGATIVE": score -= 30
    
    return score
