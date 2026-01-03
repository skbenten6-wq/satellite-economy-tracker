import os
import json
import ee
import smtplib
import requests
import urllib.request
from PIL import Image
import matplotlib.pyplot as plt
from google.oauth2.service_account import Credentials
from GoogleNews import GoogleNews
from email.message import EmailMessage
from datetime import datetime

# --- 1. CONFIGURATION & AUTH ---
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
    print("✅ Satellite Systems Online")
except Exception as e:
    print(f"❌ EE Auth Failed: {e}")
    exit(1)

# Initialize News Engine (Last 24 Hours)
googlenews = GoogleNews(period='1d')
googlenews.set_lang('en')
googlenews.set_encode('utf-8')

# --- 2. DEFINE TARGETS (Map + News Keywords) ---
targets = {
    "1. TATA STEEL": { 
        "roi": [86.1950, 22.7950, 86.2050, 22.8050], 
        "vis": {'bands': ['B12', 'B11', 'B4'], 'min': 0, 'max': 4000},
        "query": "Tata Steel India production"
    },
    "2. NTPC DADRI (Power)": { 
        "roi": [77.5500, 28.5900, 77.5700, 28.6100], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000},
        "query": "NTPC coal supply India"
    },
    "3. ADANI PORTS (Mundra)": { 
        "roi": [69.6900, 22.7300, 69.7300, 22.7600], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000},
        "query": "Adani Ports cargo volume"
    },
    "4. RELIANCE (Oil)": { 
        "roi": [69.8300, 22.3300, 69.9100, 22.3800], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000},
        "query": "Reliance Industries refinery margin"
    },
    "5. GRSE (Defense)": { 
        "roi": [88.2960, 22.5390, 88.3020, 22.5430], 
        "vis": {'bands': ['B8', 'B4', 'B3'], 'min': 0, 'max': 3000},
        "query": "Garden Reach Shipbuilders delivery"
    },
    "6. MARUTI (Auto)": { 
        "roi": [76.9300, 28.3500, 76.9400, 28.3600], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000},
        "query": "Maruti Suzuki sales numbers"
    },
     "7. JEWAR AIRPORT": { 
        "roi": [77.6000, 28.1600, 77.6400, 28.1900], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000},
        "query": "Jewar Airport construction status"
    },
    "8. BHAKRA DAM (Hydro)": { 
        "roi": [76.4100, 31.3900, 76.4500, 31.4200], 
        "vis": {'bands': ['B8', 'B4', 'B3'], 'min': 0, 'max': 3000},
        "query": "Bhakra Dam water level forecast"
    }
}

# --- 3. HELPER FUNCTIONS ---
def get_image_url(coords, vis):
    roi = ee.Geometry.Rectangle(coords)
    # Try Dec, then Nov
    col = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(roi).filterDate('2024-12-01', '2025-01-04').filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)).sort('system:time_start', False)
    if col.size().getInfo() == 0:
        col = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(roi).filterDate('2024-11-01', '2025-01-04').sort('system:time_start', False)
    
    if col.size().getInfo() > 0:
        return col.first().getThumbURL({'min': vis['min'], 'max': vis['max'], 'bands': vis['bands'], 'region': roi, 'format': 'png', 'dimensions': 512})
    return None

def get_latest_news(query):
    print(f"📰 Searching: {query}...")
    googlenews.clear()
    googlenews.search(query)
    results = googlenews.result()
    
    # Get top 2 headlines
    headlines = []
    for i in range(min(2, len(results))):
        title = results[i]['title']
        link = results[i]['link']
        headlines.append(f"- {title} ({link})")
    
    if not headlines:
        return ["- No recent news found."]
    return headlines

# --- 4. EXECUTION LOOP ---
print("🚀 Starting Intelligence Scan...")
plt.figure(figsize=(15, 12))
email_body = "DAILY INTELLIGENCE BRIEFING\n===========================\n\n"

for i, (name, data) in enumerate(targets.items()):
    # A. SATELLITE SCAN
    url = get_image_url(data['roi'], data['vis'])
    plt.subplot(3, 3, i+1) # Adjust grid based on count (3x3 fits 8-9 targets)
    
    if url:
        try:
            img = Image.open(urllib.request.urlopen(url))
            plt.imshow(img)
            plt.title(name, fontsize=10, fontweight='bold')
        except:
            plt.text(0.5, 0.5, "Img Error", ha='center')
    else:
        plt.text(0.5, 0.5, "Cloudy", ha='center')
    plt.axis('off')
    
    # B. NEWS SCAN
    headlines = get_latest_news(data['query'])
    
    # C. BUILD REPORT
    email_body += f"[{name}]\n"
    for h in headlines:
        email_body += f"{h}\n"
    email_body += "\n"

plt.tight_layout()
plt.savefig("dashboard.png")
print("✅ Dashboard Generated.")

# --- 5. SEND EMAIL ---
print("📧 Sending Dispatch...")

msg = EmailMessage()
msg['Subject'] = f"🛰️ Daily Intel: Satellite + News ({datetime.now().strftime('%Y-%m-%d')})"
msg['From'] = "Satellite Bot"
msg['To'] = EMAIL_USER
msg.set_content(email_body)

# Attach Image
with open('dashboard.png', 'rb') as f:
    img_data = f.read()
    msg.add_attachment(img_data, maintype='image', subtype='png', filename='dashboard.png')

# Send via Gmail
with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
    smtp.login(EMAIL_USER, EMAIL_PASS)
    smtp.send_message(msg)

print("✅ Mission Complete. Email Sent.")
