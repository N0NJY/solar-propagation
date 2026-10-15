"""Build the compact map data files in hfprop/data/ from Natural Earth GeoJSON (public domain).

Usage: python tools/make_geo.py <dir containing the downloaded .geojson files> hfprop/data
Inputs (https://github.com/nvkelso/natural-earth-vector/tree/master/geojson):
  ne_50m_land, ne_50m_lakes, ne_50m_admin_0_boundary_lines_land,
  ne_50m_admin_1_states_provinces_lines, ne_50m_populated_places_simple
Outputs: land50.json, lakes50.json (rings), borders.json, states.json (polylines),
         cities.json ([name, lat, lon, scalerank, population, is_capital, iso2]).
Rings/polylines are flat [lon, lat, lon, lat, ...] lists rounded to 0.01 degrees.
"""
import json
import sys
from pathlib import Path

src, dst = Path(sys.argv[1]), Path(sys.argv[2])


def load(name):
    return json.load((src / f"{name}.geojson").open())["features"]


def flat(coords):
    out, last = [], None
    for lon, lat, *_ in coords:
        p = (round(lon, 2), round(lat, 2))
        if p != last:
            out += [p[0], p[1]]
            last = p
    return out


def rings(features):
    out = []
    for f in features:
        g = f["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        for poly in polys:
            r = flat(poly[0])                    # outer ring only
            if len(r) >= 6:
                out.append(r)
    return out


def lines(features):
    out = []
    for f in features:
        g = f["geometry"]
        parts = [g["coordinates"]] if g["type"] == "LineString" else g["coordinates"]
        for part in parts:
            r = flat(part)
            if len(r) >= 4:
                out.append(r)
    return out


def dump(name, obj):
    path = dst / name
    path.write_text(json.dumps(obj, separators=(",", ":")))
    print(f"{name:14s} {path.stat().st_size / 1024:7.0f} KB")


dump("land50.json", rings(load("ne_50m_land")))
dump("lakes50.json", rings(load("ne_50m_lakes")))
dump("borders.json", lines(load("ne_50m_admin_0_boundary_lines_land")))
dump("states.json", lines(load("ne_50m_admin_1_states_provinces_lines")))
cities = []
for f in load("ne_50m_populated_places_simple"):
    p = f["properties"]
    cities.append([p["nameascii"] or p["name"], round(p["latitude"], 3), round(p["longitude"], 3),
                   int(p["scalerank"]), int(p["pop_max"] or 0), int(bool(p.get("adm0cap"))), p.get("iso_a2") or ""])
cities.sort(key=lambda c: (c[3], -c[4]))
dump("cities.json", cities)
