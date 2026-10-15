"""Real reception reports from PSK Reporter ("who heard me / whom I heard").

One request per callsign is cached for 5 minutes (PSK Reporter asks clients to be gentle);
all filtering by time window, direction, mode and band happens locally.
"""
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone

from . import predict
from .geo import bearing_deg, distance_km, grid_to_latlon
from .storage import cache_path

URL = "https://retrieve.pskreporter.info/query"
TTL = 300
FETCH_SECONDS = 86400

_EDGES = [(1.8, 2.0, "160m"), (3.5, 4.0, "80m"), (5.25, 5.45, "60m"), (7.0, 7.3, "40m"),
          (10.1, 10.15, "30m"), (14.0, 14.35, "20m"), (18.068, 18.168, "17m"), (21.0, 21.45, "15m"),
          (24.89, 24.99, "12m"), (28.0, 29.7, "10m"), (50.0, 54.0, "6m")]
BAND_ORDER = [b for _, _, b in _EDGES]

# decode thresholds, dB in a 2.5 kHz reference bandwidth (approximate)
MODE_SNR = {"FT8": -20.0, "FT4": -17.0, "FT2": -14.0, "JS8": -22.0, "WSPR": -28.0, "FST4": -22.0,
            "FST4W": -30.0, "Q65": -24.0, "JT65": -24.0, "JT9": -24.0, "MSK144": -18.0,
            "PSK31": -10.0, "PSK63": -8.0, "RTTY": 0.0, "CW": -3.0, "SSB": 6.0}
DEFAULT_SNR = -10.0


def band_of(freq_hz):
    mhz = freq_hz / 1e6
    for lo, hi, name in _EDGES:
        if lo <= mhz <= hi:
            return name
    return None


def _locator_latlon(loc):
    """Centre of the 6- (or 4-) character square at the start of a locator, or None."""
    loc = (loc or "").strip()
    for n in (6, 4):
        if len(loc) >= n and re.fullmatch(r"[A-Ra-r]{2}\d\d([A-Xa-x]{2})?", loc[:n]):
            try:
                return grid_to_latlon(loc[:n])
            except ValueError:
                return None
    return None


def parse(xml_text):
    """PSK Reporter XML -> list of dicts, one per report, relative to the queried callsign.

    isSender=1 means the queried station was *transmitting* (another station heard it)."""
    rows = []
    for rr in ET.fromstring(xml_text).iter("receptionReport"):
        a = rr.attrib
        mine_sent = a.get("isSender") == "1"
        mine_recv = a.get("isReceiver") == "1"
        if mine_sent == mine_recv and (mine_sent or "isSender" in a):
            continue                         # both or neither: not a clean one-way report
        other = a.get("receiverCallsign") if mine_sent else a.get("senderCallsign")
        loc = a.get("receiverLocator") if mine_sent else a.get("senderLocator")
        pos = _locator_latlon(loc)
        try:
            freq = float(a["frequency"])
            t = int(a["flowStartSeconds"])
        except (KeyError, ValueError):
            continue
        band = band_of(freq)
        if not other or not pos or not band:
            continue
        rows.append({"call": other, "lat": pos[0], "lon": pos[1], "grid": (loc or "")[:6],
                     "freq": freq, "band": band, "mode": a.get("mode", "?"),
                     "snr": float(a["sNR"]) if a.get("sNR") not in (None, "") else None,
                     "t": t, "heard_me": mine_sent})
    return rows


def fetch(callsign):
    q = urllib.parse.urlencode({"callsign": callsign, "rronly": 1, "flowStartSeconds": -FETCH_SECONDS,
                                "rptlimit": 3000})
    req = urllib.request.Request(f"{URL}?{q}", headers={"User-Agent": "hfprop/0.1"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return parse(r.read().decode("utf-8", "replace"))


def get_spots(callsign, offline=False, force=False):
    """-> (rows, age_seconds | None, error | None). Cached per callsign for TTL seconds."""
    call = callsign.strip().upper()
    if not call:
        return [], None, None
    path = cache_path("psk_" + re.sub(r"\W", "_", call) + ".json")
    cached = None
    try:
        cached = json.loads(path.read_text())
    except Exception:
        pass
    now = time.time()
    if cached and now - cached["t"] < TTL and not force and not offline:
        return cached["rows"], now - cached["t"], None
    if cached and now - cached["t"] < TTL and force:
        return cached["rows"], now - cached["t"], None       # never hit PSK more than once per TTL
    err = None
    if not offline:
        try:
            rows = fetch(call)
            path.write_text(json.dumps({"t": now, "rows": rows}))
            return rows, 0.0, None
        except Exception as ex:
            err = f"PSK Reporter unavailable ({type(ex).__name__})"
    if cached:
        return cached["rows"], now - cached["t"], err
    return [], None, err or "offline"


def select(rows, now, window_s, dirs=("heard_me", "i_heard"), modes=(), band=None):
    out = []
    for r in rows:
        if now - r["t"] > window_s:
            continue
        if ("heard_me" if r["heard_me"] else "i_heard") not in dirs:
            continue
        if modes and r["mode"] not in modes:
            continue
        if band and r["band"] != band:
            continue
        out.append(r)
    return out


def mode_counts(rows):
    return Counter(r["mode"] for r in rows)


def stations(rows, my_lat, my_lon):
    """Collapse reports to one entry per distant station for the map and list."""
    by = {}
    for r in rows:
        s = by.setdefault(r["call"], {"call": r["call"], "lat": r["lat"], "lon": r["lon"], "grid": r["grid"],
                                      "heard_me": False, "i_heard": False, "bands": set(), "modes": set(),
                                      "best_snr": None, "last": 0, "n": 0})
        s["heard_me" if r["heard_me"] else "i_heard"] = True
        s["bands"].add(r["band"])
        s["modes"].add(r["mode"])
        s["n"] += 1
        s["last"] = max(s["last"], r["t"])
        if r["snr"] is not None and (s["best_snr"] is None or r["snr"] > s["best_snr"]):
            s["best_snr"] = r["snr"]
    out = []
    for s in by.values():
        s["km"] = distance_km(my_lat, my_lon, s["lat"], s["lon"])
        s["bearing"] = bearing_deg(my_lat, my_lon, s["lat"], s["lon"])
        s["bands"] = sorted(s["bands"], key=BAND_ORDER.index)
        s["modes"] = sorted(s["modes"])
        out.append(s)
    return sorted(out, key=lambda s: -s["last"])


def agreement(rows, my_lat, my_lon, sw, st=None):
    """How well the propagation model matches real reports.

    For each distinct (station, band, mode, direction) the latest report is compared with the
    model's verdict for that path/frequency/time/mode. A report counts as an agreement when
    the model said GO or MARGINAL. Space weather is today's, an approximation for older spots.
    """
    st = st or predict.Station()
    latest = {}
    for r in rows:
        k = (r["call"], r["band"], r["mode"], r["heard_me"])
        if k not in latest or r["t"] > latest[k]["t"]:
            latest[k] = r
    agree, miss = 0, []
    for r in latest.values():
        if r["heard_me"]:
            tx = st.power_w
        else:
            tx = 50.0                                         # unknown remote power
        s = predict.Station(power_w=tx, gain_dbi=st.gain_dbi, noise=st.noise,
                            snr_needed=MODE_SNR.get(r["mode"], DEFAULT_SNR))
        dt = datetime.fromtimestamp(r["t"], timezone.utc)
        state, snr, det = predict.link(my_lat, my_lon, r["lat"], r["lon"], r["freq"] / 1e6, dt,
                                       sw.ssn, sw.kp, sw.xray_flux, s)
        if state == predict.NOGO:
            miss.append({"call": r["call"], "band": r["band"], "mode": r["mode"],
                         "km": det["dist"], "muf": det["muf"]})
        else:
            agree += 1
    return {"total": len(latest), "agree": agree, "misses": miss}
