# HF Propagation

HF / ionospheric propagation prediction and live space weather for ham radio operators and SWLs.
Enter a zip code, grid square, or lat/long (or press *Find me*) and see what you can reach, right now
and over the next 24 hours.

## Download

| Platform | Status | How |
|---|---|---|
| **Android** (phone or tablet) | Released | Get the file from the [latest release](https://github.com/N0NJY/solar-propagation/releases/latest) and tap it. Step by step: [Install on Android](docs/Install-on-Android.md). Most devices want the `arm64-v8a` file |
| **Linux** (also Raspberry Pi, 64-bit) | Works | [Install on Linux](#install-linux) below |
| **Windows** (64-bit) | Works on Windows 11, lightly tested | Get the zip from the [latest release](https://github.com/N0NJY/solar-propagation/releases/latest). Step by step: [Install on Windows](docs/Install-on-Windows.md) |
| **macOS** | Builds, **untested** | See [Getting Started](docs/Getting-Started.md#macos-untested) |

## What it does

* **Home** - alert banner (flares / storms), bands open right now, next openings, solar flux / Kp / X-ray.
* **Bands** - 24-hour outlook grid and a GO / MARGINAL / NO-GO card per band (160m-6m) listing reachable regions.
* **Map** - zoomable (wheel / drag / pinch / buttons) day/night world map with selectable detail
  (countries, states & provinces, cities, Maidenhead grid squares), region dots, a heat map of where you can be heard, and real
  PSK Reporter stations (who heard you, whom you heard) with mode / time / band filters and a
  "prediction check" against reality.
* **Space Wx** - NOAA R/S/G scales, solar wind and Bz, X-ray flares, Kp, CMEs (NOAA discussion + live
  coronagraph), alerts.
* **Settings** - metric / imperial units, mode, power, antenna, noise level, callsign (starts as `NOCALL`).
  Defaults work; nothing is required.

Space weather comes from NOAA SWPC; real reports from PSK Reporter. The prediction model is an empirical
estimate meant for planning, not a substitute for VOACAP.

## Install (Linux)

    git clone https://github.com/N0NJY/solar-propagation.git
    cd solar-propagation
    packaging/install.sh          # per-user install into ~/.local, adds an app-menu entry
    hfprop-app                    # or launch "HF Propagation" from the menu
    hfprop FN31                   # command-line version
    packaging/uninstall.sh        # remove (settings in ~/.cache/hfprop are kept)

Needs Python 3.10 or newer and, on ARM, a 64-bit system. The first launch downloads the Flet window runtime, so it
needs internet once. Raspberry Pi and older-Python notes are in [Getting Started](docs/Getting-Started.md).

## Documentation

Guides are in [docs/](docs/Home.md) and on the [wiki](https://github.com/N0NJY/solar-propagation/wiki): installing,
a tour of every screen, how the predictions work and their limits, data sources and privacy, troubleshooting, and a developer guide.
Problems and questions: [issues](https://github.com/N0NJY/solar-propagation/issues).

## Develop

    python3 -m venv .venv && .venv/bin/pip install -e ".[desktop]" pytest
    .venv/bin/python -m hfprop_app        # run the app
    .venv/bin/python -m pytest            # tests

Layout: `hfprop/` is the dependency-free engine (propagation model, NOAA/PSK data, geometry);
`hfprop_app/` is the Flet UI. Developer env vars: `HFPROP_TAB` (start tab 0-4), `HFPROP_CALL`,
`HFPROP_DATA` (cache dir). See the [Developer Guide](docs/Developer-Guide.md) and the roadmap in [PLAN.md](PLAN.md).

## Contact and news

* Email: [n0njy.software@gmail.com](mailto:n0njy.software@gmail.com)
* Write-up: [Propagation program for your tablet](https://preppercomm.substack.com/p/propagation-program-for-your-tablet)
* More from the author: [PrepperComm on Substack](https://preppercomm.substack.com)
* Bugs and ideas: [GitHub issues](https://github.com/N0NJY/solar-propagation/issues)

## License

MIT, see [LICENSE](LICENSE). Third-party licences and data credits are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
Map data: Natural Earth (public domain). Space weather data courtesy of NOAA SWPC; real reports from PSK Reporter.
Not affiliated with or endorsed by either.
