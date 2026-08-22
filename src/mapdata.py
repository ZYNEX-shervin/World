"""
Geographic data management and dataset downloading
"""
import os
import json
import gzip
import shutil
import sys
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError

def get_data_dir():
    """Get data directory path"""
    return Path(__file__).parent.parent / "data"

def get_world_geojson_path():
    """Get world GeoJSON path"""
    return get_data_dir() / "world.geojson"

# Constants
WORLD_GEOJSON_PATH = get_world_geojson_path()
DATA_DIR = get_data_dir()
WORLD_GEOJSON_URL = "https://naciscdn.org/naturalearth/110m/cultural/ne_110m_admin_0_countries.zip"
WORLD_GEOJSON_FALLBACK = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson"

def download_file(url, output_path, progress=True):
    """
    Download a file from URL to output_path
    """
    try:
        print(f"Downloading from: {url}")
        with urlopen(url, timeout=30) as response:
            total_size = int(response.headers.get('content-length', 0))
            chunk_size = 8192
            downloaded = 0
            
            with open(output_path, 'wb') as out:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    out.write(chunk)
                    downloaded += len(chunk)
                    
                    if progress and total_size:
                        percent = (downloaded / total_size) * 100
                        bar_length = 40
                        filled = int(bar_length * downloaded / total_size)
                        bar = '█' * filled + '░' * (bar_length - filled)
                        print(f"\rDownloading: [{bar}] {percent:.1f}%", end='', flush=True)
            
            if progress:
                print()  # New line after progress bar
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False

def extract_geojson_from_zip(zip_path, output_path):
    """
    Extract GeoJSON from Natural Earth zip file
    """
    try:
        import zipfile
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Find .geojson file in zip
            for name in zip_ref.namelist():
                if name.endswith('.geojson'):
                    with zip_ref.open(name) as source:
                        with open(output_path, 'wb') as target:
                            target.write(source.read())
                    return True
        return False
    except Exception as e:
        print(f"Error extracting zip: {e}")
        return False

def download_world_data():
    """
    Download Natural Earth world geographic data
    Returns True if successful, False otherwise
    """
    print("\n" + "="*60)
    print("WorldDot — Geographic Data Download")
    print("="*60)
    
    # Check if data already exists
    if WORLD_GEOJSON_PATH.exists():
        try:
            with open(WORLD_GEOJSON_PATH, 'r') as f:
                data = json.load(f)
                if isinstance(data, dict) and 'features' in data:
                    print(f"\n✓ Geographic data already exists: {WORLD_GEOJSON_PATH}")
                    print(f"  Features: {len(data.get('features', []))}")
                    return True
        except:
            pass
    
    # Create data directory
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Try primary source (Natural Earth zip)
    print(f"\n1. Attempting to download from Natural Earth (zip)...")
    temp_zip = DATA_DIR / "ne_110m_admin_0_countries.zip"
    if download_file(WORLD_GEOJSON_URL, temp_zip):
        print("   Extracting GeoJSON from zip...")
        if extract_geojson_from_zip(temp_zip, WORLD_GEOJSON_PATH):
            temp_zip.unlink()
            print("✓ Successfully downloaded and extracted world data!")
            return True
        temp_zip.unlink()
    
    # Try fallback source (raw GeoJSON)
    print(f"\n2. Attempting to download from GitHub fallback...")
    if download_file(WORLD_GEOJSON_FALLBACK, WORLD_GEOJSON_PATH):
        print("✓ Successfully downloaded world data!")
        return True
    
    # If all downloads fail
    print("\n" + "="*60)
    print("ERROR: Could not download geographic data")
    print("="*60)
    print("\nPlease try one of the following:")
    print("1. Check your internet connection")
    print("2. Try again: python3 src/mapdata.py")
    print("3. Manually download from:")
    print(f"   {WORLD_GEOJSON_FALLBACK}")
    print(f"   and save to: {WORLD_GEOJSON_PATH}")
    return False

def validate_geojson(file_path):
    """
    Validate GeoJSON file
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        if not isinstance(data, dict):
            raise ValueError("GeoJSON must be a JSON object")
        
        if 'features' not in data:
            raise ValueError("GeoJSON must contain 'features' array")
        
        features = data['features']
        if not isinstance(features, list):
            raise ValueError("'features' must be an array")
        
        if len(features) == 0:
            raise ValueError("GeoJSON has no features")
        
        print(f"✓ GeoJSON valid: {len(features)} features")
        return True
    except Exception as e:
        print(f"✗ GeoJSON validation error: {e}")
        return False

def load_world_geometry():
    """
    Load world geometric data as GeoDataFrame
    """
    try:
        import geopandas as gpd
        
        if not WORLD_GEOJSON_PATH.exists():
            raise FileNotFoundError(f"Geographic dataset not found at {WORLD_GEOJSON_PATH}")
        
        print(f"Loading geographic data from {WORLD_GEOJSON_PATH}...")
        gdf = gpd.read_file(str(WORLD_GEOJSON_PATH))
        
        print(f"✓ Loaded {len(gdf)} geographic features")
        print(f"  Columns: {', '.join(gdf.columns.tolist())}")
        
        return gdf
    except ImportError:
        raise ImportError("GeoPandas not installed. Run: pip install -r requirements.txt")
    except FileNotFoundError as e:
        print(f"\n✗ {e}")
        print("\nPlease download the geographic dataset:")
        print("  python3 src/mapdata.py")
        raise
    except Exception as e:
        print(f"✗ Error loading geographic data: {e}")
        raise

if __name__ == "__main__":
    """
    Standalone script to download geographic data
    """
    if download_world_data():
        if validate_geojson(WORLD_GEOJSON_PATH):
            print("\n✓ Geographic data ready for use!")
            sys.exit(0)
    
    sys.exit(1)
