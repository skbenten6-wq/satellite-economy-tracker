import os
import requests
import json
import yfinance as yf
import pandas_ta as ta
import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from watchlist_manager import load_watchlist, add_to_dynamic, remove_from_dynamic
from paper_trader import get_portfolio_status  # IMPORTING THE LEDGER

# --- CONFIGURATION ---
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

# GITHUB REMOTE CONTROL KEYS
GH_TOKEN = os.environ.get("GH_PAT")
REPO_OWNER = os.environ.get("REPO_OWNER")
REPO_NAME = os.environ.get("REPO_NAME")

if GEMINI_KEY:
    try:
        genai.configure(api_key=GEMINI_KEY)
    except: pass

# --- HELPER: TRIGGER GITHUB WORKFLOW ---
def trigger_github_workflow(workflow_file):
    """Sends a signal to GitHub to run a specific bot immediately"""
    if not GH_TOKEN or not REPO_OWNER or not REPO_NAME:
        return "⚠️ Error: Missing GitHub Keys (GH_PAT, REPO_OWNER, REPO_NAME)"

    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows/{workflow_file}/dispatches"
    headers = {
        "Authorization": f"token {GH_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {"ref": "main"} # Target the main branch

    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 204:
            return f"🚀 **SUCCESS:** Triggered `{workflow_file}`"
        else:
            return f"❌ **FAILED:** GitHub said {response.status_code} - {response.text}"
    except Exception as e:
        return f"⚠️ Connection Error: {str(e)}"

# --- HELPER: DIAGNOSTIC SCAN ---
def run_full_scan(ticker):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="6mo")
        if df.empty: return f"❌ No data for {ticker}"
        
        rsi = ta.rsi(df['Close'], length=14).iloc[-1]
        ema_50 = ta.ema(df['Close'], length=50).iloc[-1]
        price = df['Close'].iloc[-1]
        
        signal = "NEUTRAL"
        if rsi < 30: signal = "OVERSOLD (Buy Dip)"
        elif rsi > 70: signal = "OVERBOUGHT (Caution)"
        elif price > ema_50: signal = "BULLISH TREND"
        elif price < ema_50: signal = "BEARISH TREND"
        
        ai_msg = "AI Silent"
        if GEMINI_KEY:
            model = genai.GenerativeModel('gemini-2.5-flash')
            prompt = (f"Analyze {ticker}: Price {price:.2f}, RSI {rsi:.2f}, EMA50 {ema_50:.2f}. "
                      f"Signal: {signal}. 1-sentence verdict.")
            try:
                response = model.generate_content(prompt)
                ai_msg = response.text.strip()
            except: pass

        return (
            f"🔍 **DIAGNOSTIC: {ticker}**\n"
            f"💰 Price: {price:.2f}\n"
            f"📊 Signal: {signal}\n"
            f"📈 RSI: {rsi:.2f}\n"
            f"🤖 **AI:** {ai_msg}"
        )
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

# --- COMMAND HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🤖 **COMMAND CENTER V3**\n\n"
        "💼 **TRADING DESK:**\n"
        "/portfolio - 💰 View Ghost Ledger\n"
        "/check <STOCK> - 🔍 Instant Analysis\n\n"
        "🎮 **REMOTE CONTROLS:**\n"
        "/run_macro - 🏛️ Run Omni-Scanner\n"
        "/run_satellite - 🛰️ Run Satellite Bot\n"
        "/run_sniper - 🎯 Run Technical Sniper\n"
        "/run_gossip - 🕵️‍♂️ Run Gossip Hunter\n\n"
        "📝 **WATCHLIST:**\n"
        "/status - View List\n"
        "/add <STOCK> - Add Stock\n"
        "/del <STOCK> - Remove Stock"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

# --- PAPER TRADING HANDLER ---
async def cmd_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    report = get_portfolio_status()
    await update.message.reply_text(report, parse_mode="Markdown")

# --- REMOTE CONTROL HANDLERS ---
async def cmd_run_macro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Triggering **Omni-Scanner**...", parse_mode="Markdown")
    res = trigger_github_workflow("macro_scan.yml")
    await update.message.reply_text(res, parse_mode="Markdown")

async def cmd_run_satellite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Triggering **Satellite Scan**...", parse_mode="Markdown")
    res = trigger_github_workflow("daily_scan.yml")
    await update.message.reply_text(res, parse_mode="Markdown")

async def cmd_run_sniper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Triggering **Sniper Bot**...", parse_mode="Markdown")
    res = trigger_github_workflow("sniper_scan.yml")
    await update.message.reply_text(res, parse_mode="Markdown")

async def cmd_run_gossip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Triggering **Gossip Hunter**...", parse_mode="Markdown")
    res = trigger_github_workflow("gossip_scan.yml")
    await update.message.reply_text(res, parse_mode="Markdown")

# --- WATCHLIST HANDLERS ---
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dynamic = []
    from watchlist_manager import STATIC_WATCHLIST, WATCHLIST_FILE
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE) as f: dynamic = json.load(f)
    msg = f"📋 **WATCHLIST**\n\n🔒 **Static:** {', '.join([s.replace('.NS','') for s in STATIC_WATCHLIST])}\n🌊 **Dynamic:** {', '.join([d.replace('.NS','') for d in dynamic])}"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def add_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await update.message.reply_text("Use: `/add TATASTEEL`", parse_mode="Markdown")
    if add_to_dynamic(context.args[0]): await update.message.reply_text(f"✅ Added **{context.args[0]}**")
    else: await update.message.reply_text(f"⚠️ **{context.args[0]}** exists.")

async def del_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await update.message.reply_text("Use: `/del TATASTEEL`", parse_mode="Markdown")
    if remove_from_dynamic(context.args[0]): await update.message.reply_text(f"🗑️ Removed **{context.args[0]}**")
    else: await update.message.reply_text(f"⚠️ **{context.args[0]}** not found.")

async def check_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await update.message.reply_text("Use: `/check TATASTEEL`", parse_mode="Markdown")
    ticker = context.args[0].upper()
    if not ticker.endswith(".NS"): ticker += ".NS"
    await update.message.reply_text(f"⏳ Scanning **{ticker}**...", parse_mode="Markdown")
    await update.message.reply_text(run_full_scan(ticker), parse_mode="Markdown")

# --- MAIN ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    
    # Paper Trading
    app.add_handler(CommandHandler("portfolio", cmd_portfolio))
    
    # Remote Controls
    app.add_handler(CommandHandler("run_macro", cmd_run_macro))
    app.add_handler(CommandHandler("run_satellite", cmd_run_satellite))
    app.add_handler(CommandHandler("run_sniper", cmd_run_sniper))
    app.add_handler(CommandHandler("run_gossip", cmd_run_gossip))
    
    # Tools
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("add", add_stock))
    app.add_handler(CommandHandler("del", del_stock))
    app.add_handler(CommandHandler("check", check_stock))
    
    print("🤖 Commander V3 Active...")
    app.run_polling()
