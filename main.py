import os
import json
import ee
import requests
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from GoogleNews import GoogleNews
from fpdf import FPDF
import yfinance as yf

# ==========================================
# 1. CONFIGURATION & AUTH
# ==========================================
PROJECT_ID = "satellite-tracker-2026"
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

try:
    if os.environ.get("EE_KEY"):
        service_account_info = json.loads(os.environ["EE_KEY"])
        credentials = Credentials.from_service_account_info(
            service_account_info, 
            scopes=['https://www.googleapis.com/auth/earthengine']
        )
        ee.Initialize(credentials=credentials, project=PROJECT_ID)
    else:
        ee.Initialize(project=PROJECT_ID)
    print("✅ [SYSTEM] Satellite Connection Established")
except Exception as e:
    print(f"❌ [CRITICAL] Auth Failed: {e}")
    pass

googlenews = GoogleNews(period='2d') 
googlenews.set_lang('en')
googlenews.set_encode('utf-8')

# ==========================================
# 2. TARGET LIST (YOUR ORIGINAL LIST)
# ==========================================
targets = {
    "1. COAL INDIA (Gevra Mine)": { 
        "roi": [82.5600, 22.3100, 82.6000, 22.3500], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000}, 
        "query": "Coal India production", 
        "desc": "Pit Expansion",
        "ticker": "COALINDIA.NS" 
    },
    "2. NMDC (Bailadila Iron)": { 
        "roi": [81.2000, 18.6600, 81.2400, 18.7000], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000}, 
        "query": "NMDC iron ore prices", 
        "desc": "Red Ore Piles",
        "ticker": "NMDC.NS" 
    },
    "3. RELIANCE (Oil Storage)": { 
        "roi": [69.8300, 22.3300, 69.9100, 22.3800], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000}, 
        "query": "Crude oil inventory India", 
        "desc": "Tank Farm Levels",
        "ticker": "RELIANCE.NS" 
    },
    "4. TATA STEEL (Jamshedpur)": { 
        "roi": [86.1950, 22.7950, 86.2050, 22.8050], 
        "vis": {'bands': ['B12', 'B11', 'B4'], 'min': 0, 'max': 4000}, 
        "query": "Tata Steel India production", 
        "desc": "Blast Furnace Heat",
        "ticker": "TATASTEEL.NS" 
    },
    "5. HINDALCO (Copper Dahej)": { 
        "roi": [72.5300, 21.6900, 72.5600, 21.7200], 
        "vis": {'bands': ['B12', 'B11', 'B4'], 'min': 0, 'max': 4000}, 
        "query": "Copper prices India demand", 
        "desc": "Smelter Activity",
        "ticker": "HINDALCO.NS" 
    },
    "6. ULTRATECH (Aditya Cement)": { 
        "roi": [74.6000, 24.7800, 74.6400, 24.8200], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000}, 
        "query": "Cement demand India", 
        "desc": "Grey Dust & Quarry",
        "ticker": "ULTRATECH.NS" 
    },
    "7. ADANI PORTS (Mundra)": { 
        "roi": [69.6900, 22.7300, 69.7300, 22.7600], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000}, 
        "query": "Adani Ports cargo volume", 
        "desc": "Ships at Dock",
        "ticker": "ADANIPORTS.NS" 
    },
    "8. CONCOR (Delhi Depot)": { 
        "roi": [77.2880, 28.5200, 77.2980, 28.5300], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000}, 
        "query": "Container Corp volume", 
        "desc": "Container Density",
        "ticker": "CONCOR.NS" 
    },
    "9. MARUTI (Manesar Yard)": { 
        "roi": [76.9300, 28.3500, 76.9400, 28.3600], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000}, 
        "query": "Maruti Suzuki sales", 
        "desc": "Car Inventory",
        "ticker": "MARUTI.NS" 
    },
    "10. JEWAR AIRPORT (Const.)": { 
        "roi": [77.6000, 28.1600, 77.6400, 28.1900], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000}, 
        "query": "Jewar Airport status", 
        "desc": "Construction Progress",
        "ticker": "GMRINFRA.NS" 
    },
    "11. BHADLA SOLAR (Energy)": { 
        "roi": [71.9000, 27.5300, 71.9400, 27.5600], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000}, 
        "query": "India solar capacity", 
        "desc": "Panel Expansion",
        "ticker": None 
    },
    "12. BHAKRA DAM (Hydro)": { 
        "roi": [76.4100, 31.3900, 76.4500, 31.4200], 
        "vis": {'bands': ['B8', 'B4', 'B3'], 'min': 0, 'max': 3000}, 
        "query": "Monsoon rainfall India", 
        "desc": "Water Level",
        "ticker": None 
    }
}

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
def get_valuation_data(ticker):
    """Fetches live market data"""
    if not ticker: return {"price": "N/A", "pe": "N/A", "signal": "N/A"}
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="1mo")
        current_price = info.get('currentPrice', 0)
        if not current_price and not hist.empty: current_price = hist['Close'].iloc[-1]
        pe_ratio = info.get('trailingPE', 0)
        
        # Calculate 1-Month Return
        change_pct = 0
        if not hist.empty:
            start_price = hist['Close'].iloc[0]
            change_pct = ((current_price - start_price) / start_price) * 100
            
        signal = "NEUTRAL"
        if pe_ratio > 0:
            if pe_ratio < 15 and change_pct < 10: signal = "VALUE BUY"
            elif pe_ratio > 40: signal = "OVERVALUED"
            elif change_pct > 15: signal = "HEATED (PRICED IN)"
        
        return {"price": f"Rs {current_price:.1f}", "pe": f"{pe_ratio:.1f}x", "signal": signal}
    except: return {"price": "Error", "pe": "-", "signal": "Error"}

def get_satellite_data(coords, vis, filename):
    try:
        roi = ee.Geometry.Rectangle(coords)
        # Dynamic Date: Look back 45 days for better chance of clear image
        end_date = datetime.now()
        start_date = end_date - timedelta(days=45)
        
        col = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
               .filterBounds(roi)
               .filterDate(start_date, end_date)
               .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
               .sort('system:time_start', False))
        
        if col.size().getInfo() > 0:
            url = col.first().getThumbURL({
                'min': vis['min'], 'max': vis['max'], 'bands': vis['bands'], 
                'region': roi, 'format': 'jpg', 'dimensions': 600
            })
            r = requests.get(url)
            if r.status_code == 200:
                with open(filename, 'wb') as f:
                    f.write(r.content)
                return url, True
    except Exception as e:
        print(f"EE Error: {e}")
    return None, False

def get_market_news(query):
    try:
        googlenews.clear()
        googlenews.search(query)
        results = googlenews.result()
        news_data = []
        for item in results[:2]:
            title = item.get('title', '')
            link = item.get('link', '')
            date = item.get('date', 'Recent')
            
            if link.startswith("./"): link = f"https://news.google.com{link[1:]}"
            
            # CRITICAL FIX: Sanitize Title for PDF to prevent crashes
            clean_title = title.encode('latin-1', 'ignore').decode('latin-1')
            
            if "http" in link: 
                news_data.append({'title': clean_title, 'link': link, 'date': date})
                
        if not news_data:
            safe_link = f"https://www.google.com/search?q={urllib.parse.quote(query)}&tbm=nws"
            news_data.append({'title': "No fresh news. Click for Google Search.", 'link': safe_link, 'date': "N/A"})
        return news_data
    except:
        return [{'title': "News fetch failed.", 'link': "#", 'date': "Error"}]

# ==========================================
# 4. REPORT GENERATION
# ==========================================
print("🚀 [SYSTEM] Generating Financial Intelligence Report...")

pdf = FPDF()
pdf.set_auto_page_break(auto=True, margin=15)

for i, (name, data) in enumerate(targets.items()):
    print(f"   ...Analyzing: {name}")
    
    # 1. FETCH DATA
    img_filename = f"sector_{i}.jpg"
    img_url, has_image = get_satellite_data(data['roi'], data['vis'], img_filename)
    news_items = get_market_news(data['query'])
    val_data = get_valuation_data(data['ticker'])
    
    # 2. BUILD PDF PAGE
    pdf.add_page()
    
    # Title
    pdf.set_font("Arial", "B", 14)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 10, f"{name}", ln=True)
    
    # Valuation Bar
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, f"  Price: {val_data['price']}  |  P/E: {val_data['pe']}  |  Signal: {val_data['signal']}", ln=True, fill=True)
    pdf.ln(5)
    
    # News Links (Blue & Clickable)
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(0, 0, 255)
    for n in news_items:
        link_text = f"[{n['date']}] {n['title']}"
        pdf.write(5, link_text, n['link'])
        pdf.ln(7)
    
    pdf.ln(5)
    # Image
    if has_image:
        try:
            pdf.image(img_filename, x=10, w=190)
        except:
            pdf.cell(0, 10, "Image Error", ln=True)

# FINALIZE PDF
filename = "Financial_Intel_Report.pdf"
pdf.output(filename)
print("✅ Report Generated.")

# ==========================================
# 5. TELEGRAM DELIVERY
# ==========================================
if BOT_TOKEN and CHAT_ID:
    print("🚀 Sending to Telegram...")
    try:
        with open(filename, 'rb') as f:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
            payload = {"chat_id": CHAT_ID, "caption": "🛰️ **Alpha Satellite Dispatch**\nFull Strategic Scan attached."}
            files = {"document": f}
            resp = requests.post(url, data=payload, files=files)
            print(f"✅ Sent: {resp.status_code}")
    except Exception as e:
        print(f"❌ Telegram Error: {e}")
else:
    print("⚠️ Telegram Config Missing. PDF saved locally.")
