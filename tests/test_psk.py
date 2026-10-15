from datetime import datetime, timezone

from hfprop import predict, psk, spaceweather

XML = """<?xml version="1.0"?>
<receptionReports currentSeconds="1792079500">
  <receptionReport receiverCallsign="K1RA" receiverLocator="FM18cr50" senderCallsign="N0NJY" senderLocator="FN31PR47AB" frequency="10130648" flowStartSeconds="1792079100" mode="JS8" isSender="1" isReceiver="0" sNR="-16"/>
  <receptionReport receiverCallsign="N0NJY" receiverLocator="FN31PR" senderCallsign="G4ABC" senderLocator="IO91" frequency="14074000" flowStartSeconds="1792079000" mode="FT8" isSender="0" isReceiver="1" sNR="-12"/>
  <receptionReport receiverCallsign="X1X" receiverLocator="" senderCallsign="N0NJY" senderLocator="FN31" frequency="14074000" flowStartSeconds="1792079000" mode="FT8" isSender="1" sNR="-3"/>
  <receptionReport receiverCallsign="Y2Y" receiverLocator="JN58" senderCallsign="N0NJY" senderLocator="FN31" frequency="3000000" flowStartSeconds="1792079000" mode="FT8" isSender="1" sNR="-3"/>
  <activeCallsign callsign="WD0BGZ" reports="1"/>
</receptionReports>"""
ME = (41.7, -72.7)
NOW = 1792079500


def test_band_of():
    assert psk.band_of(14074000) == "20m" and psk.band_of(10130648) == "30m"
    assert psk.band_of(3000000) is None


def test_parse_directions_and_drops_unusable_reports():
    rows = psk.parse(XML)
    assert [(r["call"], r["heard_me"], r["band"]) for r in rows] == [("K1RA", True, "30m"), ("G4ABC", False, "20m")]
    assert abs(rows[1]["lat"] - 51.5) < 1.0 and abs(rows[1]["lon"] + 1.0) < 2.0     # IO91 = southern England


def test_select_and_aggregate():
    rows = psk.parse(XML)
    assert len(psk.select(rows, NOW, 3600)) == 2
    assert len(psk.select(rows, NOW, 3600, dirs=("heard_me",))) == 1
    assert psk.select(rows, NOW, 3600, modes=("CW",)) == []
    assert len(psk.select(rows, NOW, 3600, band="20m")) == 1
    assert psk.select(rows, NOW + 99999, 3600) == []
    st = psk.stations(rows, *ME)
    assert {s["call"] for s in st} == {"K1RA", "G4ABC"}
    uk = next(s for s in st if s["call"] == "G4ABC")
    assert uk["i_heard"] and not uk["heard_me"] and uk["km"] > 5000 and uk["bands"] == ["20m"]
    assert psk.mode_counts(rows) == {"JS8": 1, "FT8": 1}


def test_agreement_counts_model_verdicts():
    rows = psk.parse(XML)
    sw = spaceweather.SpaceWeather(sfi=130, ssn=85, kp=2, xray_flux=1e-7)
    out = psk.agreement(rows, ME[0], ME[1], sw, predict.Station())
    assert out["total"] == 2 and 0 <= out["agree"] <= 2
    assert out["agree"] + len(out["misses"]) == 2
