import requests
import matplotlib.pyplot as plt
from io import BytesIO
from PIL import Image

import os

# --- 1. CONFIGURATION (UPDATED FOR AUTOMATION) ---
# This reads the keys from GitHub's secure vault
CLIENT_ID = os.environ["SH_CLIENT_ID"]
CLIENT_SECRET = os.environ["SH_CLIENT_SECRET"]

# ... (Keep the rest of the script exactly the same) ...

# DEFINING THE "GRAND MASTER" BASKET (4 TARGETS)
TARGETS = {
    # --- ROW 1: DEFENSE (GRSE) ---
    "1. GRSE: Dry Dock (Construction)": {
        "bbox": [88.2920, 22.5440, 88.2960, 22.5470],
        "mode": "INFRARED", 
        "desc": "Grey Block = Work in Progress"
    },
    "2. GRSE: FOJ Jetty (Delivery)": {
        "bbox": [88.2960, 22.5390, 88.3020, 22.5430],
        "mode": "INFRARED",
        "desc": "Cyan Bar = Ship Fitting Out"
    },
    
    # --- ROW 2: ECONOMY (Logistics & Steel) ---
    "3. CONCOR: Tughlakabad (Logistics)": {
        "bbox": [77.2880, 28.5200, 77.2980, 28.5300],
        "mode": "TRUE_COLOR",
        "desc": "Texture/Dots = Containers"
    },
    "4. TATA STEEL: Jamshedpur (Mfg)": {
        "bbox": [86.1950, 22.7950, 86.2050, 22.8050],
        "mode": "HEAT_MAP",
        "desc": "Orange Spots = Active Furnaces"
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
    except Exception:
        return None

# --- 3. THE SMART REQUEST ENGINE ---
def get_image(token, target_config):
    api_url = "https://services.sentinel-hub.com/api/v1/process"
    mode = target_config["mode"]
    
    # DYNAMIC EVALSCRIPTS
    if mode == "INFRARED":
        # Sharp Metal/Water contrast
        script = """
        //VERSION=3
        function setup() { return { input: ["B08", "B04", "B03"], output: { bands: 3 } }; }
        function evaluatePixel(sample) { return [sample.B08 * 2.5, sample.B04 * 2.5, sample.B03 * 2.5]; }
        """
    elif mode == "TRUE_COLOR":
        # Real colors
        script = """
        //VERSION=3
        function setup() { return { input: ["B04", "B03", "B02"], output: { bands: 3 } }; }
        function evaluatePixel(sample) { return [sample.B04 * 2.5, sample.B03 * 2.5, sample.B02 * 2.5]; }
        """
    elif mode == "HEAT_MAP":
        # Heat (SWIR)
        script = """
        //VERSION=3
        function setup() { return { input: ["B12", "B11", "B04"], output: { bands: 3 } }; }
        function evaluatePixel(sample) {
            return [sample.B12 * 2.5, sample.B11 * 1.5, sample.B04 * 1]; 
        }
        """

    payload = {
        "input": {
            "bounds": {"bbox": target_config["bbox"], "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}},
            "data": [{
                "type": "sentinel-2-l2a",
                "dataFilter": {"timeRange": {"from": "2025-11-15T00:00:00Z", "to": "2026-01-03T23:59:59Z"}, "maxCloudCoverage": 10}
            }]
        },
        "output": {"width": 512, "height": 512, "responses": [{"identifier": "default", "format": {"type": "image/png"}}]},
        "evalscript": script
    }

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    response = requests.post(api_url, json=payload, headers=headers)
    return Image.open(BytesIO(response.content)) if response.status_code == 200 else None

# ... (Previous code remains the same) ...

# --- 4. EXECUTE DASHBOARD (2x2 GRID) ---
token = get_token(CLIENT_ID, CLIENT_SECRET)

if token:
    plt.figure(figsize=(12, 12)) 
    
    for i, (name, config) in enumerate(TARGETS.items()):
        print(f"Scanning {name}...")
        img = get_image(token, config)
        
        plt.subplot(2, 2, i+1)
        if img:
            plt.imshow(img)
            plt.title(f"{name}", fontsize=10, fontweight='bold')
            plt.xlabel(config['desc'], fontsize=9)
            plt.xticks([])
            plt.yticks([])
        else:
            plt.text(0.5, 0.5, "Image Failed", ha='center')
            plt.title(name)
            
    plt.tight_layout()
    
    # CHANGE: Save to file instead of just showing
    plt.savefig("dashboard.png") 
    print("✅ Dashboard saved as dashboard.png")
else:
    print("❌ Auth Failed")
