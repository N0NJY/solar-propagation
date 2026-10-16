import json

from hfprop import swx


def test_parse_objects_drops_truncated_tail():
    txt = '[{"a": 1}, {"a": 2}, {"a": 3, "b": "tru'
    assert swx.parse_objects(txt) == [{"a": 1}, {"a": 2}]


def test_parse_wind_prefers_active_spacecraft_and_sorts_oldest_first():
    mag = [{"time_tag": "2026-10-15T10:02:01", "source": "IMAP", "active": False, "bz_gsm": 9, "bt": 9},
           {"time_tag": "2026-10-15T10:02:00", "source": "DSCOVR", "active": True, "bz_gsm": -6, "bt": 7},
           {"time_tag": "2026-10-15T10:01:00", "source": "DSCOVR", "active": True, "bz_gsm": -5, "bt": 7}]
    wind = [{"time_tag": "2026-10-15T10:02:00", "source": "DSCOVR", "active": True,
             "proton_speed": 500.0, "proton_density": 3.0}]
    rows = swx.parse_wind(mag, wind)
    assert [r["t"] for r in rows] == ["2026-10-15T10:01", "2026-10-15T10:02"]
    assert rows[-1]["bz"] == -6 and rows[-1]["speed"] == 500.0


def test_parse_scales():
    raw = {k: {"R": {"Scale": "0"}, "S": {"Scale": "1"}, "G": {"Scale": None}} for k in "0123"}
    assert swx.parse_scales(raw)["now"] == {"R": 0, "S": 1, "G": 0}


def test_parse_alerts_keeps_only_recognised_messages():
    rows = [{"issue_datetime": "2026-10-13 20:58:58.7",
             "message": "Space Weather Message Code: WARK04\r\nWARNING: Geomagnetic K-index of 4 expected\r\nx"},
            {"issue_datetime": "2026-10-13 10:00:00", "message": "no recognisable heading here"}]
    out = swx.parse_alerts(rows)
    assert len(out) == 1 and out[0]["kind"] == "Warning" and "K-index of 4" in out[0]["title"]


DISC = """:Product: Forecast Discussion
:Issued: 2026 Oct 15 1230 UTC
#
Solar Activity

.24 hr Summary...
Activity was low. A large filament erupted at 14/1200 UTC. An associated CME was seen in LASCO C2.
It will pass above Earth.

Solar Wind

.24 hr Summary...
Elevated.
"""


def test_discussion_and_cme_mentions():
    d = swx.parse_discussion(DISC)
    assert d["issued"] == "2026 Oct 15 1230 UTC"
    assert set(d["sections"]) == {"Solar Activity", "Solar Wind"}
    m = swx.cme_mentions(d["sections"]["Solar Activity"])
    assert "CME" in m and "filament" in m and "Activity was low" not in m
    assert swx.cme_mentions(d["sections"]["Solar Wind"]) == ""


def test_cache_falls_back_to_stale_data_when_offline(tmp_path, monkeypatch):
    monkeypatch.setenv("HFPROP_DATA", str(tmp_path))
    (tmp_path / "swx_demo.json").write_text(json.dumps({"t": 1.0, "data": {"ok": True}}))
    def boom():
        raise OSError("no network")
    data, age = swx._cached("demo", boom)
    assert data == {"ok": True} and age > 1000
    assert swx._cached("missing", boom) == (None, None)


def test_latest_skips_missing_plasma_fields():
    wind = [{"t": "a", "bz": -3.0, "speed": 450.0}, {"t": "b", "bz": -4.0, "bt": 5.0}]
    assert swx.latest(wind, "speed") == 450.0
    assert swx.latest(wind, "bz") == -4.0
    assert swx.latest(wind, "density") is None and swx.latest([], "bz") is None
