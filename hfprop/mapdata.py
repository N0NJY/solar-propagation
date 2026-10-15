"""Map geometry helpers (no UI): coastlines, night-side outline, great-circle paths."""
import json
from pathlib import Path

from . import solar
from .geo import intermediate, distance_km

_LAND = None


def land_rings():
    """List of rings, each a flat [lon, lat, lon, lat, ...] list (Natural Earth 110m)."""
    global _LAND
    if _LAND is None:
        _LAND = json.loads((Path(__file__).parent / "data" / "land.json").read_text())
    return _LAND


def night_outline(dt, step=4):
    """Terminator as [(lon, lat)] west->east, and which pole edge is dark ('S' or 'N')."""
    dec, _ = solar.sun_declination_ra(dt)
    pts = [(float(lon), solar.terminator_lat(float(lon), dt)) for lon in range(-180, 181, step)]
    return pts, ("S" if dec > 0 else "N")


def great_circle(lat1, lon1, lat2, lon2, n=48):
    """Polyline segments [(lon,lat),...] split where the path crosses the 180 meridian."""
    segs, cur, prev = [], [], None
    for i in range(n + 1):
        lat, lon = intermediate(lat1, lon1, lat2, lon2, i / n)
        if prev is not None and abs(lon - prev) > 180:
            segs.append(cur)
            cur = []
        cur.append((lon, lat))
        prev = lon
    segs.append(cur)
    return segs
