"""Empirical ionosphere: foF2, hop geometry, MUF and D-layer absorption.

Deliberately simple and dependency-free (runs anywhere, including Android).
Good for go/no-go planning; not a substitute for VOACAP/P.533 in detail.
"""
import math

from . import solar
from .geo import R_EARTH, distance_km, intermediate

H_F2 = 300.0       # km, effective F2 reflection height
MAX_HOP_KM = 4000.0
MAX_M = 3.8        # cap on the MUF obliquity factor


def fof2(lat, lon, dt, ssn, kp=2.0):
    """Median F2 critical frequency (MHz) at a point and time."""
    chi = solar.zenith_angle(lat, lon, dt)
    day_peak = 4.6 + 0.055 * ssn
    # day: cos^0.3 of the zenith angle; night: floor ~0.45 of the daytime peak,
    # smoothed across the terminator.
    if chi < 90:
        day = max(0.0, math.cos(math.radians(chi))) ** 0.3
    else:
        day = 0.0
    night_floor = 0.42
    f = day_peak * (night_floor + (1 - night_floor) * day)
    # latitude: falls toward the poles, equatorial anomaly bump near +-15 deg
    al = abs(lat)
    f *= 1.0 - 0.45 * (al / 90.0) ** 2.2
    if day > 0.3:
        f *= 1.0 + 0.12 * math.exp(-((al - 15.0) / 10.0) ** 2)
    # winter anomaly: slightly higher in local winter by day
    dec, _ = solar.sun_declination_ra(dt)
    winter = math.sin(math.radians(lat)) * math.sin(dec) < 0   # sun in the other hemisphere
    f *= 1.0 + (0.04 * day if winter else 0.0)
    # geomagnetic storm depression, stronger toward the poles
    if kp > 3:
        f *= 1.0 - min(0.5, 0.05 * (kp - 3) * (0.4 + al / 90.0))
    return max(f, 1.5)


def hop_incidence(hop_km, h=H_F2):
    """Incidence angle at the layer (radians) for a single hop of hop_km."""
    a = hop_km / 2.0 / R_EARTH
    return math.atan2(R_EARTH * math.sin(a), R_EARTH + h - R_EARTH * math.cos(a))


def hop_slant_km(hop_km, h=H_F2):
    a = hop_km / 2.0 / R_EARTH
    leg = math.sqrt(R_EARTH ** 2 + (R_EARTH + h) ** 2 - 2 * R_EARTH * (R_EARTH + h) * math.cos(a))
    return 2 * leg


def path_hops(dist_km):
    return max(1, math.ceil(dist_km / MAX_HOP_KM))


def muf(lat1, lon1, lat2, lon2, dt, ssn, kp=2.0):
    """Path MUF (MHz), absorption index inputs and geometry for the whole path.

    Control points: the middle of every hop. Returns dict.
    """
    dist = distance_km(lat1, lon1, lat2, lon2)
    n = path_hops(dist)
    hop = dist / n
    phi = hop_incidence(hop)
    m = min(MAX_M, 1.0 / math.cos(phi))
    mufs, chis = [], []
    for i in range(n):
        lat, lon = intermediate(lat1, lon1, lat2, lon2, (i + 0.5) / n)
        mufs.append(fof2(lat, lon, dt, ssn, kp) * m)
        chis.append(solar.zenith_angle(lat, lon, dt))
    return {"muf": min(mufs), "hops": n, "hop_km": hop, "phi": phi,
            "chis": chis, "dist": dist}


def absorption_db(freq, chi_deg, phi, ssn, xray_flux=0.0):
    """One-hop D-layer absorption (dB), simplified CCIR/ITU-R P.533 form."""
    # ionisation index: strong by day, near zero at night
    c = max(0.0, math.cos(math.radians(0.881 * min(chi_deg, 102.0)))) if chi_deg < 102 else 0.0
    iz = (1 + 0.0037 * ssn) * (c ** 1.3) + 0.04   # tiny night residual
    sec = min(1.0 / math.cos(min(phi, math.radians(84))), 8.0)
    fh = 1.2   # approx. gyrofrequency term
    a = 677.2 * iz * sec * 0.55 / ((freq + fh) ** 1.98 + 10.2)
    # flare-driven blackout on the sunlit side
    if xray_flux >= 1e-5 and chi_deg < 85:
        a *= 1.0 + min(6.0, math.log10(xray_flux / 1e-5) * 3 + 1)
    return a
