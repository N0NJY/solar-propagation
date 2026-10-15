"""Command-line front end:  python -m hfprop FN31   |   python -m hfprop 90210"""
import argparse
import sys
from datetime import datetime, timezone, timedelta

from . import spaceweather, geo, predict, solar

COL = {"GO": "\033[92m", "MARGINAL": "\033[93m", "NO-GO": "\033[91m"}
OFF = "\033[0m"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="hfprop")
    ap.add_argument("where", help="zip code, grid square (FN31), or 'lat,lon'")
    ap.add_argument("--hours", type=int, default=0, help="hours from now (UTC)")
    ap.add_argument("--power", type=float, default=100.0, help="tx power in watts")
    ap.add_argument("--mode", choices=["ssb", "cw", "digital"], default="ssb")
    ap.add_argument("--noise", choices=["quiet", "residential", "city"], default="residential")
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--details", action="store_true", help="list reachable places per band")
    a = ap.parse_args(argv)
    try:
        lat, lon, label = geo.parse_location(a.where)
    except Exception as e:
        sys.exit(f"error: {e}")
    sw = spaceweather.get_space_weather(offline=a.offline)
    dt = datetime.now(timezone.utc) + timedelta(hours=a.hours)
    need = {"ssb": 6.0, "cw": -3.0, "digital": -18.0}[a.mode]
    st = predict.Station(power_w=a.power, snr_needed=need, noise=a.noise)
    print(f"\n{label}  ({lat:.2f}, {lon:.2f})  grid {geo.latlon_to_grid(lat, lon)}"
          f"   {dt:%Y-%m-%d %H:%M} UTC")
    tag = "live" if sw.live else f"CACHED/DEFAULT ({sw.age_hours:.0f} h old)"
    print(f"SFI {sw.sfi:.0f}  SSN~{sw.ssn:.0f}  Kp {sw.kp:.1f}  A {sw.a_index:.0f}  "
          f"X-ray {sw.xray_class}   [{tag}]")
    for k, v in spaceweather.summarize(sw).items():
        print(f"  {k}: {v}")
    print(f"\n{'BAND':<6}{'STATUS':<10}REACHABLE (go / marginal)")
    for r in predict.band_table(lat, lon, dt, sw, st):
        c = COL[r["overall"]]
        go = ", ".join(e["target"] for e in r["go"][:6]) or "-"
        more = f" +{len(r['go']) - 6}" if len(r["go"]) > 6 else ""
        print(f"{r['band']:<6}{c}{r['overall']:<10}{OFF}{len(r['go']):>2} go / {len(r['marginal']):>2} marg  {go}{more}")
        if a.details and r["marginal"]:
            print(f"{'':16}marginal: {', '.join(e['target'] for e in r['marginal'])}")


if __name__ == "__main__":
    main()
