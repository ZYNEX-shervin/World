#!/usr/bin/env python3
"""Real-world GeoJSON terminal map rendered primarily with dots."""
from __future__ import annotations

import json
import math
import os
import shutil
import time
import urllib.request
from pathlib import Path

from shapely.geometry import Point, shape
from shapely.ops import unary_union
from shapely.prepared import prep

DATA_DIR = Path(__file__).with_name("data")
DATA_FILE = DATA_DIR / "countries.geojson"
DATA_URL = "https://raw.githubusercontent.com/datasets/geo-boundaries-world-110m/main/countries.geojson"

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


def ensure_data():
    DATA_DIR.mkdir(exist_ok=True)
    if DATA_FILE.exists() and DATA_FILE.stat().st_size > 10000:
        return
    print("Downloading real country boundaries from Natural Earth GeoJSON...")
    urllib.request.urlretrieve(DATA_URL, DATA_FILE)


class World:
    def __init__(self):
        ensure_data()
        with DATA_FILE.open(encoding="utf-8") as f:
            fc = json.load(f)
        self.geoms = [shape(x["geometry"]) for x in fc["features"]]
        self.names = [
            x.get("properties", {}).get("name")
            or x.get("properties", {}).get("NAME")
            or "Unknown"
            for x in fc["features"]
        ]
        self.land = unary_union(self.geoms)
        self.land_test = prep(self.land)
        self.border = unary_union([g.boundary for g in self.geoms])
        self.labels = []
        for name, geom in zip(self.names, self.geoms):
            p = geom.representative_point()
            self.labels.append((name, p.x, p.y))

    def is_land(self, lon, lat):
        return self.land_test.contains(Point(lon, lat))

    def is_border(self, lon, lat, radius):
        # Exact country boundary geometry; this includes international borders and coastlines.
        return self.border.distance(Point(lon, lat)) <= radius


class View:
    def __init__(self):
        self.lon = 10.0
        self.lat = 25.0
        self.zoom = 1.0
        self.projection = "mercator"
        self.labels = True
        self.cities = True
        self.borders = True
        self.colors = False
        self.night = False
        self.grid = False

    def reset(self):
        self.__init__()


def term_size():
    s = shutil.get_terminal_size((120, 36))
    return max(60, s.columns), max(15, s.lines - 5)


def geo_to_xy(lon, lat, view):
    if view.projection == "orthographic":
        p0 = math.radians(view.lat)
        dl = math.radians(lon - view.lon)
        p = math.radians(lat)
        visible = math.sin(p0)*math.sin(p) + math.cos(p0)*math.cos(p)*math.cos(dl)
        if visible < 0:
            return None
        x = math.cos(p) * math.sin(dl)
        y = math.cos(p0)*math.sin(p) - math.sin(p0)*math.cos(p)*math.cos(dl)
        return .5 + x*.5, .5 - y*.5

    if view.projection == "robinson":
        p = math.radians(lat)
        scale = .87 + .13*math.cos(p)
        x = .5 + ((lon - view.lon) / 360.0) * scale * view.zoom
        y = .5 - (.48*math.sin(p) - .48*math.sin(math.radians(view.lat))) * view.zoom / 2
        return x, y

    # Mercator centered on the current longitude/latitude.
    def my(latitude):
        latitude = max(-85.051, min(85.051, latitude))
        return math.asinh(math.tan(math.radians(latitude)))
    x = .5 + ((lon - view.lon) / 360.0) * view.zoom
    y = .5 - (my(lat) - my(view.lat)) / (2*math.pi) * view.zoom
    return x, y


def xy_to_geo(nx, ny, view):
    if view.projection == "orthographic":
        X, Y = (nx-.5)*2, (0.5-ny)*2
        rho = math.hypot(X, Y)
        if rho > 1:
            return None
        if rho < 1e-9:
            return view.lon, view.lat
        c = math.asin(rho)
        p0 = math.radians(view.lat)
        lat = math.asin(math.cos(c)*math.sin(p0) + Y*math.sin(c)*math.cos(p0)/rho)
        lon = math.radians(view.lon) + math.atan2(X*math.sin(c), rho*math.cos(p0)*math.cos(c)-Y*math.sin(p0)*math.sin(c))
        return math.degrees(lon), math.degrees(lat)

    if view.projection == "robinson":
        lat = view.lat + math.degrees(math.asin(max(-1, min(1, (.5-ny)*2/view.zoom/.48))))
        scale = .87 + .13*math.cos(math.radians(lat))
        lon = view.lon + (nx-.5)*360/scale/view.zoom
        return lon, lat

    y = math.asinh(math.tan(math.radians(view.lat))) - (ny-.5)*2*math.pi/view.zoom
    lat = math.degrees(math.atan(math.sinh(y)))
    lon = view.lon + (nx-.5)*360/view.zoom
    lon = ((lon+180)%360)-180
    return lon, lat


def color(ch, code, enabled):
    return f"\033[{code}m{ch}\033[0m" if enabled else ch


def render(world, view):
    w, h = term_size()
    grid = [[" "]*w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            geo = xy_to_geo((x+.5)/w, (y+.5)/h, view)
            if not geo:
                continue
            lon, lat = geo
            if not -90 <= lat <= 90:
                continue
            if world.is_land(lon, lat):
                # Everything is a dot; boundaries use a denser/stronger dot zone.
                ch = "."
                if view.borders and world.is_border(lon, lat, max(.03, .20/view.zoom)):
                    ch = "."
                if view.night and is_night(lon):
                    ch = "."
                grid[y][x] = color(ch, 37, view.colors)
            elif view.grid and (abs(lon%10-5)<.15 or abs(lat%10-5)<.15):
                grid[y][x] = color(".", 90, view.colors)

    if view.labels and view.zoom >= 1.25:
        for name, lon, lat in world.labels:
            pos = geo_to_xy(lon, lat, view)
            if not pos:
                continue
            sx, sy = int(pos[0]*w), int(pos[1]*h)
            if not (0 <= sy < h and 0 <= sx < w):
                continue
            text = name.upper()
            if view.zoom < 2.5 and len(text) > 12:
                continue
            for i, ch in enumerate(text[:w-sx]):
                if sx+i < w:
                    grid[sy][sx+i] = color(ch, 36, view.colors)

    if view.cities and view.zoom >= 2:
        for lon, lat in CITIES.values():
            pos = geo_to_xy(lon, lat, view)
            if pos:
                sx, sy = int(pos[0]*w), int(pos[1]*h)
                if 0 <= sy < h and 0 <= sx < w:
                    grid[sy][sx] = color(".", 33, view.colors)
    return grid


def is_night(lon):
    sun = ((time.time()/86400)*360)%360 - 180
    return abs(((lon-sun+180)%360)-180) > 90


def clear():
    print("\033[2J\033[H", end="")


def show(world, view):
    clear()
    print(f" WORLD DOTMAP | REAL COUNTRY BOUNDARIES | {view.projection.upper()} | {view.zoom:.2f}x")
    for row in render(world, view):
        print("".join(row))
    print(f" Center {view.lon:.2f}°, {view.lat:.2f}° | labels:{view.labels} borders:{view.borders} cities:{view.cities} color:{view.colors} night:{view.night}")
    print("+/- zoom | arrows/WASD pan | P projection | / search | L labels | B borders | T cities | C color | D night | G grid | R reset | Q quit")


def key():
    if os.name == "nt":
        import msvcrt
        c = msvcrt.getwch()
        if c in ("\x00", "\xe0"):
            c2 = msvcrt.getwch()
            return {"H":"UP", "P":"DOWN", "K":"LEFT", "M":"RIGHT"}.get(c2, c2)
        return c
    import tty, termios
    fd = sys.stdin.fileno(); old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd); c = os.read(fd, 1).decode(errors="ignore")
        if c == "\x1b":
            seq = os.read(fd, 2).decode(errors="ignore")
            return {"[A":"UP", "[B":"DOWN", "[C":"RIGHT", "[D":"LEFT"}.get(seq, "ESC")
        return c
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def search(world, view):
    clear()
    q = input("Search country/city: ").strip().lower()
    if q in CITIES:
        view.lon, view.lat, view.zoom = *CITIES[q], 5.0
        return
    for name, lon, lat in world.labels:
        if q in name.lower():
            view.lon, view.lat, view.zoom = lon, lat, 4.0
            return
    print("Not found.")
    input("Press Enter...")


def main():
    try:
        world = World()
    except Exception as exc:
        clear(); print("Map data setup failed:", exc); print("Check your internet connection for the first run."); return
    view = View()
    while True:
        show(world, view)
        k = key()
        if k in ("q", "Q"): break
        if k in ("+", "="): view.zoom = min(30, view.zoom*1.35)
        elif k in ("-", "_"): view.zoom = max(.35, view.zoom/1.35)
        elif k in ("UP", "w", "W"): view.lat = min(85, view.lat+12/view.zoom)
        elif k in ("DOWN", "s", "S"): view.lat = max(-85, view.lat-12/view.zoom)
        elif k in ("LEFT", "a", "A"): view.lon -= 18/view.zoom
        elif k in ("RIGHT", "d"): view.lon += 18/view.zoom
        elif k in ("p", "P"): view.projection = {"mercator":"robinson", "robinson":"orthographic", "orthographic":"mercator"}[view.projection]
        elif k in ("l", "L"): view.labels = not view.labels
        elif k in ("b", "B"): view.borders = not view.borders
        elif k in ("t", "T"): view.cities = not view.cities
        elif k in ("c", "C"): view.colors = not view.colors
        elif k in ("d", "D"): view.night = not view.night
        elif k in ("g", "G"): view.grid = not view.grid
        elif k in ("r", "R"): view.reset()
        elif k == "/": search(world, view)
    clear(); print("World DotMap closed.")


if __name__ == "__main__":
    main()
