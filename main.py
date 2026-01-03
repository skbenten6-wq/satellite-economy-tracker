import os
import json
import ee
import requests
import urllib.request
from PIL import Image
import matplotlib.pyplot as plt
from google.oauth2.service_account import Credentials

# --- 1. AUTHENTICATION (ROBOT MODE) ---
try:
    service_account_info = json.loads(os.environ["EE_KEY"])
    
    # THE FIX: We must explicitly tell Google this is for "Earth Engine"
    credentials = Credentials.from_service_account_info(
        service_account_info, 
        scopes=['https://www.googleapis.com/auth/earthengine']
    )
    
    # Initialize Earth Engine with the Robot Key
    ee.Initialize(credentials=credentials, project="satellite-tracker-2026")
    print("✅ Robot Authentication Successful!")
except Exception as e:
    print(f"❌ Auth Failed: {e}")
    exit(1)

# --- 2. DEFINE TARGETS ---
targets = {
    "1. TATA STEEL": { "roi": [86.1950, 22.7950, 86.2050, 22.8050], "vis": {'bands': ['B12', 'B11', 'B4'], 'min': 0, 'max': 4000}, "desc": "Orange = Heat" },
    "2. NTPC DADRI": { "roi": [77.5500, 28.5900, 77.5700, 28.6100], "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000}, "desc": "Black = Inventory" },
    "3. BHADLA SOLAR": { "roi": [71.9000, 27.5300, 71.9400, 27.5600], "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000}, "desc": "Blue = Expansion" },
    "4. GRSE DOCK": { "roi": [88.2920, 22.5440, 88.2960, 22.5470], "vis": {'bands': ['B8', 'B4', 'B3'], 'min': 0, 'max': 3000}, "desc": "Grey = Work" },
    "5. GRSE JETTY": { "roi": [88.2960, 22.5390, 88.3020, 22.5430], "vis": {'bands': ['B8', 'B4', 'B3'], 'min': 0, 'max': 3000}, "desc": "Cyan = Fitting" },
    "6. RELIANCE OIL": { "roi": [69.8300, 22.3300, 69.9100, 22.3800], "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000}, "desc": "Shadows = Demand" },
    "7. MUNDRA PORT": { "roi": [69.6900, 22.7300, 69.7300, 22.7600], "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000}, "desc": "Dots = Ships" },
    "8. CONCOR RAIL": { "roi": [77.2880, 28.5200, 77.2980, 28.5300], "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000}, "desc": "Texture = Volume" },
    "9. JEWAR AIRPORT": { "roi": [77.6000, 28.1600, 77.6400, 28.1900], "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000}, "desc": "Grey = Progress" },
    "10. MARUTI YARD": { "roi": [76.9300, 28.3500, 76.9400, 28.3600], "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000}, "desc": "White = Unsold" },
    "11. BHAKRA DAM": { "roi": [76.4100, 31.3900, 76.4500, 31.4200], "vis": {'bands': ['B8', 'B4', 'B3'], 'min': 0, 'max': 3000}, "desc": "Black = Water" },
    "12. NAGARJUNA": { "roi": [79.2900, 16.5700, 79.3300, 16.6000], "vis": {'bands': ['B8', 'B4', 'B3'], 'min': 0, 'max': 3000}, "desc": "Black = Water" }
}

# --- 3. SCANNER ENGINE ---
def get_image_url(coords, vis):
    roi = ee.Geometry.Rectangle(coords)
    # Check Dec first, then Nov
    col = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(roi).filterDate('2024-12-01', '2025-01-04').filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)).sort('system:time_start', False)
    if col.size().getInfo() == 0:
        col = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(roi).filterDate('2024-11-01', '2025-01-04').sort('system:time_start', False)
    
    if col.size().getInfo() > 0:
        return col.first().getThumbURL({'min': vis['min'], 'max': vis['max'], 'bands': vis['bands'], 'region': roi, 'format': 'png', 'dimensions': 512})
    return None

# --- 4. EXECUTE & SAVE ---
print("🚀 Scanning & Saving...")
plt.figure(figsize=(18, 24))

for i, (name, data) in enumerate(targets.items()):
    url = get_image_url(data['roi'], data['vis'])
    plt.subplot(4, 3, i+1)
    if url:
        try:
            img = Image.open(urllib.request.urlopen(url))
            plt.imshow(img)
            plt.title(name, fontsize=12, fontweight='bold')
            plt.xlabel(data['desc'], fontsize=10)
        except:
            plt.text(0.5, 0.5, "Error", ha='center')
    else:
        plt.text(0.5, 0.5, "Cloudy", ha='center')
    plt.axis('off')

plt.tight_layout()
plt.savefig("dashboard.png") # Saves to virtual machine for email
print("✅ Dashboard saved!")
