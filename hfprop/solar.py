"""Sun position: declination, zenith angle, day/night."""
import math
from datetime import datetime, timezone


def _julian_days(dt):
    return dt.timestamp() / 86400.0 + 2440587.5 - 2451545.0


def sun_declination_ra(dt):
    n = _julian_days(dt)
    L = math.radians((280.460 + 0.9856474 * n) % 360)
    g = math.radians((357.528 + 0.9856003 * n) % 360)
    lam = L + math.radians(1.915) * math.sin(g) + math.radians(0.020) * math.sin(2 * g)
    eps = math.radians(23.439 - 0.0000004 * n)
    dec = math.asin(math.sin(eps) * math.sin(lam))
    ra = math.atan2(math.cos(eps) * math.sin(lam), math.cos(lam))
    return dec, ra


def subsolar_point(dt):
    dec, ra = sun_declination_ra(dt)
    gmst = math.radians((280.46061837 + 360.98564736629 * _julian_days(dt)) % 360)
    lon = math.degrees(ra - gmst)
    lon = (lon + 180) % 360 - 180
    return math.degrees(dec), lon


def zenith_angle(lat, lon, dt):
    """Solar zenith angle in degrees (90 = horizon, >90 = night)."""
    dec, ra = sun_declination_ra(dt)
    gmst = math.radians((280.46061837 + 360.98564736629 * _julian_days(dt)) % 360)
    ha = gmst + math.radians(lon) - ra
    p = math.radians(lat)
    c = math.sin(p) * math.sin(dec) + math.cos(p) * math.cos(dec) * math.cos(ha)
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def terminator_lat(lon, dt):
    """Latitude of the day/night line at a given longitude (for map drawing)."""
    dec, _ = sun_declination_ra(dt)
    slat, slon = subsolar_point(dt)
    dl = math.radians(lon - slon)
    if abs(math.tan(dec)) < 1e-9:
        return 0.0
    return math.degrees(math.atan(-math.cos(dl) / math.tan(dec)))


def utcnow():
    return datetime.now(timezone.utc)
