import os
import requests
import yfinance as yf
import pandas_ta as ta
import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from watchlist_manager import load_watchlist, add_to_dynamic, remove_from_dynamic

# SECRETS
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

if GEMINI_KEY:
    try:
        genai.configure(api_key=GEMINI_KEY)
    except: pass

# --- HELPER: FULL DIAGNOSTIC SCAN ---
def run_full_scan(ticker):
    """Runs Sniper Technicals + AI Analysis for a single stock"""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="6mo")
        if df.empty: return f"❌ Could not fetch data for {ticker}"
        
        # 1. TECHNICALS
        rsi = ta.rsi(df['Close'], length=14).iloc[-1]
        ema_50 = ta.ema(df['Close'], length=50).iloc[-1]
        price = df['Close'].iloc[-1]
        
        signal = "NEUTRAL"
        if rsi < 30: signal = "OVERSOLD (Buy Dip)"
        elif rsi > 70: signal = "OVERBOUGHT (Caution)"
        elif price > ema_50: signal = "BULLISH TREND"
        elif price < ema_50: signal = "BEARISH TREND"
        
        # 2. AI OPINION
        ai_msg = "AI Unavailable"
        if GEMINI_KEY:
            model = genai.GenerativeModel('gemini-2.5-flash')
            prompt = (f"Analyze {ticker} based on: Price {price:.2f}, RSI {rsi:.2f}, EMA50 {ema_50:.2f}. "
                      f"Technical Signal: {signal}. "
                      "Give a 1-sentence trading verdict.")
            try:
                response = model.generate_content(prompt)
                ai_msg = response.text.strip()
            except: pass

        return (
            f"🔍 **DIAGNOSTIC: {ticker}**\n"
            f"💰 Price: {price:.2f}\n"
            f"📊 Signal: {signal}\n"
            f"📈 RSI: {rsi:.2f}\n"
            f"🤖 **AI Verdict:** {ai_msg}"
        )
    except Exception as e:
        return f"⚠️ Error checking {ticker}: {str(e)}"

# --- TELEGRAM COMMAND HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🤖 **COMMAND CENTER ONLINE**\n\n"
        "📜 `/status` - View Watchlists\n"
        "➕ `/add <SYMBOL>` - Add to Dynamic List\n"
        "➖ `/del <SYMBOL>` - Remove from Dynamic List\n"
        "🔍 `/check <SYMBOL>` - Instant Diagnostic\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    full_list = load_watchlist()
    from watchlist_manager import STATIC_WATCHLIST, WATCHLIST_FILE
    import json
    
    dynamic = []
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE) as f: dynamic = json.load(f)
        
    msg = (
        f"📋 **WATCHLIST STATUS**\n\n"
        f"🔒 **Static ({len(STATIC_WATCHLIST)}):**\n{', '.join([s.replace('.NS','') for s in STATIC_WATCHLIST])}\n\n"
        f"🌊 **Dynamic ({len(dynamic)}):**\n{', '.join([d.replace('.NS','') for d in dynamic])}"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def add_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Usage: `/add TATASTEEL`", parse_mode="Markdown")
        return
    ticker = context.args[0]
    if add_to_dynamic(ticker):
        await update.message.reply_text(f"✅ Added **{ticker}** to Dynamic Watchlist.", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"⚠️ **{ticker}** is already being watched.", parse_mode="Markdown")

async def del_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Usage: `/del TATASTEEL`", parse_mode="Markdown")
        return
    ticker = context.args[0]
    if remove_from_dynamic(ticker):
        await update.message.reply_text(f"🗑️ Removed **{ticker}** from Dynamic Watchlist.", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"⚠️ **{ticker}** was not in the dynamic list.", parse_mode="Markdown")

async def check_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Usage: `/check TATASTEEL`", parse_mode="Markdown")
        return
    
    ticker = context.args[0].upper()
    if not ticker.endswith(".NS"): ticker += ".NS"
    
    await update.message.reply_text(f"⏳ Scanning **{ticker}**...", parse_mode="Markdown")
    report = run_full_scan(ticker)
    await update.message.reply_text(report, parse_mode="Markdown")

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("add", add_stock))
    app.add_handler(CommandHandler("del", del_stock))
    app.add_handler(CommandHandler("check", check_stock))
    
    print("🤖 Telegram Commander Active...")
    app.run_polling()
