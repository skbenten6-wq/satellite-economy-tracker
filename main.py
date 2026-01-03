import os
import requests
import matplotlib.pyplot as plt
from io import BytesIO
from PIL import Image

# --- 1. CONFIGURATION ---
# Checks if running on GitHub Actions (Environment Variables)
# If running locally, you must set these variables or replace them manually here.
if "SH_CLIENT_ID" in os.environ:
    CLIENT_ID = os.environ["SH_CLIENT_ID"]
    CLIENT_SECRET = os.environ["SH_CLIENT_SECRET"]
else:
    # FALLBACK FOR LOCAL TESTING (Replace with your actual keys if running on PC/Colab)
    CLIENT_ID = "YOUR_CLIENT_ID_HERE"
    CLIENT_SECRET = "YOUR_CLIENT_SECRET_HERE"

# THE "MACRO-ECONOMY" BASKET (8 TARGETS)
TARGETS = {
    # --- ROW 1: HEAVY INDUSTRY (Foundation) ---
    "1. TATA STEEL: Jamshedpur (Production)": {
        "bbox": [86.1950, 22.7950, 86.2050, 22.8050],
        "mode": "HEAT_MAP",
        "desc": "Orange/Red Spots = Active Blast Furnaces"
    },
    "2. NTPC DADRI: Coal Piles (Power)": {
        "bbox": [77.5500, 28.5900, 77.5700, 28.6100],
        "mode": "TRUE_COLOR",
        "desc": "Black Mounds = Coal Inventory (Size change)"
    },

    # --- ROW 2: DEFENSE & OIL (High Value) ---
    "3. GRSE: Dry Dock (Ship Construction)": {
        "bbox": [88.2920, 22.5440, 88.2960, 22.5470],
        "mode": "INFRARED", 
        "desc": "Grey Block in Notch = Work in Progress"
    },
    "4. RELIANCE: Jamnagar (Oil Storage)": {
        "bbox": [69.8300, 22.3300, 69.9100, 22.3800],
        "mode": "TRUE_COLOR",
        "desc": "Black Crescents = Empty Tanks (High Demand)"
    },
    
    # --- ROW 3: LOGISTICS (Movement) ---
    "5. CONCOR: Tughlakabad (Imports/Exports)": {
        "bbox": [77.2880, 28.5200, 77.2980, 28.5300],
        "mode": "TRUE_COLOR",
        "desc": "Colorful Texture = Container Volume"
    },
    "6. GRSE: FOJ Jetty (Delivery Status)": {
        "bbox": [88.2960, 22.5390, 88.3020, 22.5430],
        "mode": "INFRARED",
        "desc": "Thick Cyan Blob = Ship Fitting Out"
    },

    # --- ROW 4: CONSUMPTION (End User) ---
    "7. MARUTI: Manesar Yard (Auto Sales)": {
        "bbox": [76.9300, 28.3500, 76.9400, 28.3600],
        "mode": "TRUE_COLOR", 
        "desc": "Bright/White = High Unsold Inventory"
    },
    "8. NAGARJUNA SAGAR: Dam (Rural Demand)": {
        "bbox": [79.2900, 16.5700, 79.3300, 16.6000], 
        "mode": "INFRARED", 
        "desc": "Black Area = Water Level (Rural Health)"
    }
}

# --- 2. AUTHENTICATION ---
def get_token(id, secret):
    token_url = "https://services.sentinel-hub.com/oauth/token"
    payload = {"grant_type": "client_credentials"}
    try:
        response = requests.post(token_url, data=payload, auth=(id, secret))
        response.raise_for_status()
        return response.json()['access_token']
    except Exception as e:
        print(f"❌ Auth Failed: {e}")
        return None

# --- 3. THE SMART REQUEST ENGINE ---
def get_image(token, target_config):
    api_url = "https://services.sentinel-hub.com/api/v1/process"
    mode = target_config["mode"]
    
    # DYNAMIC EVALSCRIPTS (The Logic for Satellite Filters)
    if mode == "INFRARED":
        # Best for Water/Land/Metal separation
        # B08(NIR)=Red, B04(Red)=Green, B03(Green)=Blue
        script = """
        //VERSION=3
        function setup() { return { input: ["B08", "B04", "B03"], output: { bands: 3 } }; }
        function evaluatePixel(sample) { return [sample.B08 * 2.5, sample.B04 * 2.5, sample.B03 * 2.5]; }
        """
    elif mode == "TRUE_COLOR":
        # Standard visual photograph (Enhanced Brightness)
        script = """
        //VERSION=3
        function setup() { return { input: ["B04", "B03", "B02"], output: { bands: 3 } }; }
        function evaluatePixel(sample) { return [sample.B04 * 3.0, sample.B03 * 3.0, sample.B02 * 3.0]; }
        """
    elif mode == "HEAT_MAP":
        # Short-Wave Infrared to detect Extreme Heat
        script = """
        //VERSION=3
        function setup() { return { input: ["B12", "B11", "B04"], output: { bands: 3 } }; }
        function evaluatePixel(sample) {
            // High B12 (Heat) makes the pixel Red/Orange
            return [sample.B12 * 2.5, sample.B11 * 1.5, sample.B04 * 1]; 
        }
        """

    payload = {
        "input": {
            "bounds": {"bbox": target_config["bbox"], "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}},
            "data": [{
                "type": "sentinel-2-l2a",
                # Scan last 30 days to find a clear image (Cloud filtering)
                # Note: Adjust the 'from' date if needed to ensure recent data
                "dataFilter": {"timeRange": {"from": "2025-12-04T00:00:00Z", "to": "2026-01-03T23:59:59Z"}, "maxCloudCoverage": 10}
            }]
        },
        "output": {"width": 512, "height": 512, "responses": [{"identifier": "default", "format": {"type": "image/png"}}]},
        "evalscript": script
    }

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        response = requests.post(api_url, json=payload, headers=headers)
        if response.status_code == 200:
            return Image.open(BytesIO(response.content))
        else:
            print(f"⚠️ API Error for target: {response.text}")
            return None
    except Exception as e:
        print(f"⚠️ Connection Error: {e}")
        return None

# --- 4. EXECUTE DASHBOARD (4 Rows x 2 Columns) ---
token = get_token(CLIENT_ID, CLIENT_SECRET)

if token:
    print("🚀 Starting Satellite Scan...")
    plt.figure(figsize=(15, 20)) # Tall layout for 8 images
    
    for i, (name, config) in enumerate(TARGETS.items()):
        print(f"Scanning: {name}...")
        img = get_image(token, config)
        
        plt.subplot(4, 2, i+1) # 4 Rows, 2 Columns
        if img:
            plt.imshow(img)
            plt.title(f"{name}", fontsize=12, fontweight='bold')
            plt.xlabel(config['desc'], fontsize=10)
            plt.xticks([])
            plt.yticks([])
        else:
            plt.text(0.5, 0.5, "Image Failed (Clouds/Error)", ha='center')
            plt.title(name)
            
    plt.tight_layout()
    plt.savefig("dashboard.png") 
    print("✅ DASHBOARD COMPLETE: Saved as 'dashboard.png'")
else:
    print("❌ Authentication Failed. Check Client ID/Secret.")
