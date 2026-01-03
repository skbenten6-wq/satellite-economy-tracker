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

# ==========================================
# 1. CONFIGURATION & AUTHENTICATION
# ==========================================
PROJECT_ID = "satellite-tracker-2026"
EMAIL_USER = os.environ.get("MAIL_USERNAME")
EMAIL_PASS = os.environ.get("MAIL_PASSWORD")

# Authenticate Earth Engine (Robot Mode)
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

# Initialize News Engine (Strict 1-Day Window)
googlenews = GoogleNews(period='1d') 
googlenews.set_lang('en')
googlenews.set_encode('utf-8')

# ==========================================
# 2. SECTOR TARGET LIST (12 KEY INDICATORS)
# ==========================================
targets = {
    # --- ROW 1: RAW MATERIAL INPUTS (The Foundation) ---
    "1. COAL INDIA (Gevra Mine)": { 
        "roi": [82.5600, 22.3100, 82.6000, 22.3500], # Asia's Largest Mine
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000},
        "query": "Coal India production targets",
        "desc": "Pit Expansion (Energy Input)"
    },
    "2. NMDC (Bailadila Iron)": { 
        "roi": [81.2000, 18.6600, 81.2400, 18.7000], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000},
        "query": "NMDC iron ore prices",
        "desc": "Red Ore Piles (Steel Input)"
    },
    "3. RELIANCE (Oil Storage)": { 
        "roi": [69.8300, 22.3300, 69.9100, 22.3800], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000},
        "query": "Crude oil inventory India",
        "desc": "Tank Farm Levels"
    },
    
    # --- ROW 2: INDUSTRIAL ACTIVITY (Processing) ---
    "4. TATA STEEL (Jamshedpur)": { 
        "roi": [86.1950, 22.7950, 86.2050, 22.8050], 
        "vis": {'bands': ['B12', 'B11', 'B4'], 'min': 0, 'max': 4000},
        "query": "Tata Steel India production",
        "desc": "Blast Furnace Heat"
    },
    "5. HINDALCO (Copper Dahej)": { 
        "roi": [72.5300, 21.6900, 72.5600, 21.7200], 
        "vis": {'bands': ['B12', 'B11', 'B4'], 'min': 0, 'max': 4000},
        "query": "Copper prices India demand",
        "desc": "Smelter Activity (Orange=Hot)"
    },
    "6. ULTRATECH (Aditya Cement)": { 
        "roi": [74.6000, 24.7800, 74.6400, 24.8200], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000},
        "query": "Cement demand India construction",
        "desc": "Grey Dust & Quarry Size"
    },

    # --- ROW 3: LOGISTICS & OUTPUT (Movement) ---
    "7. ADANI PORTS (Mundra)": { 
        "roi": [69.6900, 22.7300, 69.7300, 22.7600], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000},
        "query": "Adani Ports cargo volume",
        "desc": "Ships at Dock (Export/Import)"
    },
    "8. CONCOR (Delhi Depot)": { 
        "roi": [77.2880, 28.5200, 77.2980, 28.5300], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000},
        "query": "Container Corp of India volume",
        "desc": "Container Density (Trade Pulse)"
    },
    "9. MARUTI (Manesar Yard)": { 
        "roi": [76.9300, 28.3500, 76.9400, 28.3600], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000},
        "query": "Maruti Suzuki monthly sales",
        "desc": "Finished Car Inventory"
    },

    # --- ROW 4: INFRA & MACRO (The Future) ---
    "10. JEWAR AIRPORT (Const.)": { 
        "roi": [77.6000, 28.1600, 77.6400, 28.1900], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000},
        "query": "Jewar Airport project status",
        "desc": "Construction Progress"
    },
    "11. BHADLA SOLAR (Energy)": { 
        "roi": [71.9000, 27.5300, 71.9400, 27.5600], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000},
        "query": "India solar power capacity",
        "desc": "Panel Expansion"
    },
    "12. BHAKRA DAM (Hydro)": { 
        "roi": [76.4100, 31.3900, 76.4500, 31.4200], 
        "vis": {'bands': ['B8', 'B4', 'B3'], 'min': 0, 'max': 3000},
        "query": "Monsoon rainfall India impact",
        "desc": "Water Level (Black Area)"
    }
}

# ==========================================
# 3. CORE INTELLIGENCE FUNCTIONS
# ==========================================
def get_satellite_image(coords, vis):
    """Fetches the latest cloud-free Sentinel-2 image."""
    roi = ee.Geometry.Rectangle(coords)
    # Priority: December (Recent) -> November (Fallback)
    col = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(roi).filterDate('2024-12-01', '2025-01-04').filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)).sort('system:time_start', False)
    
    if col.size().getInfo() == 0:
        col = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(roi).filterDate('2024-11-01', '2025-01-04').sort('system:time_start', False)
    
    if col.size().getInfo() > 0:
        return col.first().getThumbURL({'min': vis['min'], 'max': vis['max'], 'bands': vis['bands'], 'region': roi, 'format': 'png', 'dimensions': 600})
    return None

def get_market_news(query):
    """Fetches and cleans news from the last 24 hours."""
    googlenews.clear()
    googlenews.search(query)
    results = googlenews.result()
    
    news_html = ""
    count = 0
    safe_search = f"https://www.google.com/search?q={urllib.parse.quote(query)}&tbm=nws"

    for item in results:
        if count >= 2: break 
        
        title = item.get('title', '')
        link = item.get('link', '')
        date = item.get('date', 'Recent')

        if link.startswith("./"):
            link = f"https://news.google.com{link[1:]}"
        
        time_style = "color:#27ae60; font-weight:bold;" if "ago" in date else "color:#7f8c8d;"
        
        if "http" in link and title:
            news_html += f"""
            <div style="margin-bottom: 8px; font-size: 13px; line-height: 1.4;">
                <span style="{time_style}; font-size: 11px;">[{date}]</span>
                <a href="{link}" style="color:#2c3e50; text-decoration:none; font-weight:600;">{title}</a>
            </div>
            """
            count += 1
            
    if count == 0:
        news_html = """<div style="font-style:italic; color:#95a5a6; font-size:12px;">No major headlines in last 24h.</div>"""
        
    news_html += f"""<div style="margin-top:6px;"><a href="{safe_search}" style="font-size:11px; color:#3498db; text-decoration:none;">&rarr; Deep Search</a></div>"""
    
    return news_html

# ==========================================
# 4. REPORT GENERATION LOOP
# ==========================================
print("🚀 [SYSTEM] Initiating Supply Chain Scan...")
html_report = """
<html>
<body style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f4f6f7; padding: 20px;">
    <div style="max-width: 900px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        
        <div style="background-color: #2c3e50; padding: 25px; text-align: center; color: #ffffff;">
            <h2 style="margin: 0; font-size: 26px; letter-spacing: 1.5px;">SUPPLY CHAIN ALPHA</h2>
            <p style="margin: 8px 0 0; font-size: 14px; opacity: 0.9;">12-Point Economic Intelligence Grid</p>
        </div>

        <div style="background-color: #ecf0f1; padding: 10px 20px; border-bottom: 1px solid #bdc3c7; font-size: 12px; color: #7f8c8d; text-align: right;">
            <strong>REPORT DATE:</strong> """ + datetime.now().strftime("%d %B %Y") + """
        </div>

        <table style="width: 100%; border-collapse: collapse;">
"""

for name, data in targets.items():
    print(f"   ...Scanning: {name}")
    img_url = get_satellite_image(data['roi'], data['vis'])
    news_block = get_market_news(data['query'])
    
    html_report += f"""
    <tr style="border-bottom: 1px solid #ecf0f1;">
        <td style="width: 40%; padding: 20px; vertical-align: top; background-color: #fafbfc;">
            <div style="font-size: 10px; font-weight: bold; color: #95a5a6; letter-spacing: 1px; margin-bottom: 5px;">ASSET TRACKER</div>
            <div style="font-size: 16px; font-weight: 800; color: #2c3e50; margin-bottom: 5px;">{name}</div>
            <div style="font-size: 11px; color: #e67e22; font-weight:bold; margin-bottom: 15px;">Target: {data['desc']}</div>
            
            <div style="border: 1px solid #bdc3c7; border-radius: 4px; overflow: hidden; height: 200px; background-color: #eee;">
                <img src="{img_url}" style="width: 100%; height: 100%; object-fit: cover;" alt="Cloud/Data Unavailable">
            </div>
        </td>
        <td style="width: 60%; padding: 20px; vertical-align: top;">
            <div style="font-size: 10px; font-weight: bold; color: #27ae60; letter-spacing: 1px; margin-bottom: 10px;">MARKET INTEL (INPUT/OUTPUT)</div>
            {news_block}
        </td>
    </tr>
    """

html_report += """
        </table>
        <div style="background-color: #2c3e50; color: #95a5a6; padding: 20px; text-align: center; font-size: 11px;">
            &copy; 2026 Supply Chain Alpha | Automated via Earth Engine & Python
        </div>
    </div>
</body>
</html>
"""

# ==========================================
# 5. DISPATCH EMAIL
# ==========================================
print("📧 [SYSTEM] Compiling Report...")
msg = EmailMessage()
msg['Subject'] = f"Supply Chain Alpha: {datetime.now().strftime('%d %b')} (12-Point Grid)"
msg['From'] = "Satellite Alpha Bot"
msg['To'] = EMAIL_USER
msg.add_alternative(html_report, subtype='html')

with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
    smtp.login(EMAIL_USER, EMAIL_PASS)
    smtp.send_message(msg)

print("✅ [SUCCESS] Intelligence Report Delivered.")
