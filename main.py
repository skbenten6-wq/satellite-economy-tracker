import os
import json
import ee
import base64
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

# --- SANITIZER FUNCTION (Fixes the Crash) ---
def clean_text(text):
    """Removes emojis and unsupported characters to prevent PDF crashes."""
    if not text: return ""
    # This magic line removes anything that isn't standard English/Latin
    return text.encode('latin-1', 'ignore').decode('latin-1')

try:
    if os.environ.get("EE_KEY"):
        key_data = base64.b64decode(os.environ.get("EE_KEY")).decode('utf-8')
        service_account_info = json.loads(key_data)
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
# 2. TARGET LIST (With Emojis - Will be stripped for PDF)
# ==========================================
targets = {
    "1. COAL INDIA (Gevra Mine)": { 
        "roi": [82.5600, 22.3100, 82.6000, 22.3500], 
        "vis": {'bands': ['B12', 'B11', 'B4'], 'min': 0, 'max': 4000, 'gamma': 1.3}, 
        "query": "Coal India production", 
        "ticker": "COALINDIA.NS",
        "location": "Korba District, Chhattisgarh (Asia's Largest Open Cast Mine)",
        "guide": "ANALYSIS (SWIR Band): The bright pink/brown patches are active mining cuts exposing fresh earth. Black pools are water/slurry."
    },
    "2. NMDC (Bailadila Iron)": { 
        "roi": [81.2000, 18.6600, 81.2400, 18.7000], 
        "vis": {'bands': ['B12', 'B11', 'B4'], 'min': 0, 'max': 4000, 'gamma': 1.3}, 
        "query": "NMDC iron ore prices", 
        "ticker": "NMDC.NS",
        "location": "Dantewada, Chhattisgarh (Iron Ore Range)",
        "guide": "ANALYSIS (SWIR Band): High-grade iron ore reflects a distinctive deep orange/red in this band. Look for expansion of red zones."
    },
    "3. RELIANCE (Oil Complex)": { 
        "roi": [69.8300, 22.3300, 69.9100, 22.3800], 
        "vis": {'bands': ['B12', 'B11', 'B4'], 'min': 0, 'max': 4500, 'gamma': 1.4}, 
        "query": "Reliance refinery margins", 
        "ticker": "RELIANCE.NS",
        "location": "Jamnagar, Gujarat (World's Largest Refinery)",
        "guide": "ANALYSIS (SWIR Band): White circles are storage tanks. Bright glowing yellow spots indicate active heat flares or processing units."
    },
    "4. TATA STEEL (Jamshedpur)": { 
        "roi": [86.1950, 22.7950, 86.2050, 22.8050], 
        "vis": {'bands': ['B12', 'B11', 'B4'], 'min': 0, 'max': 4000, 'gamma': 1.4}, 
        "query": "Tata Steel production", 
        "ticker": "TATASTEEL.NS",
        "location": "Jamshedpur, Jharkhand (Main Steel Works)",
        "guide": "ANALYSIS (SWIR Band): Penetrates smog. Intense orange dots reveal active blast furnaces (1500C+). Blue/White roofs are cold sheds."
    },
    "5. HINDALCO (Copper Unit)": { 
        "roi": [72.5300, 21.6900, 72.5600, 21.7200], 
        "vis": {'bands': ['B12', 'B11', 'B4'], 'min': 0, 'max': 4000, 'gamma': 1.2}, 
        "query": "Hindalco copper demand", 
        "ticker": "HINDALCO.NS",
        "location": "Dahej, Gujarat (Birla Copper Complex)",
        "guide": "ANALYSIS (SWIR Band): Large coastal smelter. Dark piles near docks are copper concentrate imports or slag waste."
    },
    "6. ULTRACEMCO (Aditya)": { 
        "roi": [74.6000, 24.7800, 74.6400, 24.8200], 
        "vis": {'bands': ['B12', 'B11', 'B4'], 'min': 0, 'max': 4000, 'gamma': 1.2}, 
        "query": "Cement prices India", 
        "ticker": "ULTRACEMCO.NS",
        "location": "Shambhupura, Rajasthan (Integrated Cement Plant)",
        "guide": "ANALYSIS (SWIR Band): Limestone quarries appear bright White/Cyan. Pinkish surrounding earth indicates cleared topsoil."
    },
    "7. ADANI PORTS (Mundra)": { 
        "roi": [69.6900, 22.7300, 69.7300, 22.7600], 
        "vis": {'bands': ['B8', 'B4', 'B3'], 'min': 0, 'max': 2500, 'gamma': 1.5}, 
        "query": "Adani Ports cargo volume", 
        "ticker": "ADANIPORTS.NS",
        "location": "Mundra, Gujarat (India's Largest Private Port)",
        "guide": "ANALYSIS (NIR Band): Water appears jet black, contrasting with ships (white dots) and docks. Bright red indicates mangrove vegetation."
    },
    "8. CONCOR (Delhi ICD)": { 
        "roi": [77.2880, 28.5200, 77.2980, 28.5300], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000, 'gamma': 1.3}, 
        "query": "Container Corp volume", 
        "ticker": "CONCOR.NS",
        "location": "Tughlakabad, New Delhi (Inland Container Depot)",
        "guide": "ANALYSIS (True Color): Visual view. Look for density of colorful rectangular blocks (shipping containers) in the yard."
    },
    "9. MARUTI (Manesar)": { 
        "roi": [76.9300, 28.3500, 76.9400, 28.3600], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000, 'gamma': 1.4}, 
        "query": "Maruti Suzuki sales", 
        "ticker": "MARUTI.NS",
        "location": "Manesar, Haryana (Vehicle Stockyard)",
        "guide": "ANALYSIS (True Color): Look for grey parking grids. Filled grids = High Inventory. Empty grey asphalt = Low Inventory (High Sales)."
    },
    "10. JEWAR AIRPORT (Site)": { 
        "roi": [77.6000, 28.1600, 77.6400, 28.1900], 
        "vis": {'bands': ['B8', 'B4', 'B3'], 'min': 0, 'max': 3000, 'gamma': 1.3}, 
        "query": "Jewar Airport construction", 
        "ticker": "GMRINFRA.NS",
        "location": "Jewar, Uttar Pradesh (Upcoming Int'l Airport)",
        "guide": "ANALYSIS (NIR Band): Vegetation is red. The bright white/cyan strip is the bare earth of the runway construction site."
    },
    "11. BHADLA SOLAR (Park)": { 
        "roi": [71.9000, 27.5300, 71.9400, 27.5600], 
        "vis": {'bands': ['B8', 'B4', 'B3'], 'min': 0, 'max': 3000, 'gamma': 1.2}, 
        "query": "India solar power capacity", 
        "ticker": None,
        "location": "Bhadla, Rajasthan (World's Largest Solar Park)",
        "guide": "ANALYSIS (NIR Band): Solar panels appear dark Blue/Black (absorbing light), contrasting against bright white desert sand."
    },
    "12. BHAKRA DAM (Reservoir)": { 
        "roi": [76.4100, 31.3900, 76.4500, 31.4200], 
        "vis": {'bands': ['B8', 'B4', 'B3'], 'min': 0, 'max': 2500, 'gamma': 1.4}, 
        "query": "Monsoon rainfall India", 
        "ticker": None,
        "location": "Bilaspur, Himachal Pradesh (Gobind Sagar)",
        "guide": "ANALYSIS (NIR Band): Deep water is black. Light blue fringes indicate shallow water or drying banks. Red is hill vegetation."
    }
}

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
def get_valuation_data(ticker):
    if not ticker: return {"price": "N/A", "pe": "N/A", "signal": "N/A"}
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="1mo")
        current_price = info.get('currentPrice', 0)
        if not current_price and not hist.empty: current_price = hist['Close'].iloc[-1]
        pe_ratio = info.get('trailingPE', 0)
        
        change_pct = 0
        if not hist.empty:
            start_price = hist['Close'].iloc[0]
            change_pct = ((current_price - start_price) / start_price) * 100
            
        signal = "NEUTRAL"
        if pe_ratio > 0:
            if pe_ratio < 15 and change_pct < 10: signal = "VALUE BUY"
            elif pe_ratio > 40: signal = "OVERVALUED"
            elif change_pct > 15: signal = "HEATED"
        
        return {"price": f"Rs {current_price:.1f}", "pe": f"{pe_ratio:.1f}x", "signal": signal}
    except: return {"price": "Error", "pe": "-", "signal": "Error"}

def get_satellite_data(coords, vis, filename):
    try:
        roi = ee.Geometry.Rectangle(coords)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=45)
        
        col = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
               .filterBounds(roi)
               .filterDate(start_date, end_date)
               .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 15))
               .sort('system:time_start', False))
        
        if col.size().getInfo() > 0:
            vis_params = {
                'min': vis['min'], 
                'max': vis['max'], 
                'bands': vis['bands'], 
                'region': roi, 
                'format': 'jpg', 
                'dimensions': 700, 
                'gamma': vis.get('gamma', 1.0)
            }
            url = col.first().getThumbURL(vis_params)
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
            if "http" in link: 
                news_data.append({'title': title, 'link': link, 'date': date})
        if not news_data:
             safe_link = f"https://www.google.com/search?q={urllib.parse.quote(query)}&tbm=nws"
             news_data.append({'title': "No fresh news. Click for Search.", 'link': safe_link, 'date': "N/A"})
        return news_data
    except:
        return [{'title': "News fetch failed.", 'link': "#", 'date': "Error"}]

# ==========================================
# 4. REPORT GENERATION (SAFE & ENHANCED)
# ==========================================
print("🚀 [SYSTEM] Generating Enhanced Report...")

pdf = FPDF()
pdf.set_auto_page_break(auto=True, margin=15)

for i, (name, data) in enumerate(targets.items()):
    print(f"   ...Analyzing: {name}")
    
    img_filename = f"sector_{i}.jpg"
    img_url, has_image = get_satellite_data(data['roi'], data['vis'], img_filename)
    news_items = get_market_news(data['query'])
    val_data = get_valuation_data(data['ticker'])
    
    pdf.add_page()
    
    # 1. Header (Sanitized)
    pdf.set_font("Arial", "B", 14)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 10, clean_text(name), ln=True)
    
    # 2. Location Context (Sanitized)
    pdf.set_font("Arial", "I", 10)
    pdf.set_text_color(100, 100, 100)
    # We stripped the emoji from the dictionary above, but we clean it here again to be safe
    pdf.cell(0, 6, clean_text(f"Location: {data['location']}"), ln=True)
    pdf.ln(2)

    # 3. Valuation Bar
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, f"  Price: {val_data['price']}  |  P/E: {val_data['pe']}  |  Signal: {val_data['signal']}", ln=True, fill=True)
    pdf.ln(5)
    
    # 4. News Links (Sanitized)
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(0, 0, 255)
    for n in news_items:
        # Clean title to remove potential emojis/unicode
        safe_title = clean_text(f"[{n['date']}] {n['title']}")
        pdf.write(5, safe_title, n['link'])
        pdf.ln(7)
    
    pdf.ln(5)
    
    # 5. Image & Analyst Guide (Sanitized)
    if has_image:
        try:
            pdf.image(img_filename, x=10, w=190)
            pdf.ln(5)
            
            # The Analyst Legend
            pdf.set_font("Arial", "B", 9)
            pdf.set_text_color(50, 50, 50)
            pdf.multi_cell(0, 5, clean_text(data['guide']))
            
        except:
            pdf.cell(0, 10, "Image Error", ln=True)

# Finalize
filename = "Financial_Intel_Report.pdf"
pdf.output(filename)
print("✅ Report Generated.")

# Telegram Send
if BOT_TOKEN and CHAT_ID:
    print("🚀 Sending to Telegram...")
    try:
        with open(filename, 'rb') as f:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
            payload = {"chat_id": CHAT_ID, "caption": "🛰️ **Strategic Satellite Dispatch**\nFull Imagery & Analyst Guides Included."}
            files = {"document": f}
            requests.post(url, data=payload, files=files)
            print("✅ Sent.")
    except Exception as e:
        print(f"❌ Telegram Error: {e}")
