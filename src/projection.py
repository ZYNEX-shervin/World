"""
Geographic projections for coordinate transformations
"""
import numpy as np
from math import pi

class Projection:
    """Base projection class"""
    
    def __init__(self):
        self.name = "Projection"
    
    def project(self, lon, lat):
        """Project geographic coordinates to display coordinates"""
        raise NotImplementedError
    
    def unproject(self, x, y):
        """Unproject display coordinates back to geographic coordinates"""
        raise NotImplementedError

class EquirectangularProjection(Projection):
    """Equirectangular projection - simple linear mapping"""
    
    def __init__(self):
        super().__init__()
        self.name = "Equirectangular"
    
    def project(self, lon, lat):
        x = (lon + 180.0) / 360.0
        y = (lat + 90.0) / 180.0
        return x, y
    
    def unproject(self, x, y):
        lon = x * 360.0 - 180.0
        lat = y * 180.0 - 90.0
        lon = np.clip(lon, -180.0, 180.0)
        lat = np.clip(lat, -90.0, 90.0)
        return lon, lat

class WebMercatorProjection(Projection):
    """Web Mercator projection"""
    
    MAX_LAT = 85.051129
    
    def __init__(self):
        super().__init__()
        self.name = "Web Mercator"
    
    def project(self, lon, lat):
        lat = np.clip(lat, -self.MAX_LAT, self.MAX_LAT)
        x = (lon + 180.0) / 360.0
        lat_rad = np.radians(lat)
        y_merc = np.log(np.tan(pi/4.0 + lat_rad/2.0))
        max_merc = np.log(np.tan(pi/4.0 + np.radians(self.MAX_LAT)/2.0))
        y = (y_merc + max_merc) / (2.0 * max_merc)
        return x, y
    
    def unproject(self, x, y):
        lon = x * 360.0 - 180.0
        max_merc = np.log(np.tan(pi/4.0 + np.radians(self.MAX_LAT)/2.0))
        lat_rad = 2.0 * (np.arctan(np.exp((y * 2.0 * max_merc) - max_merc)) - pi/4.0)
        lat = np.degrees(lat_rad)
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
        proj_class = cls._projections.get(name.lower())
        if proj_class is None:
            raise ValueError(f"Unknown projection: {name}")
        return proj_class()
    
    @classmethod
    def list(cls):
        return list(cls._projections.keys())

def create_projection(name):
    """Create a projection by name"""
    return ProjectionFactory.create(name)

def get_available_projections():
    """Get list of available projections"""
    return ProjectionFactory.list()
