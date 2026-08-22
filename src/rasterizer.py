"""
Polygon rasterization and land detection
"""
import numpy as np
from shapely.geometry import Point
from shapely.prepared import prep

class Rasterizer:
    """Rasterizes geographic polygons to terminal grid"""
    
    def __init__(self, geometries, projection, char_aspect_ratio=0.45, land_threshold=0.35):
        self.geometries = geometries
        self.projection = projection
        self.char_aspect_ratio = char_aspect_ratio
        self.land_threshold = land_threshold
        self.prepared_geoms = [prep(geom) for geom in geometries if geom.is_valid]
    
    def is_land(self, lon, lat):
        """Check if a point is on land"""
        point = Point(lon, lat)
        for geom in self.prepared_geoms:
            if geom.contains(point):
                return True
        return False
    
    def sample_cell(self, center_lon, center_lat, cell_width, cell_height, samples=4):
        """Sample multiple points within a cell to determine land coverage"""
        land_count = 0
        total_count = samples * samples
        
        for i in range(samples):
            for j in range(samples):
                u = (i + 0.5) / samples
                v = (j + 0.5) / samples
                sample_lon = center_lon + (u - 0.5) * cell_width
                sample_lat = center_lat + (v - 0.5) * cell_height
                if self.is_land(sample_lon, sample_lat):
                    land_count += 1
        
        return land_count / total_count
    
    def rasterize_viewport(self, lon_min, lon_max, lat_min, lat_max, width, height, samples=2):
        """Rasterize viewport to character grid"""
        cell_width = (lon_max - lon_min) / width
        cell_height = (lat_max - lat_min) / height
        cell_height_corrected = cell_height / self.char_aspect_ratio
        
        grid = np.zeros((height, width), dtype=np.float32)
        
        for y in range(height):
            for x in range(width):
                center_lon = lon_min + (x + 0.5) * cell_width
                center_lat = lat_max - (y + 0.5) * cell_height_corrected
                coverage = self.sample_cell(center_lon, center_lat, cell_width, cell_height_corrected, samples=samples)
                grid[y, x] = coverage
        
        return grid
    
    def rasterize_with_antialiasing(self, lon_min, lon_max, lat_min, lat_max, width, height, samples=2):
        """Rasterize with anti-aliasing"""
        grid = self.rasterize_viewport(lon_min, lon_max, lat_min, lat_max, width, height, samples)
        return grid >= self.land_threshold

class FastRasterizer(Rasterizer):
    """Optimized rasterizer using bounding box filtering"""
    
    def __init__(self, geometries, projection, char_aspect_ratio=0.45, land_threshold=0.35):
        super().__init__(geometries, projection, char_aspect_ratio, land_threshold)
        self.bounds = []
        for geom in self.geometries:
            if geom.is_valid:
                self.bounds.append(geom.bounds)
