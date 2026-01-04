import json
import os
import datetime

# CONFIGURATION
PORTFOLIO_FILE = "portfolio.json"
INITIAL_CAPITAL = 1000000  # ₹10 Lakhs starting cash
TRADE_SIZE = 50000         # Put ₹50k into each trade

def load_portfolio():
    """Loads the portfolio or creates a new one if it doesn't exist"""
    if not os.path.exists(PORTFOLIO_FILE):
        return {
            "balance": INITIAL_CAPITAL,
            "holdings": {},  # Stores current stocks
            "history": []    # Stores closed trades
        }
    try:
        with open(PORTFOLIO_FILE, "r") as f:
            return json.load(f)
    except:
        return {"balance": INITIAL_CAPITAL, "holdings": {}, "history": []}

def save_portfolio(data):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(data, f, indent=4)

def execute_buy(ticker, price, date):
    """Buys a stock if we have enough cash"""
    pf = load_portfolio()
    
    # Don't buy if we already own it (Simple Rule)
    if ticker in pf["holdings"]:
        return False, "Already Holding"

    if pf["balance"] < TRADE_SIZE:
        return False, "Insufficient Funds"

    qty = int(TRADE_SIZE / price)
    if qty == 0: return False, "Price too high for trade size"

    cost = qty * price
    pf["balance"] -= cost
    
    pf["holdings"][ticker] = {
        "buy_price": price,
        "qty": qty,
        "buy_date": date
    }
    
    save_portfolio(pf)
    return True, f"Bought {qty} qty at {price:.2f}"

def execute_sell(ticker, price, date):
    """Sells a stock and records profit/loss"""
    pf = load_portfolio()
    
    if ticker not in pf["holdings"]:
        return False, "Not Holding"

    stock = pf["holdings"][ticker]
    qty = stock["qty"]
    buy_price = stock["buy_price"]
    
    revenue = qty * price
    profit = revenue - (qty * buy_price)
    
    # Remove from holdings
    del pf["holdings"][ticker]
    
    # Add cash back
    pf["balance"] += revenue
    
    # Record History
    trade_record = {
        "ticker": ticker,
        "buy_price": buy_price,
        "sell_price": price,
        "qty": qty,
        "profit": profit,
        "buy_date": stock["buy_date"],
        "sell_date": date
    }
    pf["history"].append(trade_record)
    
    save_portfolio(pf)
    return True, f"Sold for Profit: ₹{profit:.2f}"

def get_portfolio_status():
    """Returns a readable summary of your account"""
    pf = load_portfolio()
    balance = pf["balance"]
    invested = 0
    current_holdings = ""
    
    for t, data in pf["holdings"].items():
        invested += data["qty"] * data["buy_price"]
        current_holdings += f"• {t}: {data['qty']} qty @ {data['buy_price']:.1f}\n"
    
    if not current_holdings: current_holdings = "No active trades."
    
    total_trades = len(pf["history"])
    total_pnl = sum([t["profit"] for t in pf["history"]])
    
    return (
        f"💼 **GHOST LEDGER**\n"
        f"💰 Cash: ₹{balance:,.2f}\n"
        f"📉 Invested: ₹{invested:,.2f}\n"
        f"📜 History: {total_trades} Trades (P&L: ₹{total_pnl:,.2f})\n\n"
        f"🔓 **Open Positions:**\n{current_holdings}"
    )
