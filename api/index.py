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

# Data file configuration
DATA_FILE = 'revised_map_data.gpkg'
DATA_URL = "https://drive.google.com/uc?export=download&id=1ExK0Dn6SgEzhw9-gE9kOmHXKWIZ2TEHv"  # TODO: Replace with your actual link

def download_map_data():
    """Download the map data file if it doesn't exist"""
    if os.path.exists(DATA_FILE):
        print(f"{DATA_FILE} already exists")
        return DATA_FILE
    
    print(f"Downloading {DATA_FILE}...")
    try:
        response = requests.get(DATA_URL, stream=True, timeout=300)
        response.raise_for_status()
        
        with open(DATA_FILE, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"Downloaded {DATA_FILE}")
        return DATA_FILE
    except Exception as e:
        print(f"Failed to download data file: {e}")
        raise

# Download data on startup (Note: in serverless, this runs on cold start)
try:
    download_map_data()
except:
    print("Warning: Could not download map data on initialization")

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

    point = Point(longitude, latitude)  # Note: Point takes (x, y) = (lon, lat)
    gdf = gpd.read_file(DATA_FILE)
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
        hazard = None
    
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
        
        hazard, map_path = get_flood_hazard_from_ip(ip_address)
        current_map_path = map_path

        return jsonify({
            'hazard': hazard,
            'map_available': map_path is not None
        })
    except Exception as e:
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
