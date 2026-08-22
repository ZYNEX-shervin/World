"""
WorldDot package initialization
"""
__version__ = "1.0.0"
__author__ = "WorldDot Contributors"
__description__ = "Real Full-World Map Made Only From Dots"

from src.config import config
from src.projection import create_projection, get_available_projections
from src.mapdata import load_world_geometry, download_world_data

__all__ = [
    'config',
    'create_projection',
    'get_available_projections',
    'load_world_geometry',
    'download_world_data',
]
