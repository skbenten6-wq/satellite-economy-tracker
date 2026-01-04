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
            model = genai.Generative
