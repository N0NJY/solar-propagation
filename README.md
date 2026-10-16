# HF Propagation

HF / ionospheric propagation prediction and live space weather for ham radio operators and SWLs.
Enter a zip code, grid square, or lat/long (or press *Find me*) and see what you can reach, right now
and over the next 24 hours.

* **Home** - alert banner (flares / storms), bands open right now, next openings, solar flux / Kp / X-ray.
* **Bands** - 24-hour outlook grid and a GO / MARGINAL / NO-GO card per band (160m-6m) listing reachable regions.
* **Map** - zoomable (wheel / drag / pinch / buttons) day/night world map with selectable detail
  (countries, states & provinces, cities, Maidenhead grid squares), region dots, a heat map of where you can be heard, and real
  PSK Reporter stations (who heard you, whom you heard) with mode / time / band filters and a
  "prediction check" against reality.
* **Space Wx** - NOAA R/S/G scales, solar wind and Bz, X-ray flares, Kp, CMEs (NOAA discussion + live
  coronagraph), alerts.
* **Settings** - metric / imperial units, mode, power, antenna, noise level, callsign. Defaults work; nothing is required.

Space weather comes from NOAA SWPC; real reports from PSK Reporter. The prediction model is an empirical
estimate meant for planning, not a substitute for VOACAP.

## Install (Linux)

    packaging/install.sh          # per-user install into ~/.local, adds an app-menu entry
    hfprop-app                    # or launch "HF Propagation" from the menu
    hfprop FN31                   # command-line version
    packaging/uninstall.sh        # remove (settings in ~/.cache/hfprop are kept)

The first launch downloads the Flet window runtime, so it needs internet once.

## Develop

    python3 -m venv .venv && .venv/bin/pip install -e . pytest
    .venv/bin/python -m hfprop_app        # run the app
    .venv/bin/python -m pytest            # tests

Layout: `hfprop/` is the dependency-free engine (propagation model, NOAA/PSK data, geometry);
`hfprop_app/` is the Flet UI. Developer env vars: `HFPROP_TAB` (start tab 0-4), `HFPROP_CALL`,
`HFPROP_DATA` (cache dir). See [PLAN.md](PLAN.md) for the roadmap (Android build works; see the Developer Guide).

## License

MIT, see [LICENSE](LICENSE). Third-party licences and data credits are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
Space weather data courtesy of NOAA SWPC; real reports from PSK Reporter. Not affiliated with or endorsed by either.

Documentation (wiki-ready pages) is in [docs/](docs/Home.md). Third-party licences: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Map data: Natural Earth (public domain).
