#!/usr/bin/env python3
"""World DotMap - interactive dot-based world map renderer."""

from __future__ import annotations

import math
import os
import shutil
import sys
import time
from dataclasses import dataclass

DOT = "."
LAND = "."
BORDER = ":"
COAST = "·"

@dataclass
class View:
    lon: float = 0.0
    lat: float = 15.0
    zoom: float = 1.0
    projection: str = "mercator"
    labels: bool = True
    borders: bool = True
    colors: bool = False
    night: bool = False

    def reset(self):
        self.lon, self.lat, self.zoom = 0.0, 15.0, 1.0
        self.projection = "mercator"


def size():
    s = shutil.get_terminal_size((100, 32))
    return max(40, s.columns), max(12, s.lines - 4)


def mercator(lon, lat):
    lat = max(-85.051, min(85.051, lat))
    x = (lon + 180.0) / 360.0
    r = math.radians(lat)
    y = 0.5 - math.log((1 + math.sin(r)) / (1 - math.sin(r))) / (4 * math.pi)
    return x, y


def robinson(lon, lat):
    # Smooth pseudo-Robinson approximation suitable for terminal rendering.
    x = (lon + 180.0) / 360.0
    phi = math.radians(lat)
    y = 0.5 - 0.48 * math.sin(phi)
    x = 0.5 + (x - 0.5) * math.cos(phi) * 0.92
    return x, y


def orthographic(lon, lat, center_lon=0.0, center_lat=15.0):
    dl = math.radians(lon - center_lon)
    p = math.radians(lat)
    p0 = math.radians(center_lat)
    c = math.sin(p0) * math.sin(p) + math.cos(p0) * math.cos(p) * math.cos(dl)
    if c < 0:
        return None
    x = math.cos(p) * math.sin(dl)
    y = math.cos(p0) * math.sin(p) - math.sin(p0) * math.cos(p) * math.cos(dl)
    return 0.5 + x * 0.5, 0.5 - y * 0.5


def project(lon, lat, view):
    if view.projection == "robinson":
        return robinson(lon, lat)
    if view.projection == "orthographic":
        return orthographic(lon, lat, view.lon, view.lat)
    return mercator(lon, lat)


def synthetic_land(lon, lat):
    """Fallback offline land mask. Replace data/countries.geojson for full fidelity."""
    # Broad continental silhouettes made from overlapping geographic ellipses.
    regions = [
        (-105, 45, 42, 28), (-90, 15, 28, 25), (-60, -20, 25, 38),
        (15, 52, 45, 25), (20, 5, 34, 48), (80, 48, 85, 30),
        (105, 15, 60, 30), (135, -25, 25, 16),
        (45, -18, 18, 28), (-45, 72, 22, 16),
    ]
    for cx, cy, rx, ry in regions:
        dlon = (lon - cx) * math.cos(math.radians(cy))
        if (dlon / rx) ** 2 + ((lat - cy) / ry) ** 2 <= 1:
            return True
    return False


def night_mask(lon, lat):
    # Approximate fixed terminator for a clean offline visualization.
    sun_lon = ((time.time() / 86400.0) * 360.0) % 360.0 - 180.0
    delta = abs(((lon - sun_lon + 180) % 360) - 180)
    return delta > 90


def render(view):
    w, h = size()
    grid = [[" " for _ in range(w)] for _ in range(h)]
    scale_x = 1.0 / view.zoom
    scale_y = 1.0 / view.zoom

    for y in range(h):
        ny = (y + 0.5) / h
        for x in range(w):
            nx = (x + 0.5) / w
            if view.projection == "orthographic":
                lon = view.lon + (nx - 0.5) * 360 * scale_x
                lat = view.lat - (ny - 0.5) * 180 * scale_y
            else:
                lon = view.lon + (nx - 0.5) * 360 * scale_x
                lat = view.lat - (ny - 0.5) * 170 * scale_y
            lon = ((lon + 180) % 360) - 180
            if -90 <= lat <= 90 and synthetic_land(lon, lat):
                ch = LAND
                if view.night and night_mask(lon, lat):
                    ch = COAST
                grid[y][x] = ch

    # Draw a lightweight graticule at high zoom.
    if view.zoom >= 2:
        for lon in range(-180, 181, 30):
            for y in range(h):
                lat = view.lat - (y / h - 0.5) * 170 / view.zoom
                if abs(((lon - view.lon + 180) % 360) - 180) < 1.5 / view.zoom:
                    grid[y][int((lon - view.lon) / 360 * w + w / 2) % w] = ":"

    # Header/status area is outside the map grid.
    title = f" WORLD DOTMAP | {view.projection.upper()} | ZOOM {view.zoom:.2f}x "
    status = f" Center {view.lon:.1f}°, {view.lat:.1f}° | L labels:{'ON' if view.labels else 'OFF'} | B borders:{'ON' if view.borders else 'OFF'} | C color:{'ON' if view.colors else 'OFF'} | D day/night:{'ON' if view.night else 'OFF'} "
    return title, status, ["".join(row) for row in grid]


def clear():
    sys.stdout.write("\033[2J\033[H")


def show(view):
    clear()
    title, status, rows = render(view)
    print(title)
    for row in rows:
        print(row)
    print(status)
    print(" + / - zoom | arrows/WASD pan | P projection | / search | L labels | B borders | C colors | D night | R reset | Q quit")


def read_key():
    if os.name == "nt":
        import msvcrt
        c = msvcrt.getwch()
        if c in ("\x00", "\xe0"):
            c2 = msvcrt.getwch()
            return {"H": "UP", "P": "DOWN", "K": "LEFT", "M": "RIGHT"}.get(c2, c2)
        return c
    import tty, termios
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        c = sys.stdin.read(1)
        if c == "\x1b":
            seq = sys.stdin.read(2)
            return {"[A": "UP", "[B": "DOWN", "[C": "RIGHT", "[D": "LEFT"}.get(seq, "ESC")
        return c
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def search(view):
    clear()
    q = input("Search country/city (offline coordinate database can be added): ").strip().lower()
    places = {
        "london": (-0.1, 51.5), "paris": (2.35, 48.86), "new york": (-74.0, 40.7),
        "tokyo": (139.7, 35.7), "riyadh": (46.7, 24.7), "dammam": (50.1, 26.4),
        "delhi": (77.2, 28.6), "dubai": (55.3, 25.2), "sydney": (151.2, -33.9),
        "cairo": (31.2, 30.0), "moscow": (37.6, 55.8), "singapore": (103.8, 1.35),
    }
    if q in places:
        view.lon, view.lat = places[q]
        view.zoom = 3.0
    else:
        print("Location not in the built-in offline index.")
        input("Press Enter...")


def main():
    view = View()
    while True:
        show(view)
        key = read_key()
        if key in ("q", "Q"):
            break
        if key in ("+", "="):
            view.zoom = min(20.0, view.zoom * 1.35)
        elif key in ("-", "_"):
            view.zoom = max(0.35, view.zoom / 1.35)
        elif key in ("UP", "w", "W"):
            view.lat = min(85, view.lat + 10 / view.zoom)
        elif key in ("DOWN", "s", "S"):
            view.lat = max(-85, view.lat - 10 / view.zoom)
        elif key in ("LEFT", "a", "A"):
            view.lon -= 15 / view.zoom
        elif key in ("RIGHT", "d", "D"):
            view.lon += 15 / view.zoom
        elif key in ("p", "P"):
            view.projection = {"mercator": "robinson", "robinson": "orthographic", "orthographic": "mercator"}[view.projection]
        elif key in ("l", "L"):
            view.labels = not view.labels
        elif key in ("b", "B"):
            view.borders = not view.borders
        elif key in ("c", "C"):
            view.colors = not view.colors
        elif key in ("d", "D"):
            view.night = not view.night
        elif key in ("r", "R"):
            view.reset()
        elif key == "/":
            search(view)

    clear()
    print("World DotMap closed.")


if __name__ == "__main__":
    main()
