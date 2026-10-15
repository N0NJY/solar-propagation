"""Band-by-band GO / MARGINAL / NO-GO from your location to anywhere."""
import math
from dataclasses import dataclass

from . import iono, solar
from .geo import distance_km, bearing_deg
from .targets import TARGETS

BANDS = [("160m", 1.9), ("80m", 3.7), ("60m", 5.35), ("40m", 7.15), ("30m", 10.12),
         ("20m", 14.2), ("17m", 18.1), ("15m", 21.2), ("12m", 24.9), ("10m", 28.5),
         ("6m", 50.2)]

GO, MARGINAL, NOGO = "GO", "MARGINAL", "NO-GO"


@dataclass
class Station:
    power_w: float = 100.0
    gain_dbi: float = 0.0        # per antenna (tx and rx)
    snr_needed: float = 6.0      # dB in 2.5 kHz; ~6 SSB, ~-3 CW, ~-18 FT8
    noise: str = "residential"   # quiet | residential | city


_FAM_C = {"quiet": 53.6, "residential": 68.0, "city": 76.8}
_FAM_D = {"quiet": 28.6, "residential": 27.7, "city": 27.7}


def noise_dbm(freq, night, kind="residential"):
    """Receiver noise power in 2.5 kHz (dBm): max(man-made, atmospheric) over kTb."""
    man = _FAM_C[kind] - _FAM_D[kind] * math.log10(freq)
    atm = (68.0 if night else 52.0) - 27.0 * math.log10(freq) + 4.0
    fa = max(man, atm)
    return -140.0 + fa


def link(lat1, lon1, lat2, lon2, freq, dt, ssn, kp, xray, st: Station):
    """Evaluate one frequency over one path. Returns (state, snr_db, detail)."""
    p = iono.muf(lat1, lon1, lat2, lon2, dt, ssn, kp)
    n, hop = p["hops"], p["hop_km"]
    night = min(p["chis"]) > 98
    detail = {"muf": p["muf"], "hops": n, "dist": p["dist"]}
    if freq > p["muf"] * 1.10:
        return NOGO, -99.0, detail
    path_loss = n * iono.hop_slant_km(hop)
    fspl = 32.45 + 20 * math.log10(freq) + 20 * math.log10(max(path_loss, 1.0))
    absorp = sum(iono.absorption_db(freq, c, p["phi"], ssn, xray) for c in p["chis"])
    ground = 2.0 * (n - 1)
    other = 5.0 + (6.0 if freq > p["muf"] else 0.0)   # polarisation, focusing, over-MUF
    tx_dbm = 10 * math.log10(st.power_w * 1000.0)
    rx = tx_dbm + 2 * st.gain_dbi - fspl - absorp - ground - other
    snr = rx - noise_dbm(freq, night, st.noise)
    detail.update(absorption=absorp, rx_dbm=rx)
    margin = snr - st.snr_needed
    if freq > p["muf"] * 0.97 and margin > -3:
        state = MARGINAL   # at/above the median MUF: open only some days
    elif margin >= 0:
        state = GO
    elif margin >= -6:
        state = MARGINAL
    else:
        state = NOGO
    return state, snr, detail


def band_table(lat, lon, dt, sw, st=None, targets=TARGETS):
    """For each band: state counts, reachable targets, best/worst."""
    st = st or Station()
    rows = []
    for name, f in BANDS:
        go, marg = [], []
        for t in targets:
            tname, region, tlat, tlon = t
            d = distance_km(lat, lon, tlat, tlon)
            if d < 50:
                continue
            state, snr, det = link(lat, lon, tlat, tlon, f, dt, sw.ssn, sw.kp, sw.xray_flux, st)
            entry = {"target": tname, "region": region, "snr": snr, "km": d,
                     "bearing": bearing_deg(lat, lon, tlat, tlon), "hops": det["hops"]}
            (go if state == GO else marg if state == MARGINAL else []).append(entry)
        total = len(go) + len(marg)
        if len(go) >= 3: overall = GO
        elif go or len(marg) >= 3: overall = MARGINAL
        else: overall = NOGO
        rows.append({"band": name, "freq": f, "overall": overall, "go": go, "marginal": marg})
    return rows


def target_bands(lat, lon, target, dt, sw, st=None):
    """Every band's state from the user to one target (name, region, lat, lon)."""
    st = st or Station()
    out = []
    for name, f in BANDS:
        state, snr, det = link(lat, lon, target[2], target[3], f, dt, sw.ssn, sw.kp, sw.xray_flux, st)
        out.append({"band": name, "state": state, "snr": snr, "muf": det["muf"]})
    return out


def reach_grid(lat, lon, freq, dt, sw, st=None, step=6, bounds=None):
    """Reachability for one frequency, for the map heat layer.

    Returns [(cell_lat, cell_lon, state, margin_db)] for every cell centre that is GO or
    MARGINAL. margin_db is the signal margin over what is needed (bigger = stronger).
    `step` is the cell size in degrees; `bounds` = (lon_min, lat_min, lon_max, lat_max)
    limits the work to the visible area. Cells are aligned to multiples of `step`, so they
    do not shift while panning.
    """
    st = st or Station()
    x0, y0, x1, y1 = bounds or (-180.0, -90.0, 180.0, 90.0)
    x0, y0, x1, y1 = max(-180.0, x0), max(-90.0, y0), min(180.0, x1), min(90.0, y1)
    cells = []
    j = int(math.floor(y0 / step))
    while True:
        la = (j + 0.5) * step
        if la - step / 2 > y1:
            break
        if -90 < la < 90:
            i = int(math.floor(x0 / step))
            while True:
                lo = (i + 0.5) * step
                if lo - step / 2 > x1:
                    break
                if -180 < lo < 180 and distance_km(lat, lon, la, lo) >= 50:
                    state, snr, _ = link(lat, lon, la, lo, freq, dt, sw.ssn, sw.kp, sw.xray_flux, st)
                    if state != NOGO:
                        cells.append((la, lo, state, snr - st.snr_needed))
                i += 1
        j += 1
    return cells


def day_strip(lat, lon, start, sw, st=None, hours=24, targets=TARGETS):
    """Band outlook: {band: [overall state for each of the next `hours` hours]}.

    `start` should be a timezone-aware datetime already floored to the hour."""
    from datetime import timedelta
    out = {name: [] for name, _ in BANDS}
    for h in range(hours):
        for row in band_table(lat, lon, start + timedelta(hours=h), sw, st, targets):
            out[row["band"]].append(row["overall"])
    return out
