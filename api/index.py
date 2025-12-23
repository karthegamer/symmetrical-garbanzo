"""
Flask Flood Hazard Server - Vercel Serverless Function

Adapted for Vercel deployment as a serverless function.
"""
from flask import Flask, render_template, request, jsonify, send_file
import os
import requests
import geopandas as gpd
from shapely.geometry import Point

app = Flask(__name__)

# Store the current map path
current_map_path = None

# Cache the GeoDataFrame in memory to avoid re-reading on every request
cached_gdf = None

# Data file configuration - use /tmp for Vercel serverless
DATA_FILE = os.path.join('/tmp', 'revised_map_data.gpkg')
DATA_URL = "https://drive.google.com/uc?export=download&id=1ExK0Dn6SgEzhw9-gE9kOmHXKWIZ2TEHv"

def download_and_load_map_data():
    """Download the map data file if it doesn't exist and load it into memory"""
    global cached_gdf
    
    # If already cached, return immediately
    if cached_gdf is not None:
        print("Using cached GeoDataFrame")
        return cached_gdf
    
    # Ensure /tmp directory exists
    os.makedirs('/tmp', exist_ok=True)
    
    # Download if file doesn't exist
    if not os.path.exists(DATA_FILE):
        print(f"Downloading {DATA_FILE}...")
        try:
            response = requests.get(DATA_URL, stream=True, timeout=300)
            response.raise_for_status()
            
            with open(DATA_FILE, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"Downloaded {DATA_FILE}")
        except Exception as e:
            print(f"Failed to download data file: {e}")
            raise
    else:
        print(f"{DATA_FILE} already exists")
    
    # Load into memory and cache
    print("Loading GeoDataFrame into memory...")
    cached_gdf = gpd.read_file(DATA_FILE)
    print(f"GeoDataFrame cached with {len(cached_gdf)} features")
    return cached_gdf

# Load data on startup (Note: in serverless, this runs on cold start)
try:
    download_and_load_map_data()
except Exception as e:
    print(f"Warning: Could not load map data on initialization: {e}")

def get_flood_hazard_from_ip(ip_address):
    """
    Get flood hazard information based on IP address
    Returns: (hazard_string, map_path)
    """
    try:
        geo_url = f"https://get.geojs.io/v1/ip/geo/{ip_address}.json" if ip_address else "https://get.geojs.io/v1/ip/geo.json"
        geo_resp = requests.get(geo_url, timeout=5)
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()
    except Exception as exc:
        print(f"Failed to get location details: {exc}")
        return None, None

    latitude = geo_data.get("latitude")
    longitude = geo_data.get("longitude")
    
    if not latitude or not longitude:
        print("Could not determine coordinates from IP")
        return None, None

    point = Point(longitude, latitude)  # Note: Point takes (x, y) = (lon, lat)
    
    # Use cached GeoDataFrame instead of reading from disk every time
    gdf = download_and_load_map_data()
    if gdf is None:
        print("GeoDataFrame not available")
        return None, None
    
    # Create a GeoDataFrame from the point with the same CRS
    point_gdf = gpd.GeoDataFrame([{'geometry': point}], crs='EPSG:4326')

    # Ensure both are in the same CRS
    if point_gdf.crs != gdf.crs:
        point_gdf = point_gdf.to_crs(gdf.crs)

    # Perform spatial join to find which polygon contains the point
    result = gpd.sjoin(point_gdf, gdf[['geometry', 'SOIL_FLOOD_HAZARD']],
                       how='left', predicate='within')

    if len(result) > 0 and not result['SOIL_FLOOD_HAZARD'].isna().all():
        hazard = result['SOIL_FLOOD_HAZARD'].iloc[0]
    else:
        hazard = "No flood hazard data for this location"
    
    return hazard, current_map_path


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/check_flood_hazard')
def check_flood_hazard():
    global current_map_path

    try:
        # Get real IP from Vercel headers
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ip_address:
            ip_address = ip_address.split(',')[0].strip()
        
        print(f"Checking flood hazard for IP: {ip_address}")
        
        hazard, map_path = get_flood_hazard_from_ip(ip_address)
        current_map_path = map_path
        
        if hazard is None:
            return jsonify({
                'error': 'Could not determine flood hazard for your location',
                'hazard': 'Unknown',
                'map_available': False
            }), 200

        return jsonify({
            'hazard': hazard,
            'map_available': map_path is not None
        })
    except Exception as e:
        print(f"Error in check_flood_hazard: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/map')
def serve_map():
    global current_map_path

    if current_map_path and os.path.exists(current_map_path):
        return send_file(current_map_path, mimetype='image/png')
    else:
        return "Map not found", 404


# Vercel serverless function handler
def handler(request):
    """Handler for Vercel serverless deployment"""
    with app.app_context():
        return app.full_dispatch_request()
