# Developer Guide

## Layout

    hfprop/          the engine: no third-party dependencies, so it runs anywhere (including Android)
      geo.py           distance, bearing, Maidenhead grids (4 to 10 characters), zip and IP lookup
      solar.py         sun position, zenith angle, day/night terminator
      iono.py          foF2, hop geometry, MUF, D-layer absorption
      predict.py       link budget, GO / MARGINAL / NO-GO, band tables, reach grid, 24-hour strip
      targets.py       the 37 regional reference points
      spaceweather.py  solar flux, Kp, X-ray (headline numbers)
      swx.py           NOAA scales, solar wind, flares, Kp forecast, alerts, discussion
      psk.py           PSK Reporter reports, filtering, prediction check
      summary.py       alert level, bands open now, next openings
      units.py         metric / imperial
      mapdata.py       map geometry, view maths, bundled Natural Earth data (data/*.json)
      settings.py      the saved settings
      storage.py       cache folder (HFPROP_DATA, or Flet app storage on Android)
    hfprop_app/      the screens (Flet)
      main.py          Home, Bands, Map, Stations, Space Wx, Settings and the refresh loop
      mapview.py       the zoomable map drawn on a canvas
      heard.py         the Stations panel      spacewx.py   Space Wx page      strip.py   24-hour grid
    main.py          entry point used by `flet build`
    tools/           scripts that regenerate the bundled map data
    packaging/       Linux installer, uninstaller, icon, desktop entry
    tests/           pytest suite

Rule of thumb: anything that is maths or data goes in `hfprop`; anything that draws goes in `hfprop_app`.

## Run from source

    python3 -m venv .venv
    .venv/bin/pip install -e ".[desktop]" pytest
    .venv/bin/python -m hfprop_app       # the app
    .venv/bin/python -m hfprop FN31      # the command-line version
    .venv/bin/python -m pytest           # tests

Developer environment variables:

| Variable | Effect |
|---|---|
| `HFPROP_DATA` | Cache and settings folder |
| `HFPROP_TAB` | Start on a tab (0 Home, 1 Bands, 2 Map, 3 Space Wx, 4 Settings) |
| `HFPROP_ZOOM` | Start the map zoomed in on your location |
| `HFPROP_CALL` | Callsign for testing |
| `HFPROP_STATIONS` | Open the Stations page at start |
| `HFPROP_PROFILE` | Print how long each map redraw takes |
| `HFPROP_BENCH` | Run a zoom benchmark (`1`, `once`, or `stress`) |

## Build for Android

Needs the Android SDK (`ANDROID_HOME`), and the first build downloads Flutter, a JDK and the NDK.

    export ANDROID_HOME=$HOME/Android/Sdk
    flet build apk                          # about 15 minutes the first time, seconds after
    adb install -r build/apk/hfprop.apk

Build settings live in `pyproject.toml` under `[tool.flet]`. The app id is `com.n0njy.hfprop`.
`flet-desktop` is an optional extra (`.[desktop]`) and must not be bundled into the phone build.
For a smaller file, add `--split-per-abi`.

## Design notes worth knowing

* **Display cost is per shape, not per point.** The map merges every layer into a single path (and dots into one
  points shape). Hundreds of small shapes made redraws take over half a second.
* **Zoom feels instant** because the finished map image is moved and scaled by the display while you gesture,
  then redrawn sharply about a quarter second after you stop.
* **Expensive results are cached:** the heat-map grid is computed for a region larger than the view and reused
  while you pan; NOAA data is cached for five minutes; PSK Reporter is queried at most once per five minutes.
* **Off-screen geometry is dropped** before it is sent, so deep zooms are cheap.
* **Network failures never crash the app.** Each fetch falls back to its last cached copy.
* After UI edits, check that every `ft.Colors.*` and `ft.Icons.*` name exists and think through empty and
  zero-size states. Most past crashes were in paths that screenshots do not reach.

## Publishing the docs as a wiki

The pages in `docs/` are ready for a GitHub wiki. GitHub offers wikis on public repositories, and on private ones only with a paid plan. Once it is enabled and one page has been created in the web interface, run `tools/publish_wiki.sh https://github.com/OWNER/REPO.wiki.git`. It copies the pages and removes the `.md` from links. Until then the pages read fine in the repository.

## Testing on a device

`adb` can tap and screenshot a connected Android device, which the desktop window cannot do:

    adb shell input tap X Y
    adb exec-out screencap -p > shot.png
