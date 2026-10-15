import io
import json

import pytest

from hfprop import geo, spaceweather, summary

QUIET = {k: {"R": 0, "S": 0, "G": 0} for k in ("now", "day1", "day2", "day3")}


def sw(**kw):
    return spaceweather.SpaceWeather(**{"sfi": 120, "ssn": 70, "kp": 2.0, "xray_flux": 1e-7, "xray_class": "B1.0", **kw})


def scales(**now):
    d = json.loads(json.dumps(QUIET))
    d["now"].update(now)
    return d


def test_alerts_quiet():
    assert summary.alerts(sw(), QUIET) == (0, [])


def test_alerts_storm_blackout_and_forecast():
    lvl, msgs = summary.alerts(sw(kp=6.0), scales(G=2))
    assert lvl == 2 and any("G2" in m for m in msgs) and len(msgs) == 1   # no duplicate Kp message
    lvl, msgs = summary.alerts(sw(), scales(R=3))
    assert lvl == 3 and "R3" in msgs[0]
    fc = json.loads(json.dumps(QUIET)); fc["day2"]["G"] = 1
    lvl, msgs = summary.alerts(sw(), fc)
    assert lvl == 1 and "2 days" in msgs[0]
    assert summary.alerts(sw(kp=4.3), QUIET)[0] == 1
    assert summary.alerts(sw(), None) == (0, [])           # scales unavailable: still works


def test_open_now_and_next_openings():
    rows = [{"band": "20m", "overall": "GO", "go": [1] * 5}, {"band": "40m", "overall": "GO", "go": [1] * 9},
            {"band": "10m", "overall": "MARGINAL", "go": []}, {"band": "6m", "overall": "NO-GO", "go": []}]
    go, marg = summary.open_now(rows)
    assert go == [("40m", 9), ("20m", 5)] and marg == ["10m"]
    strip = {"start_hour": 22, "grid": {"20m": ["GO"] * 3, "15m": ["NO-GO", "NO-GO", "GO"], "10m": ["NO-GO", "MARGINAL", "NO-GO"],
                                         "80m": ["NO-GO", "GO", "GO"]}}
    assert summary.next_openings(strip) == [("80m", 1, 23), ("15m", 2, 0)]


def test_locate_by_ip(monkeypatch):
    class R(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): pass
    body = {"success": True, "latitude": 41.7, "longitude": -72.7, "city": "Newington", "region_code": "CT"}
    monkeypatch.setattr(geo.urllib.request, "urlopen", lambda *a, **k: R(json.dumps(body).encode()))
    assert geo.locate_by_ip() == (41.7, -72.7, "Newington, CT")
    monkeypatch.setattr(geo.urllib.request, "urlopen", lambda *a, **k: R(b'{"success": false}'))
    with pytest.raises(ValueError):
        geo.locate_by_ip()
