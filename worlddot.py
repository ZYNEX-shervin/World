"""
WorldDot — Real Full-World Map Made Only From Dots

A terminal application that renders a complete, real geographic world map
using only the '.' character.
"""
import sys
import os
import argparse
import curses
import time
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import config, WORLD_GEOJSON_PATH
from src.mapdata import download_world_data, load_world_geometry
from src.renderer import TerminalRenderer
from src.controls import InputHandler

def check_dependencies():
    """Check if all required dependencies are installed"""
    try:
        import numpy
        import shapely
        import geopandas
        import pyproj
    except ImportError as e:
        print(f"Error: Missing dependency: {e}")
        print("\nInstall dependencies with:")
        print("  pip install -r requirements.txt")
        sys.exit(1)

def ensure_dataset():
    """Ensure geographic dataset is available"""
    if WORLD_GEOJSON_PATH.exists():
        return True
    
    print("\nGeographic dataset not found.")
    print("Downloading world data...")
    
    if not download_world_data():
        print("\nError: Could not download geographic data")
        print("Please try again or download manually:")
        print("  python3 src/mapdata.py")
        sys.exit(1)
    
    return True

def main(stdscr, debug=False):
    """
    Main application loop
    
    Args:
        stdscr: curses window object
        debug: enable debug mode
    """
    try:
        # Load geographic data
        print("Loading geographic data...", file=sys.stderr)
        gdf = load_world_geometry()
        
        # Create renderer
        renderer = TerminalRenderer(stdscr, gdf, debug=debug)
        input_handler = InputHandler(stdscr, renderer)
        
        # Main loop
        frame_count = 0
        start_time = time.time()
        
        while input_handler.handle_input():
            renderer.render_frame()
            frame_count += 1
            
            # Limit frame rate to ~60 FPS
            time.sleep(0.016)
        
        # Stats
        elapsed = time.time() - start_time
        if debug and elapsed > 0:
            avg_fps = frame_count / elapsed
            print(f"\nStats: {frame_count} frames in {elapsed:.1f}s ({avg_fps:.1f} FPS)", file=sys.stderr)
    
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        if debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

def run_app(debug=False):
    """
    Run the WorldDot application
    
    Args:
        debug: enable debug mode
    """
    try:
        curses.wrapper(main, debug)
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        prog='worlddot',
        description='Real Full-World Map Made Only From Dots',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 worlddot.py
  python3 worlddot.py --projection mercator
  python3 worlddot.py --debug
  python3 worlddot.py --zoom 2.0

Controls:
  [+/-]             Zoom in/out
  [Arrow keys]      Pan (north/south/east/west)
  [WASD]            Pan (alternative)
  [R]               Reset to initial view
  [P]               Cycle projection
  [H]               Toggle help/status bar
  [C]               Toggle color mode
  [T]               Toggle Antarctica
  [Q/ESC]           Quit
        """
    )
    
    parser.add_argument(
        '--projection',
        choices=['equirectangular', 'mercator'],
        default=None,
        help='Geographic projection (default: equirectangular)'
    )
    
    parser.add_argument(
        '--zoom',
        type=float,
        default=None,
        help='Initial zoom level (default: 1.0)'
    )
    
    parser.add_argument(
        '--no-color',
        action='store_true',
        help='Disable ANSI colors'
    )
    
    parser.add_argument(
        '--hide-status',
        action='store_true',
        help='Hide status bar at startup'
    )
    
    parser.add_argument(
        '--hide-antarctica',
        action='store_true',
        help='Hide Antarctica at startup'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode with performance metrics'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )
    
    return parser.parse_args()

if __name__ == '__main__':
    # Check dependencies first
    check_dependencies()
    
    # Parse arguments
    args = parse_arguments()
    
    # Apply configuration from arguments
    if args.projection:
        config['projection'] = args.projection
    
    if args.zoom is not None:
        config['initial_zoom'] = args.zoom
    
    if args.no_color:
        config['color_enabled'] = False
    
    if args.hide_status:
        config['show_status'] = False
    
    if args.hide_antarctica:
        config['hide_antarctica'] = True
    
    # Ensure dataset exists
    ensure_dataset()
    
    # Run application
    run_app(debug=args.debug)
