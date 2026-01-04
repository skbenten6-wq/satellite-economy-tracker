import ee
import geemap
import os
import requests
import json
from datetime import datetime, timedelta
from fpdf import FPDF
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

# --- ANALYSIS FUNCTIONS ---
def analyze_location(name, info):
    if not EE_READY:
        return "NEUTRAL", "Auth Failed - Check EE_KEY", None

    try:
        # Get Sentinel-2 Data
        collection = (ee.ImageCollection('COPERNICUS/S2_SR')
                      .filterBounds(ee.Geometry.Point(info['coords']))
                      .filterDate(datetime.now() - timedelta(days=10), datetime.now())
                      .sort('CLOUDY_PIXEL_PERCENTAGE'))
        
        image = collection.first()
        if not image: return "NEUTRAL", "No Recent Data", None
            
        clouds = image.get('CLOUDY_PIXEL_PERCENTAGE').getInfo()
        
        # --- NEW: DOWNLOAD THUMBNAIL ---
        image_file = f"{name}.jpg"
        try:
            # Visualize True Color (B4=Red, B3=Green, B2=Blue)
            vis_params = {'min': 0, 'max': 3000, 'bands': ['B4', 'B3', 'B2'], 'dimensions': 600}
            thumb_url = image.getThumbURL(vis_params)
            img_data = requests.get(thumb_url).content
            with open(image_file, 'wb') as f:
                f.write(img_data)
        except Exception as e:
            print(f"⚠️ Could not download image for {name}: {e}")
            image_file = None

        sentiment = "POSITIVE" if clouds < 20 else "NEUTRAL"
        status = f"Cloud Cover: {clouds:.1f}%"
        
        return sentiment, status, image_file

    except Exception as e:
        print(f"Error analyzing {name}: {e}")
        return "NEUTRAL", "Satellite Error", None

# --- PDF REPORT GENERATION ---
class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'SATELLITE INTELLIGENCE DISPATCH', 0, 1, 'C')
        self.ln(5)

def create_and_send_report(results):
    pdf = PDFReport()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d')}", 0, 1)
    pdf.ln(5)
    
    for ticker, data in results.items():
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, f"TARGET: {ticker} ({data['type']})", 0, 1)
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 10, f"Sentiment: {data['sentiment']}", 0, 1)
        pdf.cell(0, 10, f"Status: {data['details']}", 0, 1)
        
        # EMBED IMAGE IF EXISTS
        if data['image']:
            try:
                # Add image (x=10, width=100)
                pdf.image(data['image'], x=10, y=pdf.get_y(), w=100)
                pdf.ln(60) # Move down past image
            except:
                pdf.cell(0, 10, "[Image Render Failed]", 0, 1)
        else:
            pdf.ln(5)
            
        pdf.ln(5) # Spacing
        
    filename = "satellite_report.pdf"
    pdf.output(filename)
    
    if BOT_TOKEN and CHAT_ID:
        with open(filename, 'rb') as f:
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
                data={"chat_id": CHAT_ID, "caption": "🛰️ **Sector Scan Complete**\nBrain updated."},
                files={"document": f}
            )

# --- MEMORY SYNC ---
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
    print("🛰️ Starting Orbital Scan...")
    scan_results = {}
    
    for ticker, info in TARGETS.items():
        print(f"Scanning {ticker}...")
        sentiment, details, img_path = analyze_location(ticker, info)
        scan_results[ticker] = {
            "sentiment": sentiment, "details": details, 
            "type": info['type'], "image": img_path
        }
        update_stock_sentiment(ticker, sentiment)

    create_and_send_report(scan_results)
    commit_memory_to_github()
