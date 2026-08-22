"""
Configuration management for WorldDot
"""
import json
from pathlib import Path

# Project directories
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SRC_DIR = PROJECT_ROOT / "src"
CONFIG_FILE = PROJECT_ROOT / "config.json"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
SRC_DIR.mkdir(exist_ok=True)

# Default configuration
DEFAULT_CONFIG = {
    "projection": "equirectangular",
    "dot_character": ".",
    "color_enabled": False,
    "show_status": True,
    "land_threshold": 0.35,
    "aspect_ratio": 0.45,
    "initial_zoom": 1.0,
    "hide_antarctica": False,
    "pan_speed": 5.0,
    "zoom_speed": 1.2,
    "debug": False,
}

class Config:
    """Configuration manager"""
    
    def __init__(self):
        self.config = DEFAULT_CONFIG.copy()
        self.load_config_file()
    
    def load_config_file(self):
        """Load configuration from JSON file if it exists"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r') as f:
                    user_config = json.load(f)
                    self.config.update(user_config)
            except Exception as e:
                print(f"Warning: Could not load config file: {e}")
    
    def save_config_file(self):
        """Save current configuration to JSON file"""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save config file: {e}")
    
    def get(self, key, default=None):
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set(self, key, value):
        """Set configuration value"""
        self.config[key] = value
    
    def __getitem__(self, key):
        return self.config[key]
    
    def __setitem__(self, key, value):
        self.config[key] = value

# Global config instance
config = Config()

# Map data paths
WORLD_GEOJSON_PATH = DATA_DIR / "world.geojson"
WORLD_GEOJSON_URL = "https://naciscdn.org/naturalearth/110m/cultural/ne_110m_admin_0_countries.zip"
WORLD_GEOJSON_FALLBACK = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson"

# Projection constants
EARTH_RADIUS = 6371000  # meters

# Terminal rendering
TERMINAL_MIN_WIDTH = 80
TERMINAL_MIN_HEIGHT = 24

# Zoom constants
ZOOM_MIN = 0.5
ZOOM_MAX = 50.0
DEFAULT_ZOOM = 1.0

# Pan constants
PAN_INCREMENT = 5.0  # degrees

# Color codes (ANSI)
COLORS = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "white": "\033[97m",
    "green": "\033[92m",
    "cyan": "\033[96m",
    "gray": "\033[90m",
}

# Projection names
PROJECTIONS = {
    "equirectangular": "Equirectangular",
    "mercator": "Web Mercator",
}

# Default view
DEFAULT_CENTER_LON = 0.0
DEFAULT_CENTER_LAT = 0.0
DEFAULT_PROJECTION = "equirectangular"
