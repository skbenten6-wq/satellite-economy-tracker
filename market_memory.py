import json
import os

MEMORY_FILE = "market_memory.json"

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {"global_trend": "NEUTRAL", "stock_sentiment": {}}
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except:
        return {"global_trend": "NEUTRAL", "stock_sentiment": {}}

def update_global_trend(trend):
    """Macro Bot calls this (BULLISH/BEARISH/NEUTRAL)"""
    mem = load_memory()
    mem["global_trend"] = trend.upper()
    with open(MEMORY_FILE, "w") as f:
        json.dump(mem, f, indent=4)

def update_stock_sentiment(ticker, sentiment):
    """Satellite/News Bot calls this (POSITIVE/NEGATIVE)"""
    mem = load_memory()
    if not ticker.endswith(".NS"): ticker += ".NS"
    mem["stock_sentiment"][ticker] = sentiment.upper()
    with open(MEMORY_FILE, "w") as f:
        json.dump(mem, f, indent=4)

def get_confluence_score(ticker):
    """Calculates a 'Confidence Score' (0-100) for trading"""
    mem = load_memory()
    if not ticker.endswith(".NS"): ticker += ".NS"
    
    score = 50 # Start Neutral
    
    # 1. Global Trend Impact
    trend = mem.get("global_trend", "NEUTRAL")
    if trend == "BULLISH": score += 20
    elif trend == "BEARISH": score -= 20
    
    # 2. Specific Stock Sentiment (Satellite/News)
    stock_sent = mem.get("stock_sentiment", {}).get(ticker, "NEUTRAL")
    if stock_sent == "POSITIVE": score += 30
    elif stock_sent == "NEGATIVE": score -= 30
    
    return score
