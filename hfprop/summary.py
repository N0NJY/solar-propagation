"""Home-screen summaries: alert banner and 'bands open now' / 'next opening'."""
from . import predict, swx


def alerts(sw, scales):
    """-> (level 0..3, [messages]). 0 quiet, 1 watch, 2 disturbed, 3 severe."""
    msgs, level = [], 0

    def add(lv, text):
        nonlocal level
        level = max(level, lv)
        msgs.append(text)

    if scales:
        now = scales["now"]
        if now["R"] >= 1:
            add(2 if now["R"] < 3 else 3, f"R{now['R']} radio blackout in progress: HF fading on the sunlit side.")
        if now["G"] >= 1:
            add(2 if now["G"] < 3 else 3, f"G{now['G']} geomagnetic storm: disturbed paths, worst toward the poles.")
        if now["S"] >= 1:
            add(2, f"S{now['S']} radiation storm: polar HF paths degraded.")
        for i in (1, 2, 3):
            g = scales[f"day{i}"]["G"]
            if g >= 1 and now["G"] == 0:
                add(1, f"NOAA forecasts a G{g} geomagnetic storm in {i} day{'s' if i > 1 else ''}.")
                break
    if sw.kp >= 5 and not any("geomagnetic storm:" in m for m in msgs):
        add(2, f"Kp is {sw.kp:.1f}: geomagnetic storm level.")
    elif sw.kp >= 4 and level == 0:
        add(1, f"Kp is {sw.kp:.1f}: unsettled field, polar paths may flutter.")
    if sw.xray_flux >= 1e-5 and not any("blackout" in m for m in msgs):
        add(2, f"{sw.xray_class} flare: brief low-band absorption possible.")
    return level, msgs


def open_now(rows):
    """Bands that are GO now, best first: [(band, regions_good)]; and marginal band names."""
    go = sorted(((r["band"], len(r["go"])) for r in rows if r["overall"] == predict.GO), key=lambda x: -x[1])
    marginal = [r["band"] for r in rows if r["overall"] == predict.MARGINAL]
    return go, marginal


def next_openings(strip, limit=4):
    """For bands closed right now: [(band, hours_from_now, utc_hour)] soonest first."""
    grid, start = strip["grid"], strip["start_hour"]
    out = []
    for band, states in grid.items():
        if states[0] == predict.GO:
            continue
        for h, st in enumerate(states):
            if st == predict.GO:
                out.append((band, h, (start + h) % 24))
                break
    return sorted(out, key=lambda x: (x[1], x[0]))[:limit]
