"""
Terminal rendering engine for WorldDot
"""
import curses
import time
import numpy as np
from src.config import config, TERMINAL_MIN_WIDTH, TERMINAL_MIN_HEIGHT
from src.rasterizer import FastRasterizer
from src.projection import create_projection

class TerminalRenderer:
    """Renders the world map to terminal"""
    
    def __init__(self, stdscr, gdf, debug=False):
        self.stdscr = stdscr
        self.gdf = gdf
        self.debug = debug
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
        
        # Setup curses
        curses.curs_set(0)
        self.stdscr.nodelay(True)
        self.stdscr.timeout(0)
        
        # Colors
        if curses.has_colors():
            curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
    
    def get_terminal_size(self):
        """Get current terminal dimensions"""
        height, width = self.stdscr.getmaxyx()
        return max(width, TERMINAL_MIN_WIDTH), max(height, TERMINAL_MIN_HEIGHT)
    
    def filter_antarctica(self, geometries):
        """Filter out Antarctica if requested"""
        if not self.hide_antarctica:
            return geometries
        return [g for g in geometries if g.is_valid and g.bounds[3] > -60]
    
    def get_viewport_bounds(self, width, height):
        """Calculate viewport bounds in geographic coordinates"""
        char_aspect = config.get("aspect_ratio", 0.45)
        map_height = 180.0 / self.zoom
        map_width = 360.0 / self.zoom
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
            width, height = self.get_terminal_size()
            
            if width < TERMINAL_MIN_WIDTH or height < TERMINAL_MIN_HEIGHT:
                self.stdscr.clear()
                self.stdscr.addstr(0, 0, f"Terminal too small. Min: {TERMINAL_MIN_WIDTH}x{TERMINAL_MIN_HEIGHT}")
                self.stdscr.refresh()
                return
            
            lon_min, lon_max, lat_min, lat_max = self.get_viewport_bounds(width, height)
            lon_min = max(lon_min, -180)
            lon_max = min(lon_max, 180)
            lat_min = max(lat_min, -90)
            lat_max = min(lat_max, 90)
            
            geoms = self.filter_antarctica(self.geometries)
            char_aspect = config.get("aspect_ratio", 0.45)
            land_threshold = config.get("land_threshold", 0.35)
            rasterizer = FastRasterizer(geoms, self.projection, char_aspect, land_threshold)
            
            grid = rasterizer.rasterize_with_antialiasing(
                lon_min, lon_max, lat_min, lat_max,
                width - 2, height - 5 if self.show_status else height,
                samples=2
            )
            
            self.stdscr.clear()
            
            map_height = grid.shape[0]
            for y in range(map_height):
                try:
                    for x in range(grid.shape[1]):
                        char = "." if grid[y, x] else " "
                        self.stdscr.addstr(y, x, char)
                except curses.error:
                    pass
            
            if self.show_status:
                status_y = map_height + 1
                try:
                    title = "worlddot — Real geographic map rendered using dots"
                    self.stdscr.addstr(status_y, 0, title[:width])
                except curses.error:
                    pass
                
                status_y += 1
                try:
                    status_line = (
                        f"Zoom: {self.zoom:.2f}x | Center: {self.center_lon:.2f}°, {self.center_lat:.2f}° | "
                        f"Projection: {self.projection.name} | Res: {width}x{map_height}"
                    )
                    self.stdscr.addstr(status_y, 0, status_line[:width])
                except curses.error:
                    pass
                
                status_y += 1
                try:
                    controls = "[+/-] Zoom  [↑↓←→/WASD] Pan  [R] Reset  [P] Projection"
                    self.stdscr.addstr(status_y, 0, controls[:width])
                except curses.error:
                    pass
                
                status_y += 1
                try:
                    more_controls = "[C] Color  [H] Help  [T] Antarctica  [Q] Quit"
                    self.stdscr.addstr(status_y, 0, more_controls[:width])
                except curses.error:
                    pass
            
            self.stdscr.refresh()
        except Exception as e:
            if self.debug:
                self.stdscr.addstr(0, 0, f"Error: {str(e)}")
                self.stdscr.refresh()
    
    def zoom_in(self):
        zoom_speed = config.get("zoom_speed", 1.2)
        self.zoom = min(self.zoom * zoom_speed, 50.0)
    
    def zoom_out(self):
        zoom_speed = config.get("zoom_speed", 1.2)
        self.zoom = max(self.zoom / zoom_speed, 0.5)
    
    def pan(self, direction):
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
        self.center_lon = 0.0
        self.center_lat = 0.0
        self.zoom = 1.0
    
    def cycle_projection(self):
        projections = ["equirectangular", "mercator"]
        idx = projections.index(self.projection_name)
        idx = (idx + 1) % len(projections)
        self.projection_name = projections[idx]
        self.projection = create_projection(self.projection_name)
    
    def toggle_status(self):
        self.show_status = not self.show_status
    
    def toggle_color(self):
        self.color_enabled = not self.color_enabled
    
    def toggle_antarctica(self):
        self.hide_antarctica = not self.hide_antarctica
