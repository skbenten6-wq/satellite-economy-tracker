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
import yfinance as yf

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
# 2. TARGET LIST (CORRECTED TICKERS)
# ==========================================
targets = {
    "1. COAL INDIA (Gevra Mine)": { 
        "roi": [82.5600, 22.3100, 82.6000, 22.3500], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000}, 
        "query": "Coal India production", 
        "desc": "Pit Expansion",
        "ticker": "COALINDIA.NS" 
    },
    "2. NMDC (Bailadila Iron)": { 
        "roi": [81.2000, 18.6600, 81.2400, 18.7000], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000}, 
        "query": "NMDC iron ore prices", 
        "desc": "Red Ore Piles",
        "ticker": "NMDC.NS" 
    },
    "3. RELIANCE (Oil Storage)": { 
        "roi": [69.8300, 22.3300, 69.9100, 22.3800], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000}, 
        "query": "Crude oil inventory India", 
        "desc": "Tank Farm Levels",
        "ticker": "RELIANCE.NS" 
    },
    "4. TATA STEEL (Jamshedpur)": { 
        "roi": [86.1950, 22.7950, 86.2050, 22.8050], 
        "vis": {'bands': ['B12', 'B11', 'B4'], 'min': 0, 'max': 4000}, 
        "query": "Tata Steel India production", 
        "desc": "Blast Furnace Heat",
        "ticker": "TATASTEEL.NS" 
    },
    "5. HINDALCO (Copper Dahej)": { 
        "roi": [72.5300, 21.6900, 72.5600, 21.7200], 
        "vis": {'bands': ['B12', 'B11', 'B4'], 'min': 0, 'max': 4000}, 
        "query": "Copper prices India demand", 
        "desc": "Smelter Activity",
        "ticker": "HINDALCO.NS" 
    },
    "6. ULTRATECH (Aditya Cement)": { 
        "roi": [74.6000, 24.7800, 74.6400, 24.8200], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000}, 
        "query": "Cement demand India", 
        "desc": "Grey Dust & Quarry",
        "ticker": "ULTRACEMCO.NS" # <-- FIXED TICKER
    },
    "7. ADANI PORTS (Mundra)": { 
        "roi": [69.6900, 22.7300, 69.7300, 22.7600], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000}, 
        "query": "Adani Ports cargo volume", 
        "desc": "Ships at Dock",
        "ticker": "ADANIPORTS.NS" 
    },
    "8. CONCOR (Delhi Depot)": { 
        "roi": [77.2880, 28.5200, 77.2980, 28.5300], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000}, 
        "query": "Container Corp volume", 
        "desc": "Container Density",
        "ticker": "CONCOR.NS" 
    },
    "9. MARUTI (Manesar Yard)": { 
        "roi": [76.9300, 28.3500, 76.9400, 28.3600], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000}, 
        "query": "Maruti Suzuki sales", 
        "desc": "Car Inventory",
        "ticker": "MARUTI.NS" 
    },
    "10. JEWAR AIRPORT (Const.)": { 
        "roi": [77.6000, 28.1600, 77.6400, 28.1900], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000}, 
        "query": "Jewar Airport status", 
        "desc": "Construction Progress",
        "ticker": "GMRAIRPORT.NS" # <-- FIXED TICKER
    },
    "11. BHADLA SOLAR (Energy)": { 
        "roi": [71.9000, 27.5300, 71.9400, 27.5600], 
        "vis": {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000}, 
        "query": "India solar capacity", 
        "desc": "Panel Expansion",
        "ticker": None 
    },
    "12. BHAKRA DAM (Hydro)": { 
        "roi": [76.4100, 31.3900, 76.4500, 31.4200], 
        "vis": {'bands': ['B8', 'B4', 'B3'], 'min': 0, 'max': 3000}, 
        "query": "Monsoon rainfall India", 
        "desc": "Water Level",
        "ticker": None 
    }
}

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
def get_valuation_data(ticker):
    """Fetches live market data and determines valuation status."""
    if not ticker:
        return {"price": "N/A", "pe": "N/A", "change": "N/A", "signal": "N/A", "color": "black"}
    
    try:
        stock = yf.Ticker(ticker)
        # Using fast_info sometimes is safer for prices, but .info is standard
        info = stock.info 
        
        # Safe Fetching
        current_price = info.get('currentPrice', 0)
        if current_price == 0: # Fallback
             current_price = info.get('regularMarketPreviousClose', 0)

        pe_ratio = info.get('trailingPE', 0)
        
        # Calculate 1-Month Return
        hist = stock.history(period="1mo")
        if not hist.empty:
            start_price = hist['Close'].iloc[0]
            change_pct = ((current_price - start_price) / start_price) * 100
        else:
            change_pct = 0
            
        # VALUATION LOGIC ENGINE
        signal = "NEUTRAL"
        color = "gray"
        
        if pe_ratio > 0:
            if pe_ratio < 15 and change_pct < 10:
                signal = "VALUE BUY"
                color = "green"
            elif pe_ratio > 40:
                signal = "OVERVALUED"
                color = "red"
            elif change_pct > 15:
                signal = "HEATED"
                color = "orange"
        
        return {
            "price": f"Rs. {current_price}", # <-- FIXED: No Rupee Symbol
            "pe": f"{pe_ratio:.1f}x",
            "change": f"{change_pct:+.1f}%",
            "signal": signal,
            "color": color
        }
    except:
        return {"price": "Error", "pe": "-", "change": "-", "signal": "Error", "color": "red"}

def get_satellite_data(coords, vis, filename):
    roi = ee.Geometry.Rectangle(coords)
    col = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(roi).filterDate('2024-12-01', '2025-01-04').filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)).sort('system:time_start', False)
    if col.size().getInfo() == 0:
        col = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(roi).filterDate('2024-11-01', '2025-01-04').sort('system:time_start', False)
    
    if col.size().getInfo() > 0:
        url = col.first().getThumbURL({'min': vis['min'], 'max': vis['max'], 'bands': vis['bands'], 'region': roi, 'format': 'png', 'dimensions': 600})
        try:
            urllib.request.urlretrieve(url, filename)
            return url, True
        except: return url, False
    return None, False

def get_market_news(query):
    googlenews.clear()
    googlenews.search(query)
    results = googlenews.result()
    news_data = []
    for item in results[:2]:
        title = item.get('title', '')
        link = item.get('link', '')
        date = item.get('date', 'Recent')
        if link.startswith("./"): link = f"https://news.google.com{link[1:]}"
        
        # Clean Title for PDF (Fix Encoding)
        clean_title = title.encode('ascii', 'ignore').decode('ascii') 
        
        if "http" in link: news_data.append({'title': clean_title, 'link': link, 'date': date})
    if not news_data:
        safe_link = f"https://www.google.com/search?q={urllib.parse.quote(query)}&tbm=nws"
        news_data.append({'title': "No fresh news. Click to Search.", 'link': safe_link, 'date': "N/A"})
    return news_data

# ==========================================
# 4. REPORT GENERATION
# ==========================================
print("🚀 [SYSTEM] Generating Financial Intelligence Report...")

pdf = FPDF()
pdf.set_auto_page_break(auto=True, margin=15)

html_report = """
<html>
<body style="font-family: Arial, sans-serif; background-color: #f4f6f7; padding: 20px;">
    <div style="max-width: 900px; margin: 0 auto; background-color: white; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); overflow: hidden;">
        <div style="background-color: #2c3e50; padding: 20px; text-align: center; color: white;">
            <h2 style="margin:0;">SUPPLY CHAIN ALPHA +</h2>
            <p style="margin:5px; font-size:12px;">Satellite • News • Valuation</p>
        </div>
        <table style="width:100%; border-collapse: collapse;">
"""

for i, (name, data) in enumerate(targets.items()):
    print(f"   ...Analyzing: {name}")
    
    # 1. FETCH DATA
    img_filename = f"sector_{i}.png"
    img_url, has_image = get_satellite_data(data['roi'], data['vis'], img_filename)
    news_items = get_market_news(data['query'])
    val_data = get_valuation_data(data['ticker'])
    
    # 2. BUILD HTML ROW
    news_html = ""
    for n in news_items:
        color = "green" if "ago" in n['date'] else "gray"
        news_html += f"<div style='margin-bottom:4px; font-size:11px;'><span style='color:{color};'>[{n['date']}]</span> <a href='{n['link']}' style='text-decoration:none; color:#2980b9;'>{n['title']}</a></div>"

    html_report += f"""
    <tr style="border-bottom: 1px solid #eee;">
        <td style="width: 35%; padding: 15px; background-color: #fafafa;">
            <div style="font-size:13px; font-weight:800; color:#2c3e50;">{name}</div>
            <div style="font-size:10px; color:#e67e22; margin-bottom:5px;">Strategy: {data['desc']}</div>
            <img src="{img_url}" style="width:100%; border-radius:4px;">
        </td>
        <td style="width: 45%; padding: 15px; vertical-align:top; border-right:1px solid #eee;">
            <div style="font-size:10px; font-weight:bold; color:#7f8c8d; margin-bottom:5px;">INTEL FEED</div>
            {news_html}
        </td>
        <td style="width: 20%; padding: 15px; vertical-align:top; background-color: #fdfdfd;">
            <div style="font-size:10px; font-weight:bold; color:#7f8c8d; margin-bottom:5px;">MARKET DATA</div>
            <div style="font-size:18px; font-weight:bold; color:#333;">{val_data['price']}</div>
            <div style="font-size:11px; color:#555;">P/E: {val_data['pe']}</div>
            <div style="font-size:11px; color:#555;">1M: {val_data['change']}</div>
            <div style="margin-top:8px; padding:4px; background-color:{val_data['color']}; color:white; font-size:10px; font-weight:bold; text-align:center; border-radius:3px;">
                {val_data['signal']}
            </div>
        </td>
    </tr>
    """

    # 3. BUILD PDF PAGE
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    
    # Ensure name is PDF safe
    clean_name = name.encode('ascii', 'ignore').decode('ascii')
    pdf.cell(0, 10, f"{clean_name}", ln=True)
    
    # Valuation Line in PDF (Using Rs. instead of Symbol)
    pdf.set_font("Arial", "B", 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, f"Price: {val_data['price']} | P/E: {val_data['pe']} | Signal: {val_data['signal']}", ln=True)
    
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(0, 0, 255)
    for n in news_items:
        pdf.cell(0, 8, f"[{n['date']}] {n['title']}", ln=True, link=n['link'])
    
    pdf.ln(5)
    if has_image: pdf.image(img_filename, x=10, w=190)

# FINALIZE
html_report += "</table></div></body></html>"
pdf.output("Financial_Intel_Report.pdf")
print("✅ Report Generated.")

# SEND EMAIL
print("📧 Sending Dispatch...")
msg = EmailMessage()
msg['Subject'] = f"Supply Chain Alpha +: {datetime.now().strftime('%d %b')}"
msg['From'] = "Satellite Bot"
msg['To'] = EMAIL_USER
msg.add_alternative(html_report, subtype='html')

with open("Financial_Intel_Report.pdf", 'rb') as f:
    msg.add_attachment(f.read(), maintype='application', subtype='pdf', filename="Financial_Intel_Report.pdf")

with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
    smtp.login(EMAIL_USER, EMAIL_PASS)
    smtp.send_message(msg)
print("✅ Sent.")
