"""
Polygon rasterization and land detection
"""
import numpy as np
from shapely.geometry import Point, box
from shapely.prepared import prep

class Rasterizer:
    """
    Rasterizes geographic polygons to terminal grid
    """
    
    def __init__(self, geometries, projection, char_aspect_ratio=0.45, land_threshold=0.35):
        """
        Initialize rasterizer
        
        Args:
            geometries: list of shapely geometry objects
            projection: Projection instance
            char_aspect_ratio: terminal character height/width ratio
            land_threshold: coverage threshold for land detection (0.0-1.0)
        """
        self.geometries = geometries
        self.projection = projection
        self.char_aspect_ratio = char_aspect_ratio
        self.land_threshold = land_threshold
        
        # Prepare geometries for faster intersection tests
        self.prepared_geoms = [prep(geom) for geom in geometries if geom.is_valid]
    
    def is_land(self, lon, lat):
        """
        Check if a point is on land
        
        Args:
            lon: longitude in degrees
            lat: latitude in degrees
        
        Returns:
            bool: True if point is on land, False otherwise
        """
        point = Point(lon, lat)
        for geom in self.prepared_geoms:
            if geom.contains(point):
                return True
        return False
    
    def sample_cell(self, center_lon, center_lat, cell_width, cell_height, samples=4):
        """
        Sample multiple points within a cell to determine land coverage
        
        Args:
            center_lon: cell center longitude
            center_lat: cell center latitude
            cell_width: cell width in degrees
            cell_height: cell height in degrees
            samples: number of samples per dimension (samples^2 total)
        
        Returns:
            float: land coverage (0.0-1.0)
        """
        land_count = 0
        total_count = samples * samples
        
        # Generate sample points
        for i in range(samples):
            for j in range(samples):
                # Normalized position within cell
                u = (i + 0.5) / samples
                v = (j + 0.5) / samples
                
                # Sample point coordinates
                sample_lon = center_lon + (u - 0.5) * cell_width
                sample_lat = center_lat + (v - 0.5) * cell_height
                
                if self.is_land(sample_lon, sample_lat):
                    land_count += 1
        
        return land_count / total_count
    
    def rasterize_viewport(self, lon_min, lon_max, lat_min, lat_max, 
                          width, height, samples=2):
        """
        Rasterize viewport to character grid
        
        Args:
            lon_min, lon_max: longitude bounds
            lat_min, lat_max: latitude bounds
            width: grid width in characters
            height: grid height in characters
            samples: anti-aliasing samples per cell
        
        Returns:
            numpy array of shape (height, width) with land coverage (0.0-1.0)
        """
        # Calculate cell dimensions
        cell_width = (lon_max - lon_min) / width
        cell_height = (lat_max - lat_min) / height
        
        # Apply aspect ratio correction
        # Adjust latitude based on character aspect ratio
        cell_height_corrected = cell_height / self.char_aspect_ratio
        
        # Create output grid
        grid = np.zeros((height, width), dtype=np.float32)
        
        # Rasterize each cell
        for y in range(height):
            for x in range(width):
                # Cell center in geographic coordinates
                center_lon = lon_min + (x + 0.5) * cell_width
                center_lat = lat_max - (y + 0.5) * cell_height_corrected
                
                # Sample cell for land coverage
                coverage = self.sample_cell(
                    center_lon, center_lat,
                    cell_width, cell_height_corrected,
                    samples=samples
                )
                
                grid[y, x] = coverage
        
        return grid
    
    def rasterize_with_antialiasing(self, lon_min, lon_max, lat_min, lat_max,
                                    width, height, samples=2):
        """
        Rasterize with anti-aliasing for smoother coastlines
        
        Returns:
            numpy array of boolean (height, width) where True = land
        """
        grid = self.rasterize_viewport(lon_min, lon_max, lat_min, lat_max,
                                       width, height, samples)
        
        # Apply threshold
        return grid >= self.land_threshold

class FastRasterizer(Rasterizer):
    """
    Optimized rasterizer using bounding box filtering
    """
    
    def __init__(self, geometries, projection, char_aspect_ratio=0.45, land_threshold=0.35):
        super().__init__(geometries, projection, char_aspect_ratio, land_threshold)
        
        # Pre-compute bounding boxes for filtering
        self.bounds = []
        for geom in self.geometries:
            if geom.is_valid:
                minx, miny, maxx, maxy = geom.bounds
                self.bounds.append((minx, miny, maxx, maxy))
    
    def rasterize_viewport(self, lon_min, lon_max, lat_min, lat_max,
                          width, height, samples=2):
        """
        Rasterize with viewport filtering for better performance
        """
        cell_width = (lon_max - lon_min) / width
        cell_height = (lat_max - lat_min) / height
        cell_height_corrected = cell_height / self.char_aspect_ratio
        
        grid = np.zeros((height, width), dtype=np.float32)
        
        # Filter geometries to viewport
        viewport_geoms = []
        viewport_bounds = (lon_min, lat_min - cell_height_corrected * height,
                          lon_max, lat_max)
        
        for i, (minx, miny, maxx, maxy) in enumerate(self.bounds):
            # Check if geometry bounds intersect viewport
            if (maxx >= lon_min and minx <= lon_max and
                maxy >= lat_min - cell_height_corrected * height and miny <= lat_max):
                viewport_geoms.append((i, self.prepared_geoms[i]))
        
        # Rasterize only visible geometries
        for y in range(height):
            for x in range(width):
                center_lon = lon_min + (x + 0.5) * cell_width
                center_lat = lat_max - (y + 0.5) * cell_height_corrected
                
                # Quick check with bounding boxes first
                land_count = 0
                for sample_i in range(samples * samples):
                    i = sample_i // samples
                    j = sample_i % samples
                    u = (i + 0.5) / samples
                    v = (j + 0.5) / samples
                    
                    sample_lon = center_lon + (u - 0.5) * cell_width
                    sample_lat = center_lat + (v - 0.5) * cell_height_corrected
                    
                    point = Point(sample_lon, sample_lat)
                    for _, geom in viewport_geoms:
                        if geom.contains(point):
                            land_count += 1
                            break
                
                grid[y, x] = land_count / (samples * samples)
        
        return grid
