import json
import os

WATCHLIST_FILE = "dynamic_watchlist.json"
STATIC_WATCHLIST = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", 
    "ICICIBANK.NS", "SBIN.NS", "TATAMOTORS.NS", "ITC.NS",
    "ADANIENT.NS", "COALINDIA.NS", "ZOMATO.NS", "PAYTM.NS"
]

def load_watchlist():
    """Combines Static + Dynamic Watchlist"""
    dynamic = []
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, "r") as f:
                dynamic = json.load(f)
        except: pass
    
    # Return unique items
    return list(set(STATIC_WATCHLIST + dynamic))

def add_to_dynamic(ticker):
    """Adds a new stock from other bots (e.g. Gossip Bot found something)"""
    dynamic = []
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, "r") as f:
            dynamic = json.load(f)
    
    ticker = ticker.upper()
    if not ticker.endswith(".NS"): ticker += ".NS"
    
    if ticker not in dynamic and ticker not in STATIC_WATCHLIST:
        dynamic.append(ticker)
        with open(WATCHLIST_FILE, "w") as f:
            json.dump(dynamic, f)
        return True
    return False

def remove_from_dynamic(ticker):
    """Removes a stock from the dynamic list"""
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, "r") as f:
            dynamic = json.load(f)
        
        ticker = ticker.upper()
        if not ticker.endswith(".NS"): ticker += ".NS"
        
        if ticker in dynamic:
            dynamic.remove(ticker)
            with open(WATCHLIST_FILE, "w") as f:
                json.dump(dynamic, f)
            return True
    return False
