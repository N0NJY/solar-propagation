"""Metric / imperial display helpers. Internals are always km and km/s."""

KM_PER_MI = 1.609344
UNITS = ("metric", "imperial")


def imperial(units):
    return units == "imperial"


def dist(km, units="metric", decimals=0):
    if imperial(units):
        return f"{km / KM_PER_MI:,.{decimals}f} mi"
    return f"{km:,.{decimals}f} km"


def speed(kms, units="metric"):
    """Solar-wind style speed given in km/s."""
    return f"{kms / KM_PER_MI:.0f} mi/s" if imperial(units) else f"{kms:.0f} km/s"


def dist_unit(units):
    return "mi" if imperial(units) else "km"


def km_to_unit(km, units):
    return km / KM_PER_MI if imperial(units) else km


def unit_to_km(v, units):
    return v * KM_PER_MI if imperial(units) else v
