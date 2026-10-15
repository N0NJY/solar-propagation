"""Map geometry helpers (no UI): coastlines, night-side outline, great-circle paths."""
import json
import math
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


def night_outline(dt, step=4, lon_range=(-180.0, 180.0)):
    """Terminator as [(lon, lat)] west->east, and which pole edge is dark ('S' or 'N')."""
    dec, _ = solar.sun_declination_ra(dt)
    lo, hi = max(-180.0, lon_range[0]), min(180.0, lon_range[1])
    n = max(1, int(math.ceil((hi - lo) / step)))
    pts = [(lo + (hi - lo) * i / n, solar.terminator_lat(lo + (hi - lo) * i / n, dt)) for i in range(n + 1)]
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


# ---------- detailed shapes (Natural Earth 50m etc.), loaded lazily with bounding boxes ----------
_DATA = Path(__file__).parent / "data"
_SHAPES = {}


def _bbox(flat):
    xs, ys = flat[0::2], flat[1::2]
    return (min(xs), min(ys), max(xs), max(ys))


def shapes(name):
    """[(bbox, flat_coords)] for 'land' (110m), 'land50', 'lakes50', 'borders', 'states'."""
    if name not in _SHAPES:
        raw = json.loads((_DATA / ("land.json" if name == "land" else f"{name}.json")).read_text())
        _SHAPES[name] = [(_bbox(r), r) for r in raw]
    return _SHAPES[name]


_CITIES = None


def cities():
    """[(name, lat, lon, scalerank, population, is_capital, iso2)] most important first."""
    global _CITIES
    if _CITIES is None:
        _CITIES = [tuple(c) for c in json.loads((_DATA / "cities.json").read_text())]
    return _CITIES


# ---------- zoomable viewport over an equirectangular world map ----------
MAX_ZOOM = 64.0


class View:
    """z=1 shows the whole world (360 x 180 degrees); z=N shows 1/N of each span."""

    def __init__(self, z=1.0, clon=0.0, clat=0.0):
        self.z, self.clon, self.clat = z, clon, clat
        self.clamp()

    def clamp(self):
        self.z = min(MAX_ZOOM, max(1.0, self.z))
        sl, sa = 360.0 / self.z, 180.0 / self.z
        self.clon = min(180.0 - sl / 2, max(-180.0 + sl / 2, self.clon))
        self.clat = min(90.0 - sa / 2, max(-90.0 + sa / 2, self.clat))

    def bbox(self):
        sl, sa = 360.0 / self.z, 180.0 / self.z
        return (self.clon - sl / 2, self.clat - sa / 2, self.clon + sl / 2, self.clat + sa / 2)

    def to_xy(self, lon, lat, w, h):
        x0, y0, x1, y1 = self.bbox()
        return (lon - x0) / (x1 - x0) * w, (y1 - lat) / (y1 - y0) * h

    def to_lonlat(self, x, y, w, h):
        x0, y0, x1, y1 = self.bbox()
        return x0 + x / w * (x1 - x0), y1 - y / h * (y1 - y0)

    def zoom_at(self, factor, x, y, w, h):
        """Zoom by `factor` keeping the map point under pixel (x, y) fixed."""
        lon, lat = self.to_lonlat(x, y, w, h)
        self.z = min(MAX_ZOOM, max(1.0, self.z * factor))
        self.clon, self.clat = 0.0, 0.0
        sl, sa = 360.0 / self.z, 180.0 / self.z
        self.clon = lon - (x / w - 0.5) * sl
        self.clat = lat + (y / h - 0.5) * sa
        self.clamp()

    def drag_to(self, lon, lat, x, y, w, h, z=None):
        """Place the view so map point (lon, lat) sits under pixel (x, y) (optionally at zoom z)."""
        if z is not None:
            self.z = min(MAX_ZOOM, max(1.0, z))
        sl, sa = 360.0 / self.z, 180.0 / self.z
        self.clon = lon - (x / w - 0.5) * sl
        self.clat = lat + (y / h - 0.5) * sa
        self.clamp()

    def center_on(self, lat, lon, z):
        self.z, self.clon, self.clat = z, lon, lat
        self.clamp()

    def km_per_pixel(self, h):
        return 111.19 / (h * self.z / 180.0)


def maidenhead_cells(bbox, level):
    """Grid cells overlapping bbox: level 1 = 20x10 degree fields ('FN'), 2 = 2x1 squares ('FN31').
    -> [(label, lon0, lat0, lon1, lat1)]"""
    dlon, dlat = (20.0, 10.0) if level == 1 else (2.0, 1.0)
    x0, y0, x1, y1 = bbox
    i0, i1 = int(math.floor((max(-180.0, x0) + 180.0) / dlon)), int(math.floor((min(179.999, x1) + 180.0) / dlon))
    j0, j1 = int(math.floor((max(-90.0, y0) + 90.0) / dlat)), int(math.floor((min(89.999, y1) + 90.0) / dlat))
    out = []
    for j in range(j0, j1 + 1):
        for i in range(i0, i1 + 1):
            lon0, lat0 = -180.0 + i * dlon, -90.0 + j * dlat
            fi, fj = int((lon0 + 180.0) // 20), int((lat0 + 90.0) // 10)
            label = chr(65 + fi) + chr(65 + fj)
            if level == 2:
                label += str(int(((lon0 + 180.0) % 20) // 2)) + str(int((lat0 + 90.0) % 10))
            out.append((label, lon0, lat0, lon0 + dlon, lat0 + dlat))
    return out
