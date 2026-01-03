import os
import json
import ee
import smtplib
import requests
import urllib.request
import urllib.parse
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
        "query": "Tata Steel India production"
    },
    "2. NTPC POWER": { 
        "roi": [77.5500, 28.5900, 77.5700, 28.6100], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000},
        "query": "NTPC coal supply India"
    },
    "3. ADANI PORTS": { 
        "roi": [69.6900, 22.7300, 69.7300, 22.7600], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000},
        "query": "Adani Ports Mundra cargo"
    },
    "4. RELIANCE OIL": { 
        "roi": [69.8300, 22.3300, 69.9100, 22.3800], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000},
        "query": "Reliance Industries Jamnagar refinery"
    },
    "5. GRSE DEFENSE": { 
        "roi": [88.2960, 22.5390, 88.3020, 22.5430], 
        "vis": {'bands': ['B8', 'B4', 'B3'], 'min': 0, 'max': 3000},
        "query": "Garden Reach Shipbuilders"
    },
    "6. MARUTI AUTO": { 
        "roi": [76.9300, 28.3500, 76.9400, 28.3600], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000},
        "query": "Maruti Suzuki Manesar production"
    },
     "7. JEWAR AIRPORT": { 
        "roi": [77.6000, 28.1600, 77.6400, 28.1900], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000},
        "query": "Jewar Airport construction updates"
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
    # Check Dec first, then Nov (Fallback)
    col = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(roi).filterDate('2024-12-01', '2025-01-04').filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)).sort('system:time_start', False)
    if col.size().getInfo() == 0:
        col = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(roi).filterDate('2024-11-01', '2025-01-04').sort('system:time_start', False)
    
    if col.size().getInfo() > 0:
        return col.first().getThumbURL({'min': vis['min'], 'max': vis['max'], 'bands': vis['bands'], 'region': roi, 'format': 'png', 'dimensions': 512})
    return None

def get_news_html(query):
    googlenews.clear()
    googlenews.search(query)
    results = googlenews.result()
    
    # 1. Create the "Safety Link" (Always works)
    safe_search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&tbm=nws"
    
    html_items = ""
    count = 0
    
    # 2. Add Top 2 Articles
    for item in results:
        if count >= 2: break
        title = item.get('title', 'No Title')
        link = item.get('link', '')
        
        # LINK FIXER: Repair broken Google links
        if link.startswith("./"):
            link = f"https://news.google.com{link[1:]}"
            
        # If link looks suspicious, skip it or use search
        if "http" not in link:
            continue
            
        html_items += f"<li><a href='{link}' style='text-decoration:none; color:#1a0dab;'>{title}</a></li>"
        count += 1
    
    # 3. Add the "See All" Safety Button at the bottom
    html_items += f"<li style='margin-top:5px;'><a href='{safe_search_url}' style='color:#007bff; font-weight:bold; font-size:12px;'>👉 See all news results for this sector</a></li>"
    
    return html_items

# --- 4. EXECUTION LOOP ---
print("🚀 Starting Intelligence Scan...")
plt.figure(figsize=(15, 12))

# Start HTML Email
html_body = """
<html>
  <body style="font-family: Arial, sans-serif; color:#333;">
    <h2 style="color:#2c3e50; border-bottom: 2px solid #2c3e50; padding-bottom: 10px;">🛰️ Daily Strategic Intelligence</h2>
    <p><strong>Status:</strong> Systems Nominal | <strong>Source:</strong> Sentinel-2 & Google Earth Engine</p>
    <table style="width:100%; border-collapse: collapse;">
"""

for i, (name, data) in enumerate(targets.items()):
    print(f"Scanning {name}...")
    # A. SATELLITE IMAGE
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
    
    # B. NEWS FETCH
    news_html = get_news_html(data['query'])
    
    # C. ADD TO EMAIL TABLE
    html_body += f"""
      <tr style="border-bottom: 1px solid #ddd;">
        <td style="padding: 15px; width: 30%; vertical-align: top; background-color: #f9f9f9;">
            <strong style="font-size:16px; color:#2c3e50;">{name}</strong>
        </td>
        <td style="padding: 15px; vertical-align: top;">
          <ul style="margin: 0; padding-left: 20px; font-size: 14px; line-height: 1.6;">
            {news_html}
          </ul>
        </td>
      </tr>
    """

# Close HTML
html_body += """
    </table>
    <br>
    <div style="font-size:12px; color:#777; text-align:center;">
        Generated automatically by GitHub Actions | Python | Earth Engine
    </div>
  </body>
</html>
"""

plt.tight_layout()
plt.savefig("dashboard.png")
print("✅ Dashboard Generated.")

# --- 5. SEND EMAIL ---
print("📧 Sending Dispatch...")
msg = EmailMessage()
msg['Subject'] = f"Daily Intel Report: {datetime.now().strftime('%d %b %Y')}"
msg['From'] = "Satellite Bot"
msg['To'] = EMAIL_USER

# Set HTML Content
msg.add_alternative(html_body, subtype='html')

# Attach Dashboard Image
with open('dashboard.png', 'rb') as f:
    img_data = f.read()
    msg.add_attachment(img_data, maintype='image', subtype='png', filename='dashboard.png')

with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
    smtp.login(EMAIL_USER, EMAIL_PASS)
    smtp.send_message(msg)

print("✅ Mission Complete. HTML Email Sent.")
