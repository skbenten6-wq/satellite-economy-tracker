import ee
import os
import requests
import json
import yfinance as yf
from datetime import datetime, timedelta
from fpdf import FPDF
from GoogleNews import GoogleNews
from market_memory import update_stock_sentiment

# --- CONFIGURATION ---
TARGETS = {
    "TATASTEEL": {"coords": [86.18, 22.75], "type": "Mine", "ticker": "TATASTEEL.NS"},
    "ADANIPORTS": {"coords": [69.70, 22.75], "type": "Port", "ticker": "ADANIPORTS.NS"},
    "ULTRACEMCO": {"coords": [85.00, 24.50], "type": "Factory", "ticker": "ULTRACEMCO.NS"},
    "RELIANCE": {"coords": [70.18, 22.40], "type": "Refinery", "ticker": "RELIANCE.NS"}
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

# --- 1. SATELLITE ANALYSIS ---
def analyze_location(name, info):
    if not EE_READY: return "NEUTRAL", "Auth Failed", None

    try:
        # Get Sentinel-2 Data
        collection = (ee.ImageCollection('COPERNICUS/S2_SR')
                      .filterBounds(ee.Geometry.Point(info['coords']))
                      .filterDate(datetime.now() - timedelta(days=20), datetime.now()) # Expanded range
                      .sort('CLOUDY_PIXEL_PERCENTAGE'))
        
        image = collection.first()
        if not image: return "NEUTRAL", "No Recent Data", None
            
        clouds = image.get('CLOUDY_PIXEL_PERCENTAGE').getInfo()
        
        # Download Thumbnail (JPG)
        image_file = f"{name}.jpg" 
        try:
            vis_params = {'min': 0, 'max': 3000, 'bands': ['B4', 'B3', 'B2'], 'dimensions': 600, 'format': 'jpg'}
            thumb_url = image.getThumbURL(vis_params)
            img_data = requests.get(thumb_url).content
            with open(image_file, 'wb') as f:
                f.write(img_data)
        except:
            image_file = None

        sentiment = "POSITIVE" if clouds < 20 else "NEUTRAL"
        status = f"Cloud Cover: {clouds:.1f}%"
        return sentiment, status, image_file

    except Exception as e:
        print(f"Error analyzing {name}: {e}")
        return "NEUTRAL", "Satellite Error", None

# --- 2. FINANCIAL & NEWS HUNTER ---
def get_financial_intel(ticker):
    """Fetches Price, PE, and News"""
    data = {"price": "N/A", "pe": "N/A", "news": []}
    
    # A. Market Data
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1d")
        if not hist.empty:
            data["price"] = f"{hist['Close'].iloc[-1]:.2f}"
            data["pe"] = f"{stock.info.get('trailingPE', 'N/A')}"
    except: pass

    # B. News Data
    try:
        googlenews = GoogleNews(period='2d')
        googlenews.search(ticker.replace(".NS",""))
        results = googlenews.result()
        if results:
            for item in results[:2]: # Top 2 news
                title = item['title'].encode('latin-1', 'ignore').decode('latin-1')
                date = item.get('date', 'Recent')
                data["news"].append(f"[{date}] {title}")
    except:
        data["news"].append("No recent news.")
        
    return data

# --- 3. PDF REPORT GENERATION (Restored Style) ---
class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'FINANCIAL INTELLIGENCE DISPATCH', 0, 1, 'C')
        self.ln(5)

def create_and_send_report(results):
    pdf = PDFReport()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    
    pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d')}", 0, 1)
    pdf.ln(5)
    
    for i, (target, data) in enumerate(results.items(), 1):
        # 1. IMAGE (Top)
        if data['image'] and os.path.exists(data['image']):
            pdf.image(data['image'], x=10, y=pdf.get_y(), w=190, h=100) # Large Image
            pdf.ln(105) # Move down past image
        
        # 2. TITLE
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, f"{i}. {target} ({data['type']})", 0, 1)
        
        # 3. FINANCIAL LINE
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 8, f"Price: Rs. {data['fin']['price']} | P/E: {data['fin']['pe']} | Sat Sentiment: {data['sentiment']}", 0, 1)
        
        # 4. NEWS LIST
        pdf.set_font("Arial", size=9)
        if data['fin']['news']:
            for news_item in data['fin']['news']:
                pdf.multi_cell(0, 5, f"- {news_item}")
        pdf.ln(10)
        
    filename = "Financial_Intel_Report.pdf"
    pdf.output(filename)
    
    if BOT_TOKEN and CHAT_ID:
        with open(filename, 'rb') as f:
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
                data={"chat_id": CHAT_ID, "caption": "📊 **Financial & Satellite Intel**\nReport Generated."},
                files={"document": f}
            )

# --- 4. MEMORY SYNC ---
def commit_memory_to_github():
    try:
        os.system('git config --global user.email "bot@github.com"')
        os.system('git config --global user.name "Satellite Bot"')
        os.system('git add market_memory.json')
        os.system('git commit -m "Update Intel [Skip CI]"')
        os.system('git push')
    except: pass

if __name__ == "__main__":
    print("🚀 Starting Hybrid Scan...")
    scan_results = {}
    
    for name, info in TARGETS.items():
        print(f"Scanning {name}...")
        
        # 1. Satellite
        sentiment, details, img = analyze_location(name, info)
        
        # 2. Financials
        fin_data = get_financial_intel(info['ticker'])
        
        scan_results[name] = {
            "sentiment": sentiment, 
            "type": info['type'], 
            "image": img,
            "fin": fin_data
        }
        
        update_stock_sentiment(name, sentiment)

    create_and_send_report(scan_results)
    commit_memory_to_github()
