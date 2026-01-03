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

# Authenticate Earth Engine
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

# Initialize News (Strict 24h)
googlenews = GoogleNews(period='1d') 
googlenews.set_lang('en')
googlenews.set_encode('utf-8')

# ==========================================
# 2. TARGET LIST
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
def get_satellite_data(coords, vis, filename):
    """Returns (Public URL, Download Success Boolean)"""
    roi = ee.Geometry.Rectangle(coords)
    col = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(roi).filterDate('2024-12-01', '2025-01-04').filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)).sort('system:time_start', False)
    
    if col.size().getInfo() == 0:
        col = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(roi).filterDate('2024-11-01', '2025-01-04').sort('system:time_start', False)
    
    if col.size().getInfo() > 0:
        # Get URL
        url = col.first().getThumbURL({'min': vis['min'], 'max': vis['max'], 'bands': vis['bands'], 'region': roi, 'format': 'png', 'dimensions': 600})
        # Download for PDF
        try:
            urllib.request.urlretrieve(url, filename)
            return url, True
        except:
            return url, False
    return None, False

def get_market_news(query):
    """Returns list of dicts with Title, Link, Date"""
    googlenews.clear()
    googlenews.search(query)
    results = googlenews.result()
    news_data = []
    
    for item in results[:2]:
        title = item.get('title', '')
        link = item.get('link', '')
        date = item.get('date', 'Recent')
        
        # Link Hygiene
        if link.startswith("./"): link = f"https://news.google.com{link[1:]}"
        
        # Clean Title for PDF
        clean_title = title.encode('latin-1', 'ignore').decode('latin-1')
        
        if "http" in link:
            news_data.append({'title': clean_title, 'link': link, 'date': date})
            
    if not news_data:
        # Safe Search Link
        safe_link = f"https://www.google.com/search?q={urllib.parse.quote(query)}&tbm=nws"
        news_data.append({'title': "No fresh news. Click to Search.", 'link': safe_link, 'date': "N/A"})
        
    return news_data

# ==========================================
# 4. REPORT GENERATION (HTML + PDF)
# ==========================================
print("🚀 [SYSTEM] Generating Hybrid Report...")

# INIT PDF
pdf = FPDF()
pdf.set_auto_page_break(auto=True, margin=15)

# INIT HTML
html_report = """
<html>
<body style="font-family: Arial, sans-serif; background-color: #f4f6f7; padding: 20px;">
    <div style="max-width: 800px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); overflow: hidden;">
        <div style="background-color: #2c3e50; padding: 20px; text-align: center; color: white;">
            <h2 style="margin:0;">SUPPLY CHAIN ALPHA</h2>
            <p style="margin:5px; font-size:12px;">Daily Satellite & News Intelligence</p>
        </div>
        <table style="width:100%; border-collapse: collapse;">
"""

for i, (name, data) in enumerate(targets.items()):
    print(f"   ...Processing: {name}")
    
    # 1. GET DATA
    img_filename = f"sector_{i}.png"
    img_url, has_image = get_satellite_data(data['roi'], data['vis'], img_filename)
    news_items = get_market_news(data['query'])
    
    # -----------------------------
    # BUILD HTML (For Email Body)
    # -----------------------------
    news_html = ""
    for n in news_items:
        color = "green" if "ago" in n['date'] else "gray"
        news_html += f"""
        <div style="margin-bottom:5px; font-size:12px;">
            <span style="color:{color}; font-weight:bold; font-size:10px;">[{n['date']}]</span>
            <a href="{n['link']}" style="text-decoration:none; color:#2980b9; font-weight:bold;">{n['title']}</a>
        </div>
        """
        
    html_report += f"""
    <tr style="border-bottom: 1px solid #eee;">
        <td style="width: 40%; padding: 15px; background-color: #f9f9f9;">
            <div style="font-size:14px; font-weight:800; color:#2c3e50;">{name}</div>
            <div style="font-size:10px; color:#e67e22; margin-bottom:5px;">Strategy: {data['desc']}</div>
            <img src="{img_url}" style="width:100%; border-radius:4px;">
        </td>
        <td style="width: 60%; padding: 15px; vertical-align:top;">
            <div style="font-size:10px; font-weight:bold; color:#7f8c8d; margin-bottom:8px;">LATEST INTEL</div>
            {news_html}
        </td>
    </tr>
    """

    # -----------------------------
    # BUILD PDF (For Attachment)
    # -----------------------------
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"{name}", ln=True)
    
    pdf.set_font("Arial", "I", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, f"Strategy: {data['desc']}", ln=True)
    
    # News Links in PDF
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(0, 0, 255) # Blue Text
    for n in news_items:
        # Create a clickable cell
        pdf.cell(0, 8, f"[{n['date']}] {n['title']}", ln=True, link=n['link'])
    
    pdf.ln(5)
    
    # Image in PDF
    if has_image:
        pdf.image(img_filename, x=10, w=190)
    else:
        pdf.set_text_color(255, 0, 0)
        pdf.cell(0, 10, "[Cloud Cover - No Image]", ln=True)

# CLOSE HTML
html_report += """
        </table>
        <div style="padding:15px; text-align:center; font-size:11px; color:#aaa;">
            &copy; 2026 Satellite Bot | See attached PDF for high-res archives.
        </div>
    </div>
</body>
</html>
"""

# SAVE PDF
pdf_filename = "Supply_Chain_Intel.pdf"
pdf.output(pdf_filename)
print("✅ PDF & HTML Generated.")

# ==========================================
# 5. DISPATCH EMAIL
# ==========================================
print("📧 [SYSTEM] Sending Hybrid Dispatch...")

msg = EmailMessage()
msg['Subject'] = f"Supply Chain Alpha: {datetime.now().strftime('%d %b')} (Hybrid Report)"
msg['From'] = "Satellite Bot"
msg['To'] = EMAIL_USER

# 1. Add HTML Body
msg.add_alternative(html_report, subtype='html')

# 2. Add PDF Attachment
with open(pdf_filename, 'rb') as f:
    file_data = f.read()
    msg.add_attachment(file_data, maintype='application', subtype='pdf', filename=pdf_filename)

with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
    smtp.login(EMAIL_USER, EMAIL_PASS)
    smtp.send_message(msg)

print("✅ [SUCCESS] Email Sent with HTML Body + PDF Attachment.")
