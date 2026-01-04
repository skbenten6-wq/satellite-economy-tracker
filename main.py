import ee
import geemap
import os
import requests
import json
from datetime import datetime, timedelta
from fpdf import FPDF
from GoogleNews import GoogleNews
from market_memory import update_stock_sentiment

# --- CONFIGURATION ---
TARGETS = {
    "TATASTEEL": {"coords": [86.18, 22.75], "type": "Mine"},
    "ADANIPORTS": {"coords": [69.70, 22.75], "type": "Port"},
    "ULTRACEMCO": {"coords": [85.00, 24.50], "type": "Factory"},
    "RELIANCE": {"coords": [70.18, 22.40], "type": "Refinery"}
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
                      .filterDate(datetime.now() - timedelta(days=10), datetime.now())
                      .sort('CLOUDY_PIXEL_PERCENTAGE'))
        
        image = collection.first()
        if not image: return "NEUTRAL", "No Recent Data", None
            
        clouds = image.get('CLOUDY_PIXEL_PERCENTAGE').getInfo()
        
        # Download Thumbnail (SWITCHED TO JPG FOR STABILITY)
        image_file = f"{name}.jpg" 
        try:
            # Visualize True Color
            vis_params = {'min': 0, 'max': 3000, 'bands': ['B4', 'B3', 'B2'], 'dimensions': 600, 'format': 'jpg'}
            thumb_url = image.getThumbURL(vis_params)
            img_data = requests.get(thumb_url).content
            with open(image_file, 'wb') as f:
                f.write(img_data)
        except Exception as e:
            print(f"⚠️ Image Download Failed: {e}")
            image_file = None

        sentiment = "POSITIVE" if clouds < 20 else "NEUTRAL"
        status = f"Cloud Cover: {clouds:.1f}%"
        
        return sentiment, status, image_file

    except Exception as e:
        print(f"Error analyzing {name}: {e}")
        return "NEUTRAL", "Satellite Error", None

# --- 2. NEWS HUNTER ---
def get_company_news(ticker):
    """Fetches top 3 headlines for the company"""
    try:
        googlenews = GoogleNews(period='3d')
        googlenews.search(ticker)
        results = googlenews.result()
        headlines = []
        if results:
            for item in results[:3]: # Get top 3
                # clean text to avoid PDF unicode errors
                clean_title = item['title'].encode('latin-1', 'ignore').decode('latin-1')
                headlines.append(f"- {clean_title}")
        return headlines
    except:
        return ["No recent news found."]

# --- 3. PDF REPORT GENERATION ---
class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'SATELLITE & NEWS INTELLIGENCE', 0, 1, 'C')
        self.ln(5)

def create_and_send_report(results):
    pdf = PDFReport()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d')}", 0, 1)
    pdf.ln(5)
    
    for ticker, data in results.items():
        # TITLE
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, f"{ticker} ({data['type']})", 0, 1)
        
        # DATA
        pdf.set_font("Arial", size=11)
        pdf.cell(0, 8, f"Sentiment: {data['sentiment']}", 0, 1)
        pdf.cell(0, 8, f"Status: {data['details']}", 0, 1)
        
        # IMAGE (JPG Works much better here)
        if data['image'] and os.path.exists(data['image']):
            try:
                pdf.image(data['image'], x=10, y=pdf.get_y(), w=100)
                pdf.ln(65) # Move cursor down past image
            except:
                pdf.cell(0, 10, "[Image Render Failed]", 0, 1)
        else:
            pdf.ln(5)

        # NEWS SECTION
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, "Recent Intel:", 0, 1)
        pdf.set_font("Arial", size=9)
        if data['news']:
            for news in data['news']:
                pdf.multi_cell(0, 5, news)
        else:
            pdf.cell(0, 8, "No news found.", 0, 1)
            
        pdf.ln(10) # Spacing between stocks
        
    filename = "satellite_report.pdf"
    pdf.output(filename)
    
    if BOT_TOKEN and CHAT_ID:
        with open(filename, 'rb') as f:
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
                data={"chat_id": CHAT_ID, "caption": "🛰️ **Full Intel Report**\nSatellite + News Analysis Complete."},
                files={"document": f}
            )

# --- 4. MEMORY SYNC ---
def commit_memory_to_github():
    try:
        os.system('git config --global user.email "bot@github.com"')
        os.system('git config --global user.name "Satellite Bot"')
        os.system('git add market_memory.json')
        os.system('git commit -m "🛰️ Update Satellite Intel [Skip CI]"')
        os.system('git push')
        print("✅ Brain Synced to GitHub.")
    except Exception as e:
        print(f"⚠️ Brain Sync Failed: {e}")

if __name__ == "__main__":
    print("🛰️ Starting Hybrid Scan...")
    scan_results = {}
    
    for ticker, info in TARGETS.items():
        print(f"Scanning {ticker}...")
        
        # 1. Get Satellite Data
        sentiment, details, img_path = analyze_location(ticker, info)
        
        # 2. Get News Data
        news = get_company_news(ticker)
        
        scan_results[ticker] = {
            "sentiment": sentiment, 
            "details": details, 
            "type": info['type'], 
            "image": img_path,
            "news": news
        }
        
        # 3. Update Brain
        update_stock_sentiment(ticker, sentiment)

    create_and_send_report(scan_results)
    commit_memory_to_github()
