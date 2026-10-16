"""Detailed space weather for the Space Wx page: NOAA scales, solar wind, flares, Kp,
alerts, CME/forecast discussion.  Every fetch fails soft (returns None) and is cached
on disk, so the page shows the last good data when offline."""
import json
import re
import time
import urllib.request

from .storage import cache_path

BASE = "https://services.swpc.noaa.gov/"
UA = {"User-Agent": "hfprop/0.1"}
TTL = 300   # seconds; NOAA updates every 1-5 minutes, no need to hammer it


def _open(url, headers=None, timeout=15):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    return urllib.request.urlopen(req, timeout=timeout)


def _cached(name, fetch, ttl=TTL, offline=False):
    """Return (data, age_seconds). Uses the cache while fresh, refetches when stale,
    and falls back to stale cache when the network fails."""
    path = cache_path(f"swx_{name}.json")
    cached = None
    try:
        cached = json.loads(path.read_text())
    except Exception:
        pass
    if cached and time.time() - cached["t"] < ttl:
        return cached["data"], time.time() - cached["t"]
    if not offline:
        try:
            data = fetch()
            path.write_text(json.dumps({"t": time.time(), "data": data}))
            return data, 0.0
        except Exception:
            pass
    if cached:
        return cached["data"], time.time() - cached["t"]
    return None, None


def _json(path):
    with _open(BASE + path) as r:
        return json.load(r)


def _text(path):
    with _open(BASE + path) as r:
        return r.read().decode("utf-8", "replace")


def _head_objects(path, nbytes):
    """Newest-first JSON array: read only the first nbytes and decode whole objects."""
    with _open(BASE + path, {"Range": f"bytes=0-{nbytes}"}) as r:
        txt = r.read().decode("utf-8", "ignore")
    return parse_objects(txt)


def parse_objects(txt):
    dec, i, out = json.JSONDecoder(), txt.index("[") + 1, []
    while True:
        while i < len(txt) and txt[i] in ", \n\r":
            i += 1
        try:
            obj, i = dec.raw_decode(txt, i)
        except Exception:
            break          # truncated final object
        out.append(obj)
    return out


# ---------- scales ----------
SCALE_TEXT = {
    "R": ["none", "Minor: weak HF fade on the sunlit side, a few minutes",
          "Moderate: limited HF blackout on the sunlit side, ~10s of minutes",
          "Strong: wide-area HF blackout on the sunlit side, ~1 hour",
          "Severe: HF blackout on most of the sunlit side for 1-2 hours",
          "Extreme: complete HF blackout on the entire sunlit side for hours"],
    "S": ["none", "Minor: minor polar-cap HF absorption", "Moderate: small effects on polar HF",
          "Strong: degraded polar HF", "Severe: polar HF essentially unusable",
          "Extreme: HF blackout over the polar regions"],
    "G": ["none", "Minor: weak power-grid fluctuations, aurora at high latitudes",
          "Moderate: aurora to ~55 deg; HF fades at high latitudes",
          "Strong: aurora to ~50 deg; HF degraded at higher latitudes",
          "Severe: HF problems at mid and high latitudes for hours",
          "Extreme: HF largely unusable at higher latitudes for days"],
}


def parse_scales(raw):
    """-> {'now': {R,S,G ints}, 'day1': {...}, 'day2':..., 'day3':...}"""
    def grab(k):
        d = raw[k]
        return {x: int(d[x]["Scale"] or 0) for x in "RSG"}
    return {"now": grab("0"), "day1": grab("1"), "day2": grab("2"), "day3": grab("3")}


def get_scales(offline=False):
    data, age = _cached("scales", lambda: parse_scales(_json("products/noaa-scales.json")), offline=offline)
    return data


# ---------- solar wind ----------
def parse_wind(mag, wind):
    """Primary-spacecraft series, oldest->newest: [{t, bz, bt, speed, density}]."""
    def active(rows):
        a = [r for r in rows if r.get("active")]
        return a or [r for r in rows if r.get("source") == rows[0].get("source")]
    by_t = {}
    for r in active(mag):
        by_t.setdefault(r["time_tag"][:16], {})["bz"] = r.get("bz_gsm")
        by_t[r["time_tag"][:16]]["bt"] = r.get("bt")
    for r in active(wind):
        by_t.setdefault(r["time_tag"][:16], {})["speed"] = r.get("proton_speed")
        by_t[r["time_tag"][:16]]["density"] = r.get("proton_density")
    return [{"t": t, **v} for t, v in sorted(by_t.items())]


def latest(wind, key):
    """Newest value of `key` in a solar-wind series. The plasma fields (speed, density) arrive a minute or
    two after the magnetic field, so the very last point often lacks them."""
    return next((w[key] for w in reversed(wind or []) if w.get(key) is not None), None)


def get_solar_wind(offline=False):
    def fetch():
        return parse_wind(_head_objects("json/rtsw/rtsw_mag_1m.json", 90000),
                          _head_objects("json/rtsw/rtsw_wind_1m.json", 150000))
    data, age = _cached("wind", fetch, offline=offline)
    return data


# ---------- flares / x-ray ----------
def get_xray(offline=False):
    """Long-channel (0.1-0.8 nm) flux for the last 6 h: [[unix_minutes_ago, flux]]."""
    def fetch():
        rows = [r for r in _json("json/goes/primary/xrays-6-hour.json") if r["energy"] == "0.1-0.8nm"]
        return [[r["time_tag"], r["flux"]] for r in rows][::5]      # every 5 min
    data, age = _cached("xray", fetch, offline=offline)
    return data


def get_flare_probs(offline=False):
    def fetch():
        rows = _json("json/solar_probabilities.json")[:3]
        return [{"date": r["date"][:10], "C": r["c_class_1_day"], "M": r["m_class_1_day"],
                 "X": r["x_class_1_day"], "proton": r.get("10mev_protons_1_day")} for r in rows]
    data, age = _cached("flareprob", fetch, ttl=3600, offline=offline)
    return data


# ---------- Kp ----------
def get_kp(offline=False):
    """Observed + forecast Kp, 3-hour steps: [{t, kp, observed}]."""
    def fetch():
        rows = _json("products/noaa-planetary-k-index-forecast.json")
        return [{"t": r["time_tag"], "kp": float(r["kp"]), "observed": r["observed"] == "observed"}
                for r in rows][-40:]
    data, age = _cached("kp", fetch, ttl=900, offline=offline)
    return data


# ---------- alerts ----------
_KIND = re.compile(r"^(ALERT|WARNING|WATCH|SUMMARY|EXTENDED WARNING|CANCEL WARNING)\s*:\s*(.+)$", re.M)


def parse_alerts(rows, limit=10):
    out = []
    for r in rows[:60]:
        msg = r.get("message", "").replace("\r", "")
        m = _KIND.search(msg)
        if not m:
            continue
        out.append({"time": r.get("issue_datetime", "")[:16], "kind": m.group(1).title(),
                    "title": m.group(2).strip(), "text": msg.strip()})
        if len(out) >= limit:
            break
    return out


def get_alerts(offline=False):
    data, age = _cached("alerts", lambda: parse_alerts(_json("products/alerts.json")), ttl=600, offline=offline)
    return data


# ---------- discussion (flares, CMEs, solar wind outlook) ----------
def parse_discussion(txt):
    """Split the SWPC forecast discussion into {issued, sections:{name:text}}."""
    issued = re.search(r":Issued:\s*(.+)", txt)
    secs, cur, buf = {}, None, []
    for line in txt.splitlines():
        if line.startswith((":", "#")):
            continue
        if line.strip() in ("Solar Activity", "Energetic Particle", "Solar Wind", "Geospace"):
            if cur:
                secs[cur] = "\n".join(buf).strip()
            cur, buf = line.strip(), []
        elif cur:
            buf.append(line)
    if cur:
        secs[cur] = "\n".join(buf).strip()
    return {"issued": issued.group(1).strip() if issued else "", "sections": secs}


def cme_mentions(section_text):
    """Sentences about CMEs / filaments / eruptions, joined, for a highlighted box."""
    flat = " ".join(section_text.split())
    sentences = re.split(r"(?<=[.!?])\s+", flat)
    keep = [s for s in sentences if re.search(r"\bCME|coronal mass|filament|erupt|halo|Earth-directed", s, re.I)]
    return " ".join(keep)


def get_discussion(offline=False):
    data, age = _cached("discussion", lambda: parse_discussion(_text("text/discussion.txt")),
                        ttl=1800, offline=offline)
    return data


IMAGES = {
    "lasco_c2": BASE + "images/animations/lasco-c2/latest.jpg",
    "lasco_c3": BASE + "images/animations/lasco-c3/latest.jpg",
    "enlil": BASE + "images/animations/enlil/latest.jpg",
}


def fetch_all(offline=False):
    return {"scales": get_scales(offline), "wind": get_solar_wind(offline), "xray": get_xray(offline),
            "flares": get_flare_probs(offline), "kp": get_kp(offline), "alerts": get_alerts(offline),
            "discussion": get_discussion(offline)}
