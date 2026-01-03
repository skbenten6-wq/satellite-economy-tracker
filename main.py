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

# Initialize News Engine
googlenews = GoogleNews(period='1d')
googlenews.set_lang('en')
googlenews.set_encode('utf-8')

# --- 2. DEFINE TARGETS ---
targets = {
    "1. TATA STEEL": { 
        "roi": [86.1950, 22.7950, 86.2050, 22.8050], 
        "vis": {'bands': ['B12', 'B11', 'B4'], 'min': 0, 'max': 4000},
        "query": "Tata Steel production India"
    },
    "2. NTPC POWER": { 
        "roi": [77.5500, 28.5900, 77.5700, 28.6100], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000},
        "query": "NTPC coal supply"
    },
    "3. ADANI PORTS": { 
        "roi": [69.6900, 22.7300, 69.7300, 22.7600], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000},
        "query": "Adani Ports cargo export"
    },
    "4. RELIANCE OIL": { 
        "roi": [69.8300, 22.3300, 69.9100, 22.3800], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000},
        "query": "Reliance Industries refinery"
    },
    "5. GRSE DEFENSE": { 
        "roi": [88.2960, 22.5390, 88.3020, 22.5430], 
        "vis": {'bands': ['B8', 'B4', 'B3'], 'min': 0, 'max': 3000},
        "query": "Garden Reach Shipbuilders"
    },
    "6. MARUTI AUTO": { 
        "roi": [76.9300, 28.3500, 76.9400, 28.3600], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000},
        "query": "Maruti Suzuki sales"
    },
     "7. JEWAR AIRPORT": { 
        "roi": [77.6000, 28.1600, 77.6400, 28.1900], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000},
        "query": "Noida International Airport construction"
    },
    "8. BHAKRA DAM": { 
        "roi": [76.4100, 31.3900, 76.4500, 31.4200], 
        "vis": {'bands': ['B8', 'B4', 'B3'], 'min': 0, 'max': 3000},
        "query": "Bhakra Dam water level"
    }
}

# --- 3. HELPER FUNCTIONS ---
def get_image_url(coords, vis):
    roi = ee.Geometry.Rectangle(coords)
    col = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(roi).filterDate('2024-12-01', '2025-01-04').filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)).sort('system:time_start', False)
    if col.size().getInfo() == 0:
        col = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(roi).filterDate('2024-11-01', '2025-01-04').sort('system:time_start', False)
    if col.size().getInfo() > 0:
        return col.first().getThumbURL({'min': vis['min'], 'max': vis['max'], 'bands': vis['bands'], 'region': roi, 'format': 'png', 'dimensions': 512})
    return None

def get_latest_news_html(query):
    googlenews.clear()
    googlenews.search(query)
    results = googlenews.result()
    
    html_items = ""
    for i in range(min(2, len(results))):
        title = results[i]['title']
        link = results[i]['link']
        
        # LINK CLEANER: Fix relative Google links
        if not link.startswith("http"):
            link = "https://" + link.lstrip("./")
            
        html_items += f"<li><a href='{link}' style='text-decoration:none; color:#1a0dab;'>{title}</a></li>"
    
    if not html_items:
        return "<li>No recent news found.</li>"
    return html_items

# --- 4. EXECUTION LOOP ---
print("🚀 Starting Intelligence Scan...")
plt.figure(figsize=(15, 12))

# Start the HTML Email Structure
html_body = """
<html>
  <body>
    <h2 style="color:#2c3e50;">🛰️ Daily Strategic Intelligence Report</h2>
    <p>Below is your combined Satellite & Open-Source Intelligence (OSINT) briefing.</p>
    <table style="width:100%; border-collapse: collapse;">
"""

for i, (name, data) in enumerate(targets.items()):
    # A. SATELLITE
    url = get_image_url(data['roi'], data['vis'])
    plt.subplot(3, 3, i+1)
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
    
    # B. NEWS (Generate HTML List)
    news_list_html = get_latest_news_html(data['query'])
    
    # C. ADD TO EMAIL TABLE
    html_body += f"""
      <tr style="border-bottom: 1px solid #eee;">
        <td style="padding: 10px; width: 30%;"><strong>{name}</strong></td>
        <td style="padding: 10px;">
          <ul style="margin: 0; padding-left: 20px; font-family: sans-serif; font-size: 14px;">
            {news_list_html}
          </ul>
        </td>
      </tr>
    """

# Close HTML
html_body += """
    </table>
    <br>
    <p style="color:gray; font-size:12px;">*Satellite imagery provided by Sentinel-2 (ESA) via Google Earth Engine.</p>
  </body>
</html>
"""

plt.tight_layout()
plt.savefig("dashboard.png")
print("✅ Dashboard Generated.")

# --- 5. SEND EMAIL (HTML MODE) ---
print("📧 Sending Dispatch...")

msg = EmailMessage()
msg['Subject'] = f"Daily Intel: Satellite + News ({datetime.now().strftime('%Y-%m-%d')})"
msg['From'] = "Satellite Bot"
msg['To'] = EMAIL_USER

# Set the email content to HTML
msg.add_alternative(html_body, subtype='html')

# Attach Image
with open('dashboard.png', 'rb') as f:
    img_data = f.read()
    msg.add_attachment(img_data, maintype='image', subtype='png', filename='dashboard.png')

with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
    smtp.login(EMAIL_USER, EMAIL_PASS)
    smtp.send_message(msg)

print("✅ Mission Complete. HTML Email Sent.")
