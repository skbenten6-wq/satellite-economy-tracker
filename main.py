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
# 2. SECTOR TARGET LIST
# ==========================================
targets = {
    "TATA STEEL": { 
        "roi": [86.1950, 22.7950, 86.2050, 22.8050], 
        "vis": {'bands': ['B12', 'B11', 'B4'], 'min': 0, 'max': 4000},
        "query": "Tata Steel India production",
        "desc": "Heat Signature (Blast Furnace)"
    },
    "NTPC POWER": { 
        "roi": [77.5500, 28.5900, 77.5700, 28.6100], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000},
        "query": "NTPC coal supply India",
        "desc": "Coal Inventory Levels"
    },
    "ADANI PORTS": { 
        "roi": [69.6900, 22.7300, 69.7300, 22.7600], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000},
        "query": "Adani Ports Mundra cargo volume",
        "desc": "Export/Import Activity"
    },
    "RELIANCE IND": { 
        "roi": [69.8300, 22.3300, 69.9100, 22.3800], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000},
        "query": "Reliance Industries refinery margin",
        "desc": "Crude Oil Inventory"
    },
    "GRSE DEFENSE": { 
        "roi": [88.2960, 22.5390, 88.3020, 22.5430], 
        "vis": {'bands': ['B8', 'B4', 'B3'], 'min': 0, 'max': 3000},
        "query": "Garden Reach Shipbuilders delivery",
        "desc": "Naval Delivery Status"
    },
    "MARUTI SUZUKI": { 
        "roi": [76.9300, 28.3500, 76.9400, 28.3600], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000},
        "query": "Maruti Suzuki sales figures",
        "desc": "Vehicle Dispatch Yard"
    },
    "JEWAR AIRPORT": { 
        "roi": [77.6000, 28.1600, 77.6400, 28.1900], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000},
        "query": "Jewar Airport construction progress",
        "desc": "Infrastructure Progress"
    },
    "BHAKRA DAM": { 
        "roi": [76.4100, 31.3900, 76.4500, 31.4200], 
        "vis": {'bands': ['B8', 'B4', 'B3'], 'min': 0, 'max': 3000},
        "query": "Bhakra Dam water reservoir level",
        "desc": "Rural/Hydro Health"
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
        if count >= 2: break # Max 2 headlines per sector
        
        title = item.get('title', '')
        link = item.get('link', '')
        date = item.get('date', 'Recent')

        # Link Hygiene: Fix relative links
        if link.startswith("./"):
            link = f"https://news.google.com{link[1:]}"
        
        # Freshness Check: Green for <24h, Grey for older
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
        
    # Add Deep Search Link
    news_html += f"""<div style="margin-top:6px;"><a href="{safe_search}" style="font-size:11px; color:#3498db; text-decoration:none;">&rarr; Deep Search this Sector</a></div>"""
    
    return news_html

# ==========================================
# 4. REPORT GENERATION LOOP
# ==========================================
print("🚀 [SYSTEM] Initiating Daily Scan...")
html_report = """
<html>
<body style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f4f6f7; padding: 20px;">
    <div style="max-width: 800px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        
        <div style="background-color: #2c3e50; padding: 20px; text-align: center; color: #ffffff;">
            <h2 style="margin: 0; font-size: 24px; letter-spacing: 1px;">🛰️ SATELLITE ALPHA</h2>
            <p style="margin: 5px 0 0; font-size: 14px; opacity: 0.8;">Daily Strategic Intelligence Report</p>
