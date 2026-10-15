"""Geometry and location parsing: lat/lon, Maidenhead grid, US zip code."""
import json
import math
import re
import urllib.request

from .storage import cache_path

R_EARTH = 6371.0


def distance_km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R_EARTH * math.asin(min(1.0, math.sqrt(a)))


def bearing_deg(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def intermediate(lat1, lon1, lat2, lon2, f):
    """Point a fraction f (0..1) along the great circle."""
    p1, l1, p2, l2 = map(math.radians, (lat1, lon1, lat2, lon2))
    d = distance_km(lat1, lon1, lat2, lon2) / R_EARTH
    if d < 1e-9:
        return lat1, lon1
    a = math.sin((1 - f) * d) / math.sin(d)
    b = math.sin(f * d) / math.sin(d)
    x = a * math.cos(p1) * math.cos(l1) + b * math.cos(p2) * math.cos(l2)
    y = a * math.cos(p1) * math.sin(l1) + b * math.cos(p2) * math.sin(l2)
    z = a * math.sin(p1) + b * math.sin(p2)
    return (math.degrees(math.atan2(z, math.hypot(x, y))),
            math.degrees(math.atan2(y, x)))


# 4 chars FN31, 6 FN31pr, 8 FN31pr47, 10 FN31pr47ab (each step ~ 2 / 12 / 10 / 24 times finer)
GRID_RE = r"[A-Ra-r]{2}\d\d(?:[A-Xa-x]{2}(?:\d\d(?:[A-Xa-x]{2})?)?)?"


def latlon_to_grid(lat, lon, chars=6):
    lon = min(max(lon + 180.0, 0.0), 359.9999999)
    lat = min(max(lat + 90.0, 0.0), 179.9999999)
    out = chr(65 + int(lon // 20)) + chr(65 + int(lat // 10))
    out += str(int((lon % 20) // 2)) + str(int(lat % 10))
    lo, la = lon % 2, lat % 1                      # inside the 2 x 1 degree square
    if chars >= 6:
        out += chr(97 + int(lo * 12)) + chr(97 + int(la * 24))
        lo, la = lo * 12 % 1, la * 24 % 1          # inside the sub-square (fractions 0..1)
    if chars >= 8:
        out += str(int(lo * 10)) + str(int(la * 10))
        lo, la = lo * 10 % 1, la * 10 % 1
    if chars >= 10:
        out += chr(97 + int(lo * 24)) + chr(97 + int(la * 24))
    return out


def grid_to_latlon(grid):
    """Centre of a 4-, 6-, 8- or 10-character Maidenhead square."""
    g = grid.strip()
    if not re.fullmatch(GRID_RE, g):
        raise ValueError(f"bad grid square: {grid!r}")
    g = g.upper()
    lon = (ord(g[0]) - 65) * 20 - 180 + int(g[2]) * 2.0
    lat = (ord(g[1]) - 65) * 10 - 90 + int(g[3]) * 1.0
    w, h = 2.0, 1.0                                # size of the current square in degrees
    if len(g) >= 6:
        w, h = w / 24, h / 24
        lon += (ord(g[4]) - 65) * w
        lat += (ord(g[5]) - 65) * h
    if len(g) >= 8:
        w, h = w / 10, h / 10
        lon += int(g[6]) * w
        lat += int(g[7]) * h
    if len(g) >= 10:
        w, h = w / 24, h / 24
        lon += (ord(g[8]) - 65) * w
        lat += (ord(g[9]) - 65) * h
    return lat + h / 2, lon + w / 2


def zip_to_latlon(zipcode):
    """US zip lookup via zippopotam.us, cached on disk so it works offline later."""
    z = zipcode.strip()[:5]
    cache = cache_path("zips.json")
    try:
        table = json.loads(cache.read_text())
    except Exception:
        table = {}
    if z not in table:
        with urllib.request.urlopen(f"https://api.zippopotam.us/us/{z}", timeout=10) as r:
            data = json.load(r)
        p = data["places"][0]
        table[z] = [float(p["latitude"]), float(p["longitude"]),
                    f'{p["place name"]}, {p["state abbreviation"]}']
        cache.write_text(json.dumps(table))
    return tuple(table[z])


def parse_location(text):
    """Accept 'FN31', 'FN31pr', 'FN31pr47ab', '90210', '40.7,-74.0'. Returns (lat, lon, label)."""
    t = text.strip()
    if re.fullmatch(r"\d{5}(-\d{4})?", t):
        lat, lon, name = zip_to_latlon(t)
        return lat, lon, name
    if re.fullmatch(GRID_RE, t):
        lat, lon = grid_to_latlon(t)
        return lat, lon, t[:2].upper() + t[2:4] + t[4:].lower()
    m = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*[, ]\s*(-?\d+(?:\.\d+)?)\s*", t)
    if m:
        lat, lon = float(m.group(1)), float(m.group(2))
        if abs(lat) <= 90 and abs(lon) <= 180:
            return lat, lon, latlon_to_grid(lat, lon)
    raise ValueError("Enter a zip code, grid square (FN31), or lat,lon (40.7,-74.0)")


def locate_by_ip():
    """Approximate (city-level) position from the public IP address. -> (lat, lon, label)."""
    req = urllib.request.Request(
        "https://ipwho.is/?fields=success,latitude,longitude,city,region_code,country_code",
        headers={"User-Agent": "hfprop/0.1"})
    with urllib.request.urlopen(req, timeout=10) as r:
        d = json.load(r)
    if not d.get("success"):
        raise ValueError("Could not work out your location from your internet address")
    place = ", ".join(x for x in (d.get("city"), d.get("region_code") or d.get("country_code")) if x)
    return float(d["latitude"]), float(d["longitude"]), place or latlon_to_grid(d["latitude"], d["longitude"])
