# HF Propagation App - Plan

Goal: a simple HF/ionospheric propagation tool for hams and SWLs. Enter a zip code,
grid square, or lat/long and see live space weather, band-by-band GO / MARGINAL / NO-GO,
what you can reach, and a world map. Python, Flet UI. Linux first, Android second.

## Status
- [x] Phase 0 - Core engine + CLI (`hfprop/`, 7 tests passing, live NOAA data)

## Phase 1 - Linux desktop app (Flet)
Install Flet in the venv, build `app/main.py` using `hfprop` unchanged.
Fetching and prediction run off the UI thread so the window never freezes.

Screens (bottom/top tabs; same layout scales to a tablet):
1. **Home**: one input box (zip / grid / lat,lon), "Use my location" and "Go" buttons.
   Remember the last location. Below it, live tiles: SFI, SSN, Kp, A, X-ray, each coloured
   and with the plain-English line from `spaceweather.summarize`. Shows data age / offline badge.
2. **Bands**: 160m-6m table, big colour chip per band (GO green / MARGINAL amber / NO-GO red),
   count of reachable places, tap a row to list them with distance, bearing, and signal quality.
   Time selector: Now / +3h / +6h / +12h / +24h, plus a 24-hour strip per band (open hours).
3. **Map**: world map with day/night shading, your marker, DX targets coloured for the
   selected band; tap a place for the band list to it. Band selector chips above the map.
4. **Settings** (kept small): power, mode (SSB/CW/Digital), noise (quiet/residential/city),
   antenna gain. Sensible defaults so no input is ever required.

Support work:
- [ ] Simplified world coastline data (Natural Earth 110m, converted to a small bundled
      JSON) - no cartopy/matplotlib so it ports to Android.
- [ ] Equirectangular map drawn on a Flet canvas; terminator from `solar.terminator_lat`.
- [ ] 24-hour band-open grid in `predict.py` (`band_day_strip`).
- [ ] Coverage grid for the map (`predict.reach_grid(band)`, ~10 degree cells, cached per minute).
- [ ] Alerts: flare / storm banners driven by X-ray class and Kp.
- [ ] Settings + last location persisted via `storage.py`.
- [ ] Linux packaging: `flet build linux` and a desktop launcher.

## Phase 2 - Validate and tune the model
- [ ] Compare predictions with real data: PSK Reporter spots near the user's grid, WSPR
      spots, and NOAA/GIRO ionosonde foF2. Log mismatches, adjust `iono.py` constants.
- [ ] Known weak spots: 160m too optimistic, no sporadic-E (6m/10m summer), simplistic
      high-latitude/auroral handling, antenna model is a flat dBi figure.
- [ ] Optional upgrade: pure-Python IRI (e.g. pyIRI) behind the same `fof2()` interface;
      ionosonde-corrected foF2 near the user's location.

## Phase 3 - Android
Tablet arrives; connect via USB and use for development.
- [ ] Prereqs on the Linux dev box: JDK 17, Android SDK/platform-tools, `adb`; enable
      developer options + USB debugging on the tablet; confirm with `adb devices`.
- [ ] Hot-reload dev loop: run the Flet app on the Linux box and view it on the tablet
      (Flet companion app), so UI iteration doesn't need a rebuild each time.
- [ ] `flet build apk`; fix anything platform-specific:
  - `HFPROP_DATA` set to the app's private storage dir (cache path).
  - "Use my location" via the device GPS (Flet geolocator).
  - Touch targets, responsive layout, portrait + landscape.
  - Network permission in the manifest; confirm the cache works when offline.
- [ ] Verify we only depend on pure-Python packages (hfprop has no third-party deps).
- [ ] App icon, name, version; signed release build.

## Phase 4 - Later / nice to have
Windows and macOS builds (Flet supports both), PSK Reporter live overlay, notifications when
a band opens, Maidenhead grid on the map, great-circle path view, ITU-R P.533-style upgrade.

## Decisions made
- Python + Flet for UI, `hfprop` stays dependency-free.
- GO/NO-GO is relative to the user's location, per band, per reachable place.
- Minimal input: location only; everything else defaults.
- Linux first, Android second (tablet as the dev/test device).

## Open items
- Confirm Flet version and Android build requirements against current Flet docs at the
  start of Phase 3 (the tooling changes quickly).
- Decide whether non-US zip codes matter (currently US zip only; grid and lat/long work anywhere).
