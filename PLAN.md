# HF Propagation - Plan and status

Goal: a simple HF / ionospheric propagation tool for hams and SWLs. Enter a zip code, grid square, or lat/long and see
live space weather, band-by-band GO / MARGINAL / NO-GO, what you can reach, and a world map. Python, Flet UI,
dependency-free engine (`hfprop/`) so it runs anywhere. Open source under the MIT licence.

## Status (version 1.0.0)

| Platform | Status |
|---|---|
| Android | Released (signed APKs on GitHub Releases, tested on a Samsung tablet) |
| Linux | Works (per-user installer). Tested on x86-64 |
| Raspberry Pi | Works on 64-bit Raspberry Pi OS, including Bullseye with Python 3.12 from `uv` |
| Windows | Builds on GitHub Actions. **Untested** on real hardware |
| macOS | Builds on GitHub Actions (Apple Silicon, unsigned). **Untested** on real hardware |

Features: Home (alerts, bands open now, next openings), Bands (24-hour outlook, per-band cards), Map (zoom/pan/pinch,
detail layers, heat map, Maidenhead grid, real PSK Reporter stations), Stations page, Space Wx (NOAA scales, solar wind,
flares, Kp, CMEs, alerts), Settings (units, mode, power, antenna, noise, callsign), 10-minute auto refresh, offline cache.

## Next

- [ ] Test the Windows build on a real PC, then attach it to a release with an install page
- [ ] Test the macOS build (needs a Mac user); consider an Intel build and signing
- [ ] Validate and tune the model against PSK Reporter data (see below)
- [ ] App icon and store listing if it is ever put on Google Play
- [ ] Bundle a US zip table so the first run works fully offline
- [ ] Optional: UTC / local time display setting; notifications when a band opens

## Validate and tune the model

The "prediction check" on the Stations page compares the model with real reports. Use it for a few weeks, note the mismatches,
and adjust `hfprop/iono.py` and `hfprop/predict.py`.

Known weak spots: 160 m is too optimistic, no sporadic E (summer 6 m and 10 m), high-latitude and auroral paths are crude,
the antenna is a single gain number, and each region is one representative point.

Possible upgrade: a pure-Python IRI (for example pyIRI) behind the same `fof2()` interface, or ionosonde-corrected foF2 near the user.

## Decisions made

- Python + Flet for the UI. `hfprop` stays dependency-free.
- GO / NO-GO is relative to the user's location, per band, per reachable region.
- Minimal input: location only; everything else has defaults. The callsign starts as `NOCALL` and is never looked up.
- MIT licence, open source. Selling it is on hold (see docs/Selling-It.md).
- Android releases are signed with a key kept outside the repository. The same key must be used for every update.
