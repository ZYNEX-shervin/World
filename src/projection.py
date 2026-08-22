"""
Geographic projections for coordinate transformations
"""
import numpy as np
from pyproj import Proj, transform as pyproj_transform
from math import pi, sin, cos, atan, exp, tan, sqrt, atan2

class Projection:
    """Base projection class"""
    
    def __init__(self):
        self.name = "Projection"
    
    def project(self, lon, lat):
        """
        Project geographic coordinates (lon, lat) to display coordinates (x, y)
        
        Args:
            lon: longitude in degrees
            lat: latitude in degrees
        
        Returns:
            tuple: (x, y) in normalized coordinates [0, 1]
        """
        raise NotImplementedError
    
    def unproject(self, x, y):
        """
        Unproject display coordinates back to geographic coordinates
        
        Args:
            x: normalized x coordinate [0, 1]
            y: normalized y coordinate [0, 1]
        
        Returns:
            tuple: (lon, lat) in degrees
        """
        raise NotImplementedError

class EquirectangularProjection(Projection):
    """
    Equirectangular (Plate Carree) projection
    
    Simple linear mapping:
    x = longitude
    y = latitude
    
    Best for full-world views, no singularities at poles.
    """
    
    def __init__(self):
        super().__init__()
        self.name = "Equirectangular"
    
    def project(self, lon, lat):
        """
        Project to equirectangular coordinates
        """
        # Normalize to [0, 1] range
        # Longitude: -180 to 180 -> 0 to 1
        x = (lon + 180.0) / 360.0
        
        # Latitude: -90 to 90 -> 0 to 1 (with aspect correction)
        y = (lat + 90.0) / 180.0
        
        return x, y
    
    def unproject(self, x, y):
        """
        Unproject from equirectangular coordinates
        """
        lon = x * 360.0 - 180.0
        lat = y * 180.0 - 90.0
        
        # Clamp to valid ranges
        lon = np.clip(lon, -180.0, 180.0)
        lat = np.clip(lat, -90.0, 90.0)
        
        return lon, lat

class WebMercatorProjection(Projection):
    """
    Web Mercator (EPSG:3857) projection
    
    Conformal projection commonly used in web maps.
    Requires latitude clipping to ±85.051129°
    """
    
    # Maximum latitude for Web Mercator
    MAX_LAT = 85.051129
    
    def __init__(self):
        super().__init__()
        self.name = "Web Mercator"
    
    def project(self, lon, lat):
        """
        Project to Web Mercator coordinates
        """
        # Clip latitude to valid range
        lat = np.clip(lat, -self.MAX_LAT, self.MAX_LAT)
        
        # Normalize longitude
        x = (lon + 180.0) / 360.0
        
        # Mercator formula
        lat_rad = np.radians(lat)
        y_merc = np.log(np.tan(pi/4.0 + lat_rad/2.0))
        
        # Normalize y to [0, 1]
        max_merc = np.log(np.tan(pi/4.0 + np.radians(self.MAX_LAT)/2.0))
        y = (y_merc + max_merc) / (2.0 * max_merc)
        
        return x, y
    
    def unproject(self, x, y):
        """
        Unproject from Web Mercator coordinates
        """
        lon = x * 360.0 - 180.0
        
        # Inverse Mercator formula
        max_merc = np.log(np.tan(pi/4.0 + np.radians(self.MAX_LAT)/2.0))
        lat_rad = 2.0 * (np.arctan(np.exp((y * 2.0 * max_merc) - max_merc)) - pi/4.0)
        lat = np.degrees(lat_rad)
        
        # Clamp to valid ranges
        lon = np.clip(lon, -180.0, 180.0)
        lat = np.clip(lat, -self.MAX_LAT, self.MAX_LAT)
        
        return lon, lat

class ProjectionFactory:
    """Factory for creating projection instances"""
    
    _projections = {
        "equirectangular": EquirectangularProjection,
        "mercator": WebMercatorProjection,
    }
    
    @classmethod
    def create(cls, name):
        """
        Create a projection by name
        
        Args:
            name: projection name (equirectangular, mercator)
        
        Returns:
            Projection instance
        """
        proj_class = cls._projections.get(name.lower())
        if proj_class is None:
            raise ValueError(f"Unknown projection: {name}")
        return proj_class()
    
    @classmethod
    def list(cls):
        """List available projections"""
        return list(cls._projections.keys())

def create_projection(name):
    """Convenience function to create a projection"""
    return ProjectionFactory.create(name)

def get_available_projections():
    """Get list of available projections"""
    return ProjectionFactory.list()
