#!/usr/bin/env python3
"""World DotMap: real country geometry rendered as terminal dots."""
from __future__ import annotations

import json
import math
import os
import shutil
import sys
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

try:
    from shapely.geometry import Point, shape
    from shapely.ops import unary_union
    from shapely.prepared import prep
except ImportError:
    print("Missing dependency: shapely")
    print("Run: py -m pip install -r requirements.txt")
    raise SystemExit(1)

DATA_DIR = Path(__file__).with_name("data")
DATA_FILE = DATA_DIR / "countries.geojson"
DATA_URL = "https://raw.githubusercontent.com/datasets/geo-boundaries-world-110m/main/countries.geojson"

# City/capital reference points for terminal labels and search.
CITIES = {
    "london": (-0.1276, 51.5072), "paris": (2.3522, 48.8566),
    "berlin": (13.4050, 52.5200), "madrid": (-3.7038, 40.4168),
    "rome": (12.4964, 41.9028), "cairo": (31.2357, 30.0444),
    "riyadh": (46.6753, 24.7136), "dubai": (55.2708, 25.2048),
    "dammam": (50.0888, 26.4207), "delhi": (77.2090, 28.6139),
    "mumbai": (72.8777, 19.0760), "tokyo": (139.6917, 35.6895),
    "beijing": (116.4074, 39.9042), "seoul": (126.9780, 37.5665),
    "singapore": (103.8198, 1.3521), "sydney": (151.2093, -33.8688),
    "new york": (-74.0060, 40.7128), "los angeles": (-118.2437, 34.0522),
    "washington": (-77.0369, 38.9072), "mexico city": (-99.1332, 19.4326),
    "sao paulo": (-46.6333, -23.5505), "buenos aires": (-58.3816, -34.6037),
    "moscow": (37.6173, 55.7558), "istanbul": (28.9784, 41.0082),
}


@dataclass
class View:
    lon: float = 10.0
    lat: float = 25.0
    zoom: float = 1.0
    projection: str = "mercator"
    labels: bool = True
    borders: bool = True
    cities: bool = True
    colors: bool = False
    night: bool = False
    grid: bool = False

    def reset(self):
        self.lon, self.lat, self.zoom, self.projection = 10.0, 25.0, 1.0, "mercator"


def ensure_data():
    DATA_DIR.mkdir(exist_ok=True)
    if DATA_FILE.exists() and DATA_FILE.stat().st_size > 10000:
        return
    print("Downloading real Natural Earth country boundaries (one-time setup)...")
    try:
        urllib.request.urlretrieve(DATA_URL, DATA_FILE)
    except Exception as exc:
        print(f"Could not download map data: {exc}")
        print(f"You can manually download the GeoJSON from:\n{DATA_URL}")
        raise SystemExit(1)


class WorldData:
    def __init__(self):
        ensure_data()
        with DATA_FILE.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        self.features = raw["features"]
        self.geoms = [shape(f["geometry"]) for f in self.features]
        self.names = [
            f.get("properties", {}).get("name")
            or f.get("properties", {}).get("NAME")
            or "Unknown"
            for f in self.features
        ]
        self.land = unary_union(self.geoms)
        self.land_prepared = prep(self.land)
        self.borders = unary_union([g.boundary for g in self.geoms])
        self.border_prepared = prep(self.borders)
        self.labels = []
        for name, geom in zip(self.names, self.geoms):
            p = geom.representative_point()
            self.labels.append((name, p.x, p.y))

    def country_at(self, lon: float, lat: float):
        p = Point(lon, lat)
        for name, geom in zip(self.names, self.geoms):
            if geom.contains(p):
                return name
        return None


def terminal_size():
    s = shutil.get_terminal_size((120, 36))
    return max(60, s.columns), max(16, s.lines - 5)


def mercator_inverse(x, y):
    lon = x * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y))))
    return lon, lat


def robinson_forward(lon, lat):
    # Terminal-friendly Robinson approximation.
    p = math.radians(lat)
    return 0.5 + (lon / 360.0) * (0.87 + 0.13 * math.cos(p)), 0.5 - 0.48 * math.sin(p)


def robinson_inverse(x, y):
    lat = math.degrees(math.asin(max(-1.0, min(1.0, (0.5 - y) / 0.48))))
    scale = 0.87 + 0.13 * math.cos(math.radians(lat))
    lon = ((x - 0.5) * 360.0) / scale
    return lon, lat


def orthographic_inverse(x, y, center_lon, center_lat):
    # x/y are normalized globe coordinates. Return None for the far side.
    X, Y = (x - 0.5) * 2, (0.5 - y) * 2
    rho = math.hypot(X, Y)
    if rho > 1:
        return None
    if rho < 1e-9:
        return center_lon, center_lat
    c = math.asin(rho)
    p0 = math.radians(center_lat)
    lon0 = math.radians(center_lon)
    lat = math.asin(math.cos(c) * math.sin(p0) + (Y * math.sin(c) * math.cos(p0) / rho))
    lon = lon0 + math.atan2(X * math.sin(c), rho * math.cos(p0) * math.cos(c) - Y * math.sin(p0) * math.sin(c))
    return math.degrees(lon), math.degrees(lat)


def screen_to_geo(x, y, w, h, view):
    # Character cells are wider than tall; compensate for terminal aspect ratio.
    aspect = 2.0
    nx = (x + 0.5) / w
    ny = (y + 0.5) / h
    if view.projection == "orthographic":
        return orthographic_inverse(nx, ny, view.lon, view.lat)
    if view.projection == "robinson":
        xx = 0.5 + (nx - 0.5) / view.zoom
        yy = 0.5 + (ny - 0.5) * aspect / view.zoom
        lon, lat = robinson_inverse(xx, yy)
        return lon + view.lon, lat + view.lat - 25.0
    # Mercator view centered around view.lon/view.lat.
    xx = 0.5 + (nx - 0.5) / view.zoom
    yy = 0.5 + (ny - 0.5) * aspect / view.zoom
    center_x = (view.lon + 180.0) / 360.0
    center_y = 0.5 - math.asinh(math.tan(math.radians(view.lat))) / math.pi / 2
    lon = xx * 360.0 - 180.0 + view.lon
    # Use a local Mercator offset to make panning/zoom intuitive.
    yy = center_y + (ny - 0.5) * aspect / view.zoom
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * yy))))
    lon = ((lon + 180) % 360) - 180
    return lon, lat


def night_mask(lon, lat):
    sun_lon = ((time.time() / 86400.0) * 360.0) % 360.0 - 180.0
    return abs(((lon - sun_lon + 180) % 360) - 180) > 90


def colorize(ch, code, enabled):
    return f"\033[{code}m{ch}\033[0m" if enabled else ch


def render(data: WorldData, view: View):
    w, h = terminal_size()
    grid = [[" " for _ in range(w)] for _ in range(h)]
    for y in range(h):
        for x in range(w):
            geo = screen_to_geo(x, y, w, h, view)
            if geo is None:
                continue
            lon, lat = geo
            if not (-90 <= lat <= 90):
                continue
            p = Point(lon, lat)
            if data.land_prepared.contains(p):
                ch = "."
                # Borders are intentionally rendered as dots too, with density changed.
                if view.borders and data.border_prepared.distance(p) < max(0.05, 0.55 / view.zoom):
                    ch = "."
                if view.night and night_mask(lon, lat):
                    ch = "."
                grid[y][x] = colorize(ch, 37, view.colors)
            elif view.grid and (abs((lon % 10) - 5) < 0.18 or abs((lat % 10) - 5) < 0.18):
                grid[y][x] = colorize("·", 90, view.colors)

    # Country labels become useful after zooming in. Keep them sparse at world scale.
    if view.labels:
        min_zoom = 1.0 if view.zoom >= 1.5 else 2.0
        if view.zoom >= min_zoom:
            for name, lon, lat in data.labels:
                if view.zoom < 2.0 and len(name) > 10:
                    continue
                pos = geo_to_screen(lon, lat, w, h, view)
                if pos:
                    sx, sy = pos
                    if 0 <= sy < h and 0 <= sx < w:
                        text = name.upper()
                        for i, ch in enumerate(text[: max(0, w - sx)]):
                            if sx + i < w:
                                grid[sy][sx + i] = colorize(ch, 36, view.colors)

    if view.cities and view.zoom >= 2:
        for name, (lon, lat) in CITIES.items():
            pos = geo_to_screen(lon, lat, w, h, view)
            if pos:
                sx, sy = pos
                if 0 <= sy < h and 0 <= sx < w:
                    grid[sy][sx] = colorize(".", 33, view.colors)

    return grid


def geo_to_screen(lon, lat, w, h, view):
    if view.projection == "orthographic":
        p0 = math.radians(view.lat)
        l0 = math.radians(view.lon)
        p = math.radians(lat)
        dl = math.radians(lon - view.lon)
        visible = math.sin(p0) * math.sin(p) + math.cos(p0) * math.cos(p) * math.cos(dl)
        if visible < 0:
            return None
        X = math.cos(p) * math.sin(dl)
        Y = math.cos(p0) * math.sin(p) - math.sin(p0) * math.cos(p) * math.cos(dl)
        return int((0.5 + X * 0.5) * w), int((0.5 - Y * 0.5) * h)
    if view.projection == "robinson":
        x, y = robinson_forward(lon - view.lon, lat - view.lat + 25)
        sx = int((0.5 + (x - 0.5) * view.zoom) * w)
        sy = int((0.5 + (y - 0.5) * view.zoom / 2) * h)
        return sx, sy
    cx = (view.lon + 180) / 360
    cy = 0.5 - math.asinh(math.tan(math.radians(view.lat))) / (2 * math.pi)
    x = ((lon + 180) / 360 - cx) * view.zoom + 0.5
    y = (0.5 - math.asinh(math.tan(math.radians(lat))) / (2 * math.pi) - cy) * view.zoom / 2 + 0.5
    return int(x * w), int(y * h)


def clear():
    sys.stdout.write("\033[2J\033[H")


def show(data, view):
    clear()
    print(f" WORLD DOTMAP  | REAL GEOJSON | {view.projection.upper()} | ZOOM {view.zoom:.2f}x")
    for row in render(data, view):
        print("".join(row))
    print(f" Center: {view.lon:.2f}°, {view.lat:.2f}° | labels {view.labels} | borders {view.borders} | cities {view.cities} | grid {view.grid} | night {view.night}")
    print(" + - zoom | arrows/WASD pan | P projection | / search | L labels | B borders | T cities | C color | D night | G grid | R reset | Q quit")


def read_key():
    if os.name == "nt":
        import msvcrt
        c = msvcrt.getwch()
        if c in ("\x00", "\xe0"):
            c2 = msvcrt.getwch()
            return {"H": "UP", "P": "DOWN", "K": "LEFT", "M": "RIGHT"}.get(c2, c2)
        return c
    import tty, termios
    fd = sys.stdin.fileno(); old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd); c = sys.stdin.read(1)
        if c == "\x1b":
            seq = sys.stdin.read(2)
            return {"[A":"UP", "[B":"DOWN", "[C":"RIGHT", "[D":"LEFT"}.get(seq, "ESC")
        return c
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def search(view, data):
    clear()
    q = input("Search country or city: ").strip().lower()
    if q in CITIES:
        view.lon, view.lat = CITIES[q]
        view.zoom = 4.0
        return
    for name, lon, lat in data.labels:
        if q in name.lower():
            view.lon, view.lat = lon, lat
            view.zoom = 3.0
            return
    print("No matching location found in the offline data.")
    input("Press Enter...")


def main():
    data = WorldData()
    view = View()
    while True:
        show(data, view)
        key = read_key()
        if key in ("q", "Q"):
            break
        if key in ("+", "="):
            view.zoom = min(30.0, view.zoom * 1.35)
        elif key in ("-", "_"):
            view.zoom = max(0.35, view.zoom / 1.35)
        elif key in ("UP", "w", "W"):
            view.lat = min(85, view.lat + 12 / view.zoom)
        elif key in ("DOWN", "s", "S"):
            view.lat = max(-85, view.lat - 12 / view.zoom)
        elif key in ("LEFT", "a", "A"):
            view.lon -= 18 / view.zoom
        elif key in ("RIGHT", "d"):
            view.lon += 18 / view.zoom
        elif key in ("p", "P"):
            view.projection = {"mercator":"robinson", "robinson":"orthographic", "orthographic":"mercator"}[view.projection]
        elif key in ("l", "L"):
            view.labels = not view.labels
        elif key in ("b", "B"):
            view.borders = not view.borders
        elif key in ("t", "T"):
            view.cities = not view.cities
        elif key in ("c", "C"):
            view.colors = not view.colors
        elif key in ("d", "D"):
            view.night = not view.night
        elif key in ("g", "G"):
            view.grid = not view.grid
        elif key in ("r", "R"):
            view.reset()
        elif key == "/":
            search(view, data)
    clear()
    print("World DotMap closed.")


if __name__ == "__main__":
    main()
