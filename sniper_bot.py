# ... imports ...
from market_memory import get_confluence_score # IMPORT THIS

def scan_market():
    print(f"🎯 Sniper Scope Active... [{datetime.now().strftime('%H:%M')}]")
    watchlist = load_watchlist()
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    for ticker in watchlist:
        try:
            if not ticker.endswith(".NS"): ticker = f"{ticker}.NS"
            df = yf.download(ticker, period="6mo", interval="1d", progress=False)
            if df.empty: continue
            
            # Technicals
            df['RSI'] = ta.rsi(df['Close'], length=14)
            rsi = df['RSI'].iloc[-1].item()
            price = df['Close'].iloc[-1].item()
            
            # --- INTELLIGENCE CHECK ---
            score = get_confluence_score(ticker)
            
            # DYNAMIC RSI THRESHOLDS based on Intelligence
            buy_threshold = 30
            if score >= 70: buy_threshold = 40 # Be aggressive if news is good
            if score <= 30: buy_threshold = 20 # Be very careful if news is bad
            
            # 1. BUY LOGIC
            if rsi < buy_threshold:
                # FINAL FILTER: Don't buy if Score is terrible (e.g. < 20)
                if score < 20:
                    print(f"🚫 Skipped {ticker} (RSI {rsi}) due to Negative Sentiment (Score {score})")
                    continue
                    
                success, msg = execute_buy(ticker, price, today_str)
                if success:
                    send_telegram(
                        f"🟢 **SMART BUY: {ticker}**\n"
                        f"Price: {price:.2f}\n"
                        f"RSI: {rsi:.2f} (Limit: {buy_threshold})\n"
                        f"🧠 **Intel Score:** {score}/100"
                    )

            # 2. SELL LOGIC (RSI > 70)
            elif rsi > 70:
                success, msg = execute_sell(ticker, price, today_str)
                if success:
                    send_telegram(f"🔴 **SOLD: {ticker}**\nPrice: {price:.2f}\nProfit: {msg}")

        except Exception as e:
            continue
