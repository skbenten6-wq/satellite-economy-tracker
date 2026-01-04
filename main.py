import ee
import geemap
import os
import requests
import json
from datetime import datetime, timedelta
from fpdf import FPDF
from market_memory import update_stock_sentiment # Import the Brain

# --- CONFIGURATION ---
TARGETS = {
    "TATASTEEL": {"coords": [86.18, 22.75], "type": "Mine"}, # Jamshedpur/Noamundi
    "ADANIPORTS": {"coords": [69.70, 22.75], "type": "Port"}, # Mundra
    "ULTRACEMCO": {"coords": [85.00, 24.50], "type": "Factory"},
    "RELIANCE": {"coords": [70.18, 22.40], "type": "Refinery"} # Jamnagar
}

BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# --- AUTHENTICATION ---
try:
    import base64
    service_account = os.environ.get("EE_KEY")
    if service_account:
        creds_json = base64.b64decode(service_account).decode('utf-8')
        creds = ee.ServiceAccountCredentials(None, key_data=creds_json)
        ee.Initialize(creds)
    else:
        ee.Initialize()
except Exception as e:
    print(f"⚠️ Earth Engine Auth Failed: {e}")

# --- ANALYSIS FUNCTIONS ---
def analyze_location(name, info):
    try:
        collection = (ee.ImageCollection('COPERNICUS/S2_SR')
                      .filterBounds(ee.Geometry.Point(info['coords']))
                      .filterDate(datetime.now() - timedelta(days=5), datetime.now())
                      .sort('CLOUDY_PIXEL_PERCENTAGE'))
        
        image = collection.first()
        if not image: return "NEUTRAL", "Cloudy/No Data"
            
        clouds = image.get('CLOUDY_PIXEL_PERCENTAGE').getInfo()
        
        if clouds < 20: return "POSITIVE", f"Clear View (Clouds: {clouds:.1f}%)"
        else: return "NEUTRAL", f"Obstructed (Clouds: {clouds:.1f}%)"
    except:
        return "NEUTRAL", "Satellite Error"

# --- PDF REPORT GENERATION (NO EMOJIS ALLOWED HERE) ---
class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        # REMOVED THE EMOJI FROM THIS LINE
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
        # Ensure raw strings are used, no special chars
        pdf.cell(0, 10, f"Sentiment: {data['sentiment']}", 0, 1)
        pdf.cell(0, 10, f"Status: {data['details']}", 0, 1)
        pdf.ln(5)
        
    filename = "satellite_report.pdf"
    pdf.output(filename)
    
    # Send to Telegram (Emojis are fine here!)
    if BOT_TOKEN and CHAT_ID:
        with open(filename, 'rb') as f:
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
                data={"chat_id": CHAT_ID, "caption": "🛰️ **Sector Scan Complete**\nBrain updated with latest findings."},
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

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    print("🛰️ Starting Orbital Scan...")
    scan_results = {}
    
    for ticker, info in TARGETS.items():
        sentiment, details = analyze_location(ticker, info)
        scan_results[ticker] = {"sentiment": sentiment, "details": details, "type": info['type']}
        
        # WRITE TO BRAIN
        update_stock_sentiment(ticker, sentiment)
        print(f"✅ {ticker}: {sentiment}")

    create_and_send_report(scan_results)
    commit_memory_to_github()
