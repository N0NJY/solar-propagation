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


def latlon_to_grid(lat, lon, chars=6):
    lon += 180.0
    lat += 90.0
    out = chr(ord("A") + int(lon // 20)) + chr(ord("A") + int(lat // 10))
    out += str(int((lon % 20) // 2)) + str(int(lat % 10))
    if chars >= 6:
        out += chr(ord("a") + int((lon % 2) * 12)) + chr(ord("a") + int((lat % 1) * 24))
    return out


def grid_to_latlon(grid):
    """Centre of a 4- or 6-character Maidenhead square."""
    g = grid.strip()
    if not re.fullmatch(r"[A-Ra-r]{2}\d\d([A-Xa-x]{2})?", g):
        raise ValueError(f"bad grid square: {grid!r}")
    g = g.upper()
    lon = (ord(g[0]) - 65) * 20 - 180 + int(g[2]) * 2
    lat = (ord(g[1]) - 65) * 10 - 90 + int(g[3])
    if len(g) >= 6:
        lon += (ord(g[4]) - 65) / 12 + 1 / 24
        lat += (ord(g[5]) - 65) / 24 + 1 / 48
    else:
        lon += 1.0
        lat += 0.5
    return lat, lon


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
    """Accept 'FN31', 'FN31pr', '90210', '40.7,-74.0'. Returns (lat, lon, label)."""
    t = text.strip()
    if re.fullmatch(r"\d{5}(-\d{4})?", t):
        lat, lon, name = zip_to_latlon(t)
        return lat, lon, name
    if re.fullmatch(r"[A-Ra-r]{2}\d\d([A-Xa-x]{2})?", t):
        lat, lon = grid_to_latlon(t)
        return lat, lon, t.upper()[:4] + t[4:].lower()
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
