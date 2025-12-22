"""
Flask Flood Hazard Server

Project Structure:
flood_app/
├── app.py (this file)
├── templates/
│   └── index.html
└── static/ (optional, for CSS/JS)

"""
from flask import Flask, render_template, request, jsonify, send_file
import os
import requests
import geopandas as gpd
from shapely.geometry import Point
import pandas
app = Flask(__name__)

# Store the current map path
current_map_path = None

# Data file configuration
DATA_FILE = 'revised_map_data.gpkg'
DATA_URL = "YOUR_GOOGLE_DRIVE_DIRECT_LINK_HERE"  # TODO: Replace with your actual link

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

# Download data on startup
download_map_data()

# Your function - replace with actual import
# from your_module import get_flood_hazard_from_ip

def get_flood_hazard_from_ip(ip_address):
    """
    Placeholder - replace with your actual function
    Returns: (hazard_string, map_path)
    """
    try:
      geo_url = f"https://get.geojs.io/v1/ip/geo/{ip_address}.json" if ip_address else "https://get.geojs.io/v1/ip/geo.json"
      geo_resp = requests.get(geo_url, timeout=5)
      geo_resp.raise_for_status()
      geo_data = geo_resp.json()
    except Exception as exc:  # pylint: disable=broad-except
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
        ip_address = request.remote_addr
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


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)


# templates/index.html file:
"""
<!DOCTYPE html>
<html>
<head>
    <title>Flood Hazard Checker</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            text-align: center;
        }
        button {
            background-color: #4CAF50;
            color: white;
            padding: 15px 32px;
            font-size: 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            margin: 20px 0;
        }
        button:hover {
            background-color: #45a049;
        }
        button:disabled {
            background-color: #cccccc;
            cursor: not-allowed;
        }
        #results {
            margin-top: 30px;
        }
        #hazard-text {
            font-size: 24px;
            font-weight: bold;
            margin: 20px 0;
            color: #333;
        }
        #map-image {
            max-width: 100%;
            height: auto;
            margin-top: 20px;
            border: 2px solid #ddd;
            border-radius: 4px;
        }
        .loading {
            color: #666;
            font-style: italic;
        }
    </style>
</head>
<body>
    <h1>Flood Hazard Checker</h1>
    <p>Check the flood hazard level for your location</p>

    <button id="checkButton" onclick="getFloodHazard()">Get Flood Hazard</button>

    <div id="results" style="display: none;">
        <div id="hazard-text"></div>
        <img id="map-image" src="" alt="Flood hazard map">
    </div>

    <script>
        async function getFloodHazard() {
            const button = document.getElementById('checkButton');
            const results = document.getElementById('results');
            const hazardText = document.getElementById('hazard-text');
            const mapImage = document.getElementById('map-image');

            button.disabled = true;
            button.textContent = 'Loading...';
            hazardText.textContent = 'Analyzing your location...';
            hazardText.className = 'loading';
            results.style.display = 'block';
            mapImage.style.display = 'none';

            try {
                const response = await fetch('/check_flood_hazard');
                const data = await response.json();

                if (data.error) {
                    hazardText.textContent = 'Error: ' + data.error;
                    hazardText.className = '';
                } else {
                    hazardText.textContent = data.hazard;
                    hazardText.className = '';
                    mapImage.src = '/map?' + new Date().getTime();
                    mapImage.style.display = 'block';
                }
            } catch (error) {
                hazardText.textContent = 'Error: ' + error.message;
                hazardText.className = '';
            } finally {
                button.disabled = false;
                button.textContent = 'Get Flood Hazard';
            }
        }
    </script>
</body>
</html>
"""