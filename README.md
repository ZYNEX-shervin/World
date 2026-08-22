# World DotMap

An advanced terminal world-map renderer built from `.` characters.

## Features

- Natural Earth-style GeoJSON country boundaries
- Adaptive terminal resolution
- Dot-density land rendering
- Zoom with `+` / `-`
- Panning with arrow keys or `WASD`
- Country and continent labels
- Coastline and international-border rendering
- Mercator, Robinson, and Orthographic projections
- Optional ANSI colors
- Country/city search and jump-to-location
- Live cursor latitude/longitude
- Optional day/night terminator
- Offline local map data
- Interactive terminal UI

## Run

```bash
python main.py
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Controls

| Key | Action |
|---|---|
| `+` / `-` | Zoom |
| Arrow keys / `WASD` | Pan |
| `P` | Change projection |
| `C` | Toggle colors |
| `D` | Toggle day/night |
| `L` | Toggle labels |
| `B` | Toggle borders |
| `/` | Search location |
| `R` | Reset view |
| `Q` | Quit |

The renderer is designed to remain useful over SSH and low-bandwidth terminals while providing substantially more interaction and projection support than a basic ASCII map viewer.
