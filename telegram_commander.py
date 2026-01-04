# ... inside imports ...
import random # Add this import at the top

async def cmd_intel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows what the AI Brain currently knows about the market"""
    
    # 1. FORCE FRESH FETCH FROM CLOUD
    mem = {}
    if REPO_OWNER and REPO_NAME:
        # We add a random number to the URL to bypass the cache
        rand_id = random.randint(1, 99999)
        url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/market_memory.json?t={rand_id}"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                mem = response.json()
        except: pass
    
    # 2. Fallback to local if cloud failed
    if not mem:
        mem = load_memory()
    
    trend = mem.get("global_trend", "NEUTRAL")
    sentiments = mem.get("stock_sentiment", {})
    
    trend_icon = "⚪"
    if trend == "BULLISH": trend_icon = "🟢"
    elif trend == "BEARISH": trend_icon = "🔴"
    
    msg = (
        f"🧠 **MARKET INTELLIGENCE**\n\n"
        f"🌍 **Global Regime:** {trend_icon} {trend}\n\n"
        f"📡 **Stock Sentiment:**\n"
    )
    
    if sentiments:
        for ticker, sentiment in sentiments.items():
            icon = "🟢" if sentiment == "POSITIVE" else "🔴"
            if sentiment == "NEUTRAL": icon = "⚪"
            msg += f"• {ticker}: {icon} {sentiment}\n"
    else:
        msg += "• No satellite data recorded yet.\n"
        
    await update.message.reply_text(msg, parse_mode="Markdown")
