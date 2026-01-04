import ee
import os
import requests
import json
import yfinance as yf
from datetime import datetime, timedelta
from fpdf import FPDF
from GoogleNews import GoogleNews
from market_memory import update_stock_sentiment

# --- 1. STRATEGIC TARGETS (12 LOCATIONS) ---
TARGETS = {
    "COALINDIA": {
        "coords": [82.58, 22.33], "type": "Gevra Mine", "ticker": "COALINDIA.NS"
    },
    "NMDC": {
        "coords": [81.23, 18.73], "type": "Bailadila Iron", "ticker": "NMDC.NS"
    },
    "RELIANCE": {
        "coords": [69.85, 22.36], "type": "Oil Storage", "ticker": "RELIANCE.NS"
    },
    "TATASTEEL": {
        "coords": [86.20, 22.80], "type": "Jamshedpur", "ticker": "TATASTEEL.NS"
    },
    "HINDALCO": {
        "coords": [72.55, 21.70], "type": "Copper Dahej", "ticker": "HINDALCO.NS"
    },
    "ULTRACEMCO": {
        "coords": [74.63, 24.63], "type": "Aditya Cement", "ticker": "ULTRACEMCO.NS"
    },
    "ADANIPORTS": {
        "coords": [69.70, 22.75], "type": "Mundra Port", "ticker": "ADANIPORTS.NS"
    },
    "CONCOR": {
        "coords": [77.28, 28.53], "type": "Delhi Depot", "ticker": "CONCOR.NS"
    },
    "MARUTI": {
        "coords": [76.93, 28.35], "type": "Manesar Yard", "ticker": "MARUTI.NS"
    },
    "JEWAR AIRPORT": {
        "coords": [77.61, 28.21], "type": "Construction", "ticker": None
    },
    "BHADLA SOLAR": {
        "coords": [71.90, 27.50], "type": "Energy Park", "ticker": None
    },
    "BHAKRA DAM": {
        "coords": [76.43, 31.41], "type": "Hydro Level", "ticker": None
    }
}

BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# --- AUTHENTICATION ---
EE_READY = False
try:
    import base64
    service_account = os.environ.get("EE_KEY")
    if service_account:
        creds_json = base64.b64decode(service_account).decode('utf-8')
        creds = ee.ServiceAccountCredentials(None, key_data=creds_json)
        ee.Initialize(creds)
        EE_READY = True
        print("✅ Earth Engine Authenticated")
    else:
        ee.Initialize()
        EE_READY = True
except Exception as e:
    print(f"⚠️ Earth Engine Auth Failed: {e}")

# --- 2. SATELLITE IMAGING (RESTORED INFRARED BANDS) ---
def analyze_location(name, info):
    if not EE_READY: return "NEUTRAL", "Auth Failed", None

    try:
        # Search for clear images in the last 25 days
        collection = (ee.ImageCollection('COPERNICUS/S2_SR')
                      .filterBounds(ee.Geometry.Point(info['coords']))
                      .filterDate(datetime.now() - timedelta(days=25), datetime.now())
                      .sort('CLOUDY_PIXEL_PERCENTAGE'))
        
        image = collection.first()
        if not image: return "NEUTRAL", "No Recent Data", None
            
        clouds = image.get('CLOUDY_PIXEL_PERCENTAGE').getInfo()
        
        # --- THE FIX: USE FALSE COLOR INFRARED (B8, B4, B3) ---
        # B8 = Near Infrared (Highlights Vegetation/Heat) -> Mapped to Red
        # B4 = Red -> Mapped to Green
        # B3 = Green -> Mapped to Blue
        # This creates the high-contrast "Professional" look.
        
        image_file = f"{name.replace(' ', '_')}.jpg"
        try:
            vis_params = {
                'min': 0, 
                'max': 3000, 
                'bands': ['B8', 'B4', 'B3'], # <--- RESTORED BANDS
                'dimensions': 800, 
                'format': 'jpg'
            }
            thumb_url = image.getThumbURL(vis_params)
            img_data = requests.get(thumb_url).content
            with open(image_file, 'wb') as f:
                f.write(img_data)
        except Exception as e:
            print(f"Image download failed for {name}: {e}")
            image_file = None

        sentiment = "POSITIVE" if clouds < 20 else "NEUTRAL"
        status = f"Cloud Cover: {clouds:.1f}%"
        return sentiment, status, image_file

    except Exception as e:
        print(f"Error analyzing {name}: {e}")
        return "NEUTRAL", "Satellite Error", None

# --- 3. FINANCIAL INTELLIGENCE (RESTORED LINKS) ---
def get_financial_intel(ticker):
    data = {"price": "N/A", "pe": "N/A", "signal": "N/A", "news": []}
    
    if not ticker: return data 

    # A. Price & PE
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1d")
        if not hist.empty:
            data["price"] = f"Rs. {hist['Close'].iloc[-1]:.1f}"
            pe = stock.info.get('trailingPE', 0)
            data["pe"] = f"{pe:.1f}x"
            
            if pe > 0 and pe < 15: data["signal"] = "UNDERVALUED"
            elif pe > 40: data["signal"] = "OVERVALUED"
            else: data["signal"] = "NEUTRAL"
    except: pass

    # B. News (Restored Links)
    try:
        googlenews = GoogleNews(period='3d')
        googlenews.search(ticker.replace(".NS",""))
        results = googlenews.result()
        if results:
            for item in results[:2]:
                title = item['title'].encode('latin-1', 'ignore').decode('latin-1')
                date = item.get('date', 'Recent')
                # Restored the [Backup Google Search] text line
                data["news"].append(f"[{date}] {title}\n [Backup Google Search]")
    except:
        data["news"].append("No recent news found.")
        
    return data

# --- 4. PDF GENERATOR ---
class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'SATELLITE INTELLIGENCE DISPATCH', 0, 1, 'C')
        self.ln(5)

def create_and_send_report(results):
    pdf = PDFReport()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    
    pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d')}", 0, 1)
    pdf.ln(5)
    
    for i, (name, data) in enumerate(results.items(), 1):
        # 1. Image
        if data['image'] and os.path.exists(data['image']):
            pdf.image(data['image'], x=10, y=pdf.get_y(), w=190, h=100)
            pdf.ln(105) 
        
        # 2. Header
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, f"{i}. {name} ({data['type']})", 0, 1)
        
        # 3. Data
        pdf.set_font("Arial", 'B', 10)
        fin = data['fin']
        line = f"Price: {fin['price']} | P/E: {fin['pe']} | Signal: {fin['signal']}"
        pdf.cell(0, 8, line, 0, 1)
        
        # 4. News
        pdf.set_font("Arial", size=9)
        if fin['news']:
            for news in fin['news']:
                pdf.multi_cell(0, 5, news)
                pdf.ln(1)
        
        # 5. Status
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 6, f"Sat Status: {data['details']}", 0, 1)
        pdf.set_text_color(0, 0, 0)
        
        pdf.ln(10)

    filename = "Financial_Intel_Report.pdf"
    pdf.output(filename)
    
    if BOT_TOKEN and CHAT_ID:
        with open(filename, 'rb') as f:
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
                data={"chat_id": CHAT_ID, "caption": "🛰️ **Alpha Satellite Dispatch**\nSector Scan Complete."},
                files={"document": f}
            )

# --- 5. EXECUTION ---
def commit_memory():
    try:
        os.system('git config --global user.email "bot@github.com"')
        os.system('git config --global user.name "Satellite Bot"')
        os.system('git add market_memory.json')
        os.system('git commit -m "Update Intel [Skip CI]"')
        os.system('git push')
    except: pass

if __name__ == "__main__":
    print("🚀 Starting Strategic Scan...")
    scan_results = {}
    
    for name, info in TARGETS.items():
        print(f"Scanning {name}...")
        
        # 1. Satellite
        sentiment, details, img = analyze_location(name, info)
        
        # 2. Financial
        fin_data = get_financial_intel(info['ticker'])
        
        scan_results[name] = {
            "type": info['type'],
            "image": img,
            "sentiment": sentiment,
            "details": details,
            "fin": fin_data
        }
        
        if info['ticker']:
            update_stock_sentiment(info['ticker'].replace(".NS",""), sentiment)

    create_and_send_report(scan_results)
    commit_memory()
