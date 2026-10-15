"""Live space weather from NOAA SWPC, cached so the app works offline."""
import json
import time
import urllib.request
from dataclasses import dataclass, asdict

from .storage import cache_path

BASE = "https://services.swpc.noaa.gov/"


@dataclass
class SpaceWeather:
    sfi: float = 120.0         # 10.7 cm solar flux
    ssn: float = 70.0          # equivalent sunspot number
    kp: float = 2.0            # planetary K-index (latest)
    a_index: float = 8.0
    xray_class: str = "A0.0"   # GOES long-channel class
    xray_flux: float = 1e-8    # W/m^2
    fetched: float = 0.0       # unix time of fetch; 0 = defaults, never fetched
    live: bool = False

    @property
    def age_hours(self):
        return (time.time() - self.fetched) / 3600 if self.fetched else float("inf")


def sfi_to_ssn(sfi):
    """Invert the standard SSN -> F10.7 relation (F = 63.7 + 0.728 R + 0.00089 R^2)."""
    lo, hi = 0.0, 400.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if 63.7 + 0.728 * mid + 0.00089 * mid * mid < sfi:
            lo = mid
        else:
            hi = mid
    return round((lo + hi) / 2, 1)


def xray_class(flux):
    if flux <= 0:
        return "A0.0"
    for letter, base in (("X", 1e-4), ("M", 1e-5), ("C", 1e-6), ("B", 1e-7), ("A", 1e-8)):
        if flux >= base:
            return f"{letter}{flux / base:.1f}"
    return f"A{flux / 1e-8:.1f}"


def _get(path):
    with urllib.request.urlopen(BASE + path, timeout=10) as r:
        return json.load(r)


def fetch_live():
    sw = SpaceWeather()
    flux = _get("json/f107_cm_flux.json")
    noon = [f for f in flux if f.get("reporting_schedule") == "Noon"]
    sw.sfi = float((noon or flux)[0]["flux"])
    sw.ssn = sfi_to_ssn(sw.sfi)
    k = _get("products/noaa-planetary-k-index.json")[-1]
    sw.kp, sw.a_index = float(k["Kp"]), float(k["a_running"])
    xr = [x for x in _get("json/goes/primary/xrays-1-day.json") if x["energy"] == "0.1-0.8nm"]
    if xr:
        sw.xray_flux = float(xr[-1]["flux"])
        sw.xray_class = xray_class(sw.xray_flux)
    sw.fetched, sw.live = time.time(), True
    return sw


def get_space_weather(max_age_hours=0.5, offline=False):
    """Fresh data if possible, else last cached copy, else sensible defaults."""
    cache = cache_path("spaceweather.json")
    cached = None
    try:
        cached = SpaceWeather(**json.loads(cache.read_text()))
    except Exception:
        pass
    if cached and cached.age_hours < max_age_hours:
        return cached
    if not offline:
        try:
            sw = fetch_live()
            cache.write_text(json.dumps(asdict(sw)))
            return sw
        except Exception:
            pass
    if cached:
        cached.live = False
        return cached
    return SpaceWeather()


def summarize(sw):
    """Plain-English one-liners for the UI."""
    if sw.sfi >= 150: flux = "excellent HF conditions (high bands should be open)"
    elif sw.sfi >= 110: flux = "good HF conditions (15m/12m/10m often open by day)"
    elif sw.sfi >= 85: flux = "fair HF conditions (20m best; 15m by day)"
    else: flux = "poor HF conditions (stay on 40m-20m)"
    if sw.kp >= 7: geo = "severe geomagnetic storm - HF largely disrupted at high latitudes"
    elif sw.kp >= 5: geo = "geomagnetic storm - expect degraded/auroral paths"
    elif sw.kp >= 4: geo = "unsettled field - polar paths flutter"
    else: geo = "quiet geomagnetic field"
    if sw.xray_flux >= 1e-4: xr = "X-class flare: daylit-side radio blackout likely"
    elif sw.xray_flux >= 1e-5: xr = "M-class flare: brief low-band absorption possible"
    else: xr = "no flare disruption"
    return {"solar flux": flux, "geomagnetic": geo, "x-ray": xr}
