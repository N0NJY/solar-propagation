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
