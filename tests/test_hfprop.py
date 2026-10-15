from datetime import datetime, timezone

import pytest

from hfprop import geo, predict, spaceweather

FN31 = (41.5, -73.0)
UK, TX, BR, EAST = (51.5, -0.1), (30.3, -97.7), (-23.5, -46.6), (40.7, -74.0)


def at(h):
    return datetime(2026, 10, 14, h, 0, tzinfo=timezone.utc)


def state(to, f, h, ssn=90):
    return predict.link(*FN31, *to, f, at(h), ssn, 2, 1e-7, predict.Station())[0]


def test_grid_roundtrip():
    lat, lon = geo.grid_to_latlon("FN31pr")
    assert geo.latlon_to_grid(lat, lon) == "FN31pr"
    assert abs(lat - 41.73) < 0.05 and abs(lon + 72.7) < 0.1


def test_parse_location_forms():
    assert geo.parse_location("FN31")[2] == "FN31"
    lat, lon, _ = geo.parse_location("40.7,-74.0")
    assert (lat, lon) == (40.7, -74.0)
    with pytest.raises(ValueError):
        geo.parse_location("hello")


def test_sfi_to_ssn_monotonic():
    assert spaceweather.sfi_to_ssn(67) < 5
    assert 80 < spaceweather.sfi_to_ssn(136) < 100


def test_xray_class():
    assert spaceweather.xray_class(5e-6) == "C5.0"
    assert spaceweather.xray_class(2e-5).startswith("M")


def test_day_night_behaviour():
    assert state(UK, 14.2, 17) == predict.GO          # 20m to Europe at midday
    assert state(UK, 7.15, 17) == predict.NOGO        # 40m long-haul dies by day
    assert state(UK, 7.15, 6) != predict.NOGO         # ...but opens at night
    assert state(BR, 28.5, 5) == predict.NOGO         # 10m closed at night
    assert state(TX, 3.7, 17) == predict.NOGO         # 80m 2500 km at noon
    assert state(TX, 3.7, 5) == predict.GO            # ...and open at night


def test_6m_closed_at_moderate_solar_flux():
    assert state(UK, 50.2, 17) == predict.NOGO


def test_high_sfi_opens_10m():
    assert state(UK, 28.5, 17, ssn=150) != predict.NOGO
    assert state(UK, 28.5, 17, ssn=20) == predict.NOGO


def test_land_data_and_night_outline():
    from hfprop import mapdata
    rings = mapdata.land_rings()
    assert len(rings) > 100 and all(len(r) % 2 == 0 for r in rings)
    pts, dark = mapdata.night_outline(at(12))
    assert len(pts) == 91 and dark in ("N", "S")
    assert dark == "N"      # October: sun south of the equator -> night edge on the north side


def test_great_circle_splits_at_dateline():
    from hfprop import mapdata
    segs = mapdata.great_circle(*FN31, 35.7, 139.7)
    assert len(segs) == 2
    assert all(abs(a[0] - b[0]) < 180 for seg in segs for a, b in zip(seg, seg[1:]))


def test_target_bands_covers_all_bands():
    sw = spaceweather.SpaceWeather(sfi=120, ssn=70, kp=2, xray_flux=1e-7)
    out = predict.target_bands(*FN31, ("UK", "Europe", 51.5, -0.1), at(17), sw)
    assert [r["band"] for r in out] == [b for b, _ in predict.BANDS]
    assert {r["state"] for r in out} <= {predict.GO, predict.MARGINAL, predict.NOGO}


def test_reach_grid_day_night_and_bounds():
    sw = spaceweather.SpaceWeather(sfi=120, ssn=70, kp=2, xray_flux=1e-7)
    day = predict.reach_grid(*FN31, 14.2, at(17), sw, step=10)
    night10 = predict.reach_grid(*FN31, 28.5, at(5), sw, step=10)
    assert day and all(-90 < c[0] < 90 and -180 < c[1] < 180 for c in day)
    assert {c[2] for c in day} <= {predict.GO, predict.MARGINAL}
    assert len(night10) < len(day) / 4          # 10m is mostly shut at night


def test_day_strip_shape_and_diurnal_pattern():
    sw = spaceweather.SpaceWeather(sfi=130, ssn=85, kp=2, xray_flux=1e-7)
    strip = predict.day_strip(*FN31, at(0), sw, hours=24)
    assert set(strip) == {b for b, _ in predict.BANDS} and all(len(v) == 24 for v in strip.values())
    ten = strip["10m"]            # high band: daytime only (FN31 is UTC-5; local noon ~ 17 UTC)
    assert ten[17] != predict.NOGO and ten[5] == predict.NOGO
    eighty = strip["80m"]         # low band: night opens, midday shut for long range
    assert eighty[6] != predict.NOGO


def test_extended_grid_squares():
    lat, lon, label = geo.parse_location("FN31PR47AB")
    assert label == "FN31pr47ab"
    assert abs(lat - 41.7292) < 1e-3 and abs(lon + 72.7083) < 1e-3
    for g in ("FN31", "FN31pr", "FN31pr47", "FN31pr47ab"):
        assert geo.latlon_to_grid(*geo.grid_to_latlon(g), chars=len(g)) == g
