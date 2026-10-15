"""Convert Natural Earth land GeoJSON into a compact JSON of [lon, lat, lon, lat, ...] rings.

Usage: python tools/make_land.py ne_110m_land.geojson hfprop/data/land.json
Data: Natural Earth (public domain), https://www.naturalearthdata.com/
"""
import json
import sys

src, dst = sys.argv[1], sys.argv[2]
gj = json.load(open(src))
rings = []
for f in gj["features"]:
    g = f["geometry"]
    polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
    for poly in polys:
        ring = poly[0]                      # outer ring only; holes are tiny at 110m
        flat = []
        for lon, lat in ring:
            flat += [round(lon, 1), round(lat, 1)]
        rings.append(flat)
json.dump(rings, open(dst, "w"), separators=(",", ":"))
print(len(rings), "rings,", sum(len(r) // 2 for r in rings), "points")
