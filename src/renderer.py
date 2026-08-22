"""
Terminal rendering engine for WorldDot
"""
import os
import sys
import curses
import time
import numpy as np
from datetime import datetime

from src.config import config, COLORS, TERMINAL_MIN_WIDTH, TERMINAL_MIN_HEIGHT
from src.rasterizer import FastRasterizer
from src.projection import create_projection

class TerminalRenderer:
    """
    Renders the world map to terminal
    """
    
    def __init__(self, stdscr, gdf, debug=False):
        """
        Initialize renderer
        
        Args:
            stdscr: curses window object
            gdf: GeoDataFrame with world geometries
            debug: enable debug mode
        """
        self.stdscr = stdscr
        self.gdf = gdf
        self.debug = debug
        
        # Extract geometries
        self.geometries = gdf.geometry.tolist()
        
        # State
        self.center_lon = 0.0
        self.center_lat = 0.0
        self.zoom = 1.0
        self.projection_name = config.get("projection", "equirectangular")
        self.projection = create_projection(self.projection_name)
        self.show_status = config.get("show_status", True)
        self.color_enabled = config.get("color_enabled", False)
        self.hide_antarctica = config.get("hide_antarctica", False)
        
        # Performance metrics
        self.last_frame_time = time.time()
        self.frame_times = []
        self.last_render_time = 0
        
        # Setup curses
        curses.curs_set(0)  # Hide cursor
        self.stdscr.nodelay(True)  # Non-blocking input
        self.stdscr.timeout(0)
        
        # Colors
        if curses.has_colors():
            curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
            curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
            curses.init_pair(3, curses.COLOR_CYAN, curses.COLOR_BLACK)
            curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLACK)
    
    def get_terminal_size(self):
        """Get current terminal dimensions"""
        height, width = self.stdscr.getmaxyx()
        return max(width, TERMINAL_MIN_WIDTH), max(height, TERMINAL_MIN_HEIGHT)
    
    def filter_antarctica(self, geometries):
        """Filter out Antarctica if requested"""
        if not self.hide_antarctica:
            return geometries
        
        # Filter geometries by latitude bounds (Antarctica is below ~-60°)
        filtered = []
        for geom in geometries:
            if geom.is_valid:
                minx, miny, maxx, maxy = geom.bounds
                # Keep if max latitude > -60
                if maxy > -60:
                    filtered.append(geom)
                else:
                    # Check if geometry has parts above -60
                    if geom.geom_type == 'MultiPolygon':
                        parts = [p for p in geom.geoms if p.bounds[3] > -60]
                        if parts:
                            from shapely.geometry import MultiPolygon
                            filtered.append(MultiPolygon(parts))
                    else:
                        filtered.append(geom)
            else:
                filtered.append(geom)
        
        return filtered if filtered else geometries
    
    def get_viewport_bounds(self, width, height):
        """
        Calculate viewport bounds in geographic coordinates
        
        Returns:
            (lon_min, lon_max, lat_min, lat_max)
        """
        char_aspect = config.get("aspect_ratio", 0.45)
        
        # Calculate map height in degrees (accounting for aspect ratio)
        map_height = 180.0 / self.zoom
        map_width = 360.0 / self.zoom
        
        # Adjust for terminal aspect ratio
        map_height = map_height * (width / height) * char_aspect
        map_width = map_width * (width / height)
        
        lon_min = self.center_lon - map_width / 2.0
        lon_max = self.center_lon + map_width / 2.0
        lat_min = self.center_lat - map_height / 2.0
        lat_max = self.center_lat + map_height / 2.0
        
        return lon_min, lon_max, lat_min, lat_max
    
    def render_frame(self):
        """Render a single frame"""
        try:
            start_time = time.time()
            
            width, height = self.get_terminal_size()
            
            # Check minimum size
            if width < TERMINAL_MIN_WIDTH or height < TERMINAL_MIN_HEIGHT:
                self.stdscr.clear()
                self.stdscr.addstr(0, 0, f"Terminal too small. Min: {TERMINAL_MIN_WIDTH}x{TERMINAL_MIN_HEIGHT}")
                self.stdscr.refresh()
                return
            
            # Get viewport bounds
            lon_min, lon_max, lat_min, lat_max = self.get_viewport_bounds(width, height)
            
            # Handle wrapping at antimeridian
            if lon_min < -180:
                lon_min += 360
                lon_max += 360
            elif lon_max > 180:
                lon_min -= 360
                lon_max -= 360
            
            # Clamp to valid ranges
            lon_min = max(lon_min, -180)
            lon_max = min(lon_max, 180)
            lat_min = max(lat_min, -90)
            lat_max = min(lat_max, 90)
            
            # Filter geometries
            geoms = self.filter_antarctica(self.geometries)
            
            # Create rasterizer
            char_aspect = config.get("aspect_ratio", 0.45)
            land_threshold = config.get("land_threshold", 0.35)
            rasterizer = FastRasterizer(geoms, self.projection, char_aspect, land_threshold)
            
            # Rasterize viewport
            grid = rasterizer.rasterize_with_antialiasing(
                lon_min, lon_max, lat_min, lat_max,
                width - 2, height - 5 if self.show_status else height,
                samples=2
            )
            
            # Clear screen
            self.stdscr.clear()
            
            # Render map
            map_height = grid.shape[0]
            for y in range(map_height):
                try:
                    for x in range(grid.shape[1]):
                        char = "." if grid[y, x] else " "
                        
                        # Apply color if enabled
                        if self.color_enabled and grid[y, x]:
                            self.stdscr.addstr(y, x, char, curses.color_pair(1))
                        else:
                            self.stdscr.addstr(y, x, char)
                except curses.error:
                    pass  # Ignore write errors at edge
            
            # Render status bar
            if self.show_status:
                status_y = map_height + 1
                
                # Title
                title = "worlddot — Real geographic map rendered using dots"
                try:
                    self.stdscr.addstr(status_y, 0, title[:width])
                except curses.error:
                    pass
                
                # Status line
                status_y += 1
                status_line = (
                    f"Zoom: {self.zoom:.2f}x | "
                    f"Center: {self.center_lon:.2f}°, {self.center_lat:.2f}° | "
                    f"Projection: {self.projection.name} | "
                    f"Res: {width}x{map_height}"
                )
                try:
                    self.stdscr.addstr(status_y, 0, status_line[:width])
                except curses.error:
                    pass
                
                # Controls line
                status_y += 1
                controls = "[+/-] Zoom  [↑↓←→/WASD] Pan  [R] Reset  [P] Projection"
                try:
                    self.stdscr.addstr(status_y, 0, controls[:width])
                except curses.error:
                    pass
                
                # More controls
                status_y += 1
                more_controls = "[C] Color  [H] Help  [T] Antarctica  [Q] Quit"
                try:
                    self.stdscr.addstr(status_y, 0, more_controls[:width])
                except curses.error:
                    pass
                
                # Debug info if enabled
                if self.debug:
                    status_y += 1
                    render_time = time.time() - start_time
                    self.last_render_time = render_time
                    fps = 1.0 / render_time if render_time > 0 else 0
                    debug_line = f"FPS: {fps:.1f}  Render: {render_time*1000:.1f}ms  Geoms: {len(geoms)}"
                    try:
                        self.stdscr.addstr(status_y, 0, debug_line[:width])
                    except curses.error:
                        pass
            
            self.stdscr.refresh()
            
            # Update metrics
            frame_time = time.time() - start_time
            self.frame_times.append(frame_time)
            if len(self.frame_times) > 60:
                self.frame_times.pop(0)
        
        except Exception as e:
            if self.debug:
                self.stdscr.addstr(0, 0, f"Error: {str(e)}")
                self.stdscr.refresh()
    
    def zoom_in(self):
        """Zoom in"""
        zoom_speed = config.get("zoom_speed", 1.2)
        self.zoom = min(self.zoom * zoom_speed, 50.0)
    
    def zoom_out(self):
        """Zoom out"""
        zoom_speed = config.get("zoom_speed", 1.2)
        self.zoom = max(self.zoom / zoom_speed, 0.5)
    
    def pan(self, direction):
        """
        Pan in direction
        
        Args:
            direction: 'north', 'south', 'east', 'west'
        """
        pan_speed = config.get("pan_speed", 5.0)
        pan_amount = pan_speed / self.zoom
        
        if direction == 'north':
            self.center_lat = min(self.center_lat + pan_amount, 90)
        elif direction == 'south':
            self.center_lat = max(self.center_lat - pan_amount, -90)
        elif direction == 'east':
            self.center_lon = (self.center_lon + pan_amount + 360) % 360 - 180
        elif direction == 'west':
            self.center_lon = (self.center_lon - pan_amount + 360) % 360 - 180
    
    def reset(self):
        """Reset to initial view"""
        self.center_lon = 0.0
        self.center_lat = 0.0
        self.zoom = 1.0
    
    def cycle_projection(self):
        """Cycle to next projection"""
        projections = ["equirectangular", "mercator"]
        idx = projections.index(self.projection_name)
        idx = (idx + 1) % len(projections)
        self.projection_name = projections[idx]
        self.projection = create_projection(self.projection_name)
    
    def toggle_status(self):
        """Toggle status bar visibility"""
        self.show_status = not self.show_status
    
    def toggle_color(self):
        """Toggle color mode"""
        self.color_enabled = not self.color_enabled
    
    def toggle_antarctica(self):
        """Toggle Antarctica visibility"""
        self.hide_antarctica = not self.hide_antarctica
    
    def get_fps(self):
        """Get average FPS"""
        if self.frame_times:
            avg_time = sum(self.frame_times) / len(self.frame_times)
            return 1.0 / avg_time if avg_time > 0 else 0
        return 0
