# HF Propagation

A simple HF / ionospheric propagation tool for ham radio operators and shortwave listeners.
Tell it where you are (zip code, grid square, or latitude/longitude) and it shows live space
weather, which bands are open from your location right now and over the next 24 hours, a world
map, and who has really been heard on the air.

## Pages

| Page | What it covers |
|---|---|
| [Install on Android](Install-on-Android.md) | Download the app and install it on a phone or tablet, step by step |
| [Getting Started](Getting-Started.md) | Install on Linux (or Android) and set your location |
| [Using the App](Using-the-App.md) | A tour of every screen: Home, Bands, Map, Stations, Space Wx, Settings |
| [How the Predictions Work](How-the-Predictions-Work.md) | The model in plain language, and what it can and cannot tell you |
| [Data Sources and Privacy](Data-Sources-and-Privacy.md) | Where the data comes from and what leaves your device |
| [Troubleshooting](Troubleshooting.md) | Common problems and fixes |
| [Developer Guide](Developer-Guide.md) | Code layout, running, testing, building for Linux and Android |
| [Selling It](Selling-It.md) | On hold. Licensing, data terms, store requirements and a launch checklist, kept for reference |

## Download

* **Android:** https://github.com/N0NJY/solar-propagation/releases/latest (guide: [Install on Android](Install-on-Android.md))
* **Linux and Raspberry Pi:** see [Getting Started](Getting-Started.md)
* **Windows:** [Install on Windows](Install-on-Windows.md) (tested on one laptop)
* **macOS:** untested, see [Getting Started](Getting-Started.md)

## At a glance

* **Minimal input.** Enter a location once. Everything else has a sensible default.
* **GO / MARGINAL / NO-GO** for each band from 160 m to 6 m, to each region of the world.
* **Live space weather** from NOAA: solar flux, Kp, X-ray flares, solar wind, alerts.
* **Real reports** from PSK Reporter: who heard you and whom you heard, compared with the prediction.
* **Runs on** Android and Linux (including a 64-bit Raspberry Pi). Windows works (lightly tested). A macOS build exists but is untested.
* **Python** throughout, with the [Flet](https://flet.dev) toolkit for the screens.

> Predictions are an empirical estimate for planning. They are not a guarantee and not a
> substitute for tools such as VOACAP.

## Contact and news

* Email: [n0njy.software@gmail.com](mailto:n0njy.software@gmail.com)
* Write-up: [Propagation program for your tablet](https://preppercomm.substack.com/p/propagation-program-for-your-tablet)
* More from the author: [PrepperComm on Substack](https://preppercomm.substack.com)
* Bugs and ideas: [GitHub issues](https://github.com/N0NJY/solar-propagation/issues)

## Licence

MIT. See the `LICENSE` file. Free to use, change and share.
