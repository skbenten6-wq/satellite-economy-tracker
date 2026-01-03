import os
import json
import ee
import smtplib
import requests
import urllib.request
import urllib.parse
from PIL import Image
from email.message import EmailMessage
from datetime import datetime
from google.oauth2.service_account import Credentials
from GoogleNews import GoogleNews
from fpdf import FPDF

# ==========================================
# 1. CONFIGURATION & AUTH
# ==========================================
PROJECT_ID = "satellite-tracker-2026"
EMAIL_USER = os.environ.get("MAIL_USERNAME")
EMAIL_PASS = os.environ.get("MAIL_PASSWORD")

try:
    service_account_info = json.loads(os.environ["EE_KEY"])
    credentials = Credentials.from_service_account_info(
        service_account_info, 
        scopes=['https://www.googleapis.com/auth/earthengine']
    )
    ee.Initialize(credentials=credentials, project=PROJECT_ID)
    print("✅ [SYSTEM] Satellite Connection Established")
except Exception as e:
    print(f"❌ [CRITICAL] Auth Failed: {e}")
    exit(1)

googlenews = GoogleNews(period='1d') 
googlenews.set_lang('en')
googlenews.set_encode('utf-8')

# ==========================================
# 2. SECTOR TARGET LIST (12 KEY INDICATORS)
# ==========================================
targets = {
    "1. COAL INDIA (Gevra Mine)": { "roi": [82.5600, 22.3100, 82.6000, 22.3500], "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000}, "query": "Coal India production", "desc": "Pit Expansion" },
    "2. NMDC (Bailadila Iron)": { "roi": [81.2000, 18.6600, 81.2400, 18.7000], "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000}, "query": "NMDC iron ore prices", "desc": "Red Ore Piles" },
    "3. RELIANCE (Oil Storage)": { "roi": [69.8300, 22.3300, 69.9100, 22.3800], "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000}, "query": "Crude oil inventory India", "desc": "Tank Farm Levels" },
    "4. TATA STEEL (Jamshedpur)": { "roi": [86.1950, 22.7950, 86.2050, 22.8050], "vis": {'bands': ['B12', 'B11', 'B4'], 'min': 0, 'max': 4000}, "query": "Tata Steel India production", "desc": "Blast Furnace Heat" },
    "5. HINDALCO (Copper Dahej)": { "roi": [72.5300, 21.6900, 72.5600, 21.7200], "vis": {'bands': ['B12', 'B11', 'B4'], 'min': 0, 'max': 4000}, "query": "Copper prices India demand", "desc": "Smelter Activity" },
    "6. ULTRATECH (Aditya Cement)": { "roi": [74.6000, 24.7800, 74.6400, 24.8200], "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000}, "query": "Cement demand India", "desc": "Grey Dust & Quarry" },
    "7. ADANI PORTS (Mundra)": { "roi": [69.6900, 22.7300, 69.7300, 22.7600], "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000}, "query": "Adani Ports cargo volume", "desc": "Ships at Dock" },
    "8. CONCOR (Delhi Depot)": { "roi": [77.2880, 28.5200, 77.2980, 28.5300], "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000}, "query": "Container Corp volume", "desc": "Container Density" },
    "9. MARUTI (Manesar Yard)": { "roi": [76.9300, 28.3500, 76.9400, 28.3600], "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000}, "query": "Maruti Suzuki sales", "desc": "Car Inventory" },
    "10. JEWAR AIRPORT (Const.)": { "roi": [77.6000, 28.1600, 77.6400, 28.1900], "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000}, "query": "Jewar Airport status", "desc": "Construction Progress" },
    "11. BHADLA SOLAR (Energy)": { "roi": [71.9000, 27.5300, 71.9400, 27.5600], "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000}, "query": "India solar capacity", "desc": "Panel Expansion" },
    "12. BHAKRA DAM (Hydro)": { "roi": [76.4100, 31.3900, 76.4500, 31.4200], "vis": {'bands': ['B8', 'B4', 'B3'], 'min': 0, 'max': 3000}, "query": "Monsoon rainfall India", "desc": "Water Level" }
}

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
def get_satellite_image(coords, vis, filename):
    roi = ee.Geometry.Rectangle(coords)
    col = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(roi).filterDate('2024-12-01', '2025-01-04').filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)).sort('system:time_start', False)
    
    if col.size().getInfo() == 0:
        col = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(roi).filterDate('2024-11-01', '2025-01-04').sort('system:time_start', False)
    
    if col.size().getInfo() > 0:
        url = col.first().getThumbURL({'min': vis['min'], 'max': vis['max'], 'bands': vis['bands'], 'region': roi, 'format': 'png', 'dimensions': 800}) # High Res for PDF
        urllib.request.urlretrieve(url, filename)
        return True
    return False

def get_market_news(query):
    googlenews.clear()
    googlenews.search(query)
    results = googlenews.result()
    news_items = []
    
    for item in results[:2]: # Top 2
        title = item.get('title', '')
        date = item.get('date', 'Recent')
        # Clean text for PDF (Remove Emojis/Unicode)
        clean_title = title.encode('latin-1', 'ignore').decode('latin-1')
        news_items.append(f"[{date}] {clean_title}")
    
    if not news_items: return ["No significant news in last 24h."]
    return news_items

# ==========================================
# 4. GENERATE PDF REPORT
# ==========================================
print("🚀 [SYSTEM] Generating Intelligence Report...")

# Initialize PDF
pdf = FPDF()
pdf.set_auto_page_break(auto=True, margin=15)

# Initialize HTML Email Body
html_body = "<html><body><h2>Supply Chain Alpha Report</h2><p>Attached is the high-resolution PDF analysis.</p></body></html>"

for i, (name, data) in enumerate(targets.items()):
    print(f"   ...Processing: {name}")
    
    # 1. Download High-Res Image locally
    img_filename = f"sector_{i}.png"
    has_image = get_satellite_image(data['roi'], data['vis'], img_filename)
    
    # 2. Fetch News
    news = get_market_news(data['query'])
    
    # --- ADD TO PDF ---
    pdf.add_page()
    
    # Header
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"{name}", ln=True)
    pdf.set_font("Arial", "I", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, f"Target Strategy: {data['desc']}", ln=True)
    
    # News Section
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "", 10)
    pdf.ln(5)
    for news_line in news:
        pdf.multi_cell(0, 8, f"- {news_line}")
    
    # Image Section
    pdf.ln(5)
    if has_image:
        # Full width image
        pdf.image(img_filename, x=10, w=190)
    else:
        pdf.cell(0, 10, "[Satellite Data Unavailable - Cloud Cover]", ln=True)

# Save PDF
pdf_filename = "Daily_Intel_Report.pdf"
pdf.output(pdf_filename)
print(f"✅ PDF Generated: {pdf_filename}")

# ==========================================
# 5. DISPATCH EMAIL (WITH ATTACHMENT)
# ==========================================
print("📧 [SYSTEM] Sending Dispatch...")

msg = EmailMessage()
msg['Subject'] = f"Supply Chain Alpha: {datetime.now().strftime('%d %b')} (PDF Report)"
msg['From'] = "Satellite Bot"
msg['To'] = EMAIL_USER

msg.add_alternative(html_body, subtype='html')

# ATTACH PDF
with open(pdf_filename, 'rb') as f:
    file_data = f.read()
    msg.add_attachment(file_data, maintype='application', subtype='pdf', filename=pdf_filename)

with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
    smtp.login(EMAIL_USER, EMAIL_PASS)
    smtp.send_message(msg)

print("✅ [SUCCESS] Report Sent.")
