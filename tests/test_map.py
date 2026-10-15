import math

from hfprop import geo, mapdata, predict, spaceweather, units
from datetime import datetime, timezone


def test_units():
    assert units.dist(160.9344, "imperial") == "100 mi"
    assert units.dist(1500, "metric") == "1,500 km"
    assert units.speed(480, "metric") == "480 km/s" and units.speed(483.0, "imperial") == "300 mi/s"
    assert abs(units.unit_to_km(units.km_to_unit(1234.5, "imperial"), "imperial") - 1234.5) < 1e-9


def test_view_roundtrip_and_clamp():
    v = mapdata.View()
    assert v.bbox() == (-180.0, -90.0, 180.0, 90.0)
    v.center_on(41.7, -72.7, 8)
    x, y = v.to_xy(-72.7, 41.7, 1000, 500)
    assert abs(x - 500) < 1e-6 and abs(y - 250) < 1e-6
    lon, lat = v.to_lonlat(123, 321, 1000, 500)
    assert all(abs(a - b) < 1e-9 for a, b in zip(v.to_xy(lon, lat, 1000, 500), (123, 321)))
    v.center_on(89.0, 179.0, 8)                      # near the corner: clamped inside the world
    x0, y0, x1, y1 = v.bbox()
    assert x1 <= 180.0 + 1e-9 and y1 <= 90.0 + 1e-9
    v2 = mapdata.View(1000.0)
    assert v2.z == mapdata.MAX_ZOOM


def test_zoom_at_keeps_point_under_cursor():
    v = mapdata.View(2.0, -60.0, 20.0)
    before = v.to_lonlat(300, 120, 1000, 500)
    v.zoom_at(2.5, 300, 120, 1000, 500)
    after = v.to_lonlat(300, 120, 1000, 500)
    assert abs(before[0] - after[0]) < 1e-6 and abs(before[1] - after[1]) < 1e-6
    assert abs(v.z - 5.0) < 1e-9
    v.zoom_at(0.001, 300, 120, 1000, 500)
    assert v.z == 1.0                                 # cannot zoom out past the whole world


def test_drag_to_supports_pinch_and_pan():
    v = mapdata.View(4.0, 10.0, 10.0)
    lon, lat = v.to_lonlat(400, 200, 1000, 500)       # map point under the first finger
    v.drag_to(lon, lat, 500, 250, 1000, 500, z=8.0)   # finger moved and fingers spread
    assert abs(v.z - 8.0) < 1e-9
    assert all(abs(a - b) < 1e-9 for a, b in zip(v.to_xy(lon, lat, 1000, 500), (500, 250)))


def test_maidenhead_cells_label_matches_geo():
    cells = mapdata.maidenhead_cells((-73.5, 41.2, -72.5, 41.9), 2)
    labels = {c[0] for c in cells}
    assert geo.latlon_to_grid(41.5, -73.0)[:4] in labels and "FN31" in labels
    fields = mapdata.maidenhead_cells((-180, -90, 180, 90), 1)
    assert len(fields) == 18 * 18 and fields[0][0] == "AA" and fields[-1][0] == "RR"


def test_detail_data_loads():
    assert len(mapdata.shapes("land50")) > 1000 and len(mapdata.shapes("lakes50")) > 100
    assert len(mapdata.shapes("borders")) > 100 and len(mapdata.shapes("states")) > 100
    bb, flat = mapdata.shapes("states")[0]
    assert bb[0] <= bb[2] and len(flat) % 2 == 0
    names = {c[0] for c in mapdata.cities()}
    assert {"Tokyo", "Raleigh"} <= names


def test_night_outline_limited_range():
    pts, _ = mapdata.night_outline(datetime(2026, 10, 15, 12, tzinfo=timezone.utc), 0.5, (-80.0, -70.0))
    assert abs(pts[0][0] + 80) < 1e-9 and abs(pts[-1][0] + 70) < 1e-9 and len(pts) >= 20


def test_reach_grid_bounds_and_alignment():
    sw = spaceweather.SpaceWeather(sfi=130, ssn=85, kp=2, xray_flux=1e-7)
    dt = datetime(2026, 10, 15, 17, tzinfo=timezone.utc)
    full = predict.reach_grid(41.7, -72.7, 14.2, dt, sw, step=6)
    part = predict.reach_grid(41.7, -72.7, 14.2, dt, sw, step=6, bounds=(-100, 20, -60, 50))
    assert part and len(part) < len(full)
    assert all(-103 <= c[1] <= -57 and 17 <= c[0] <= 53 for c in part)
    fset = {(c[0], c[1]) for c in full}
    assert all((c[0], c[1]) in fset for c in part)         # same cell centres as the world grid
    fine = predict.reach_grid(41.7, -72.7, 7.15, dt, sw, step=0.5, bounds=(-75, 40, -71, 43))   # 40m: nearby cells are open
    assert fine and all(abs((c[0] / 0.5) - round(c[0] / 0.5 - 0.5) - 0.5) < 1e-6 for c in fine)
