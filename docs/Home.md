# HF Propagation

A simple HF / ionospheric propagation tool for ham radio operators and shortwave listeners.
Tell it where you are (zip code, grid square, or latitude/longitude) and it shows live space
weather, which bands are open from your location right now and over the next 24 hours, a world
map, and who has really been heard on the air.

## Pages

| Page | What it covers |
|---|---|
| [Getting Started](Getting-Started.md) | Install on Linux or Android and set your location |
| [Using the App](Using-the-App.md) | A tour of every screen: Home, Bands, Map, Stations, Space Wx, Settings |
| [How the Predictions Work](How-the-Predictions-Work.md) | The model in plain language, and what it can and cannot tell you |
| [Data Sources and Privacy](Data-Sources-and-Privacy.md) | Where the data comes from and what leaves your device |
| [Troubleshooting](Troubleshooting.md) | Common problems and fixes |
| [Developer Guide](Developer-Guide.md) | Code layout, running, testing, building for Linux and Android |
| [Selling It](Selling-It.md) | Licensing, data terms, store requirements and a launch checklist |

## At a glance

* **Minimal input.** Enter a location once. Everything else has a sensible default.
* **GO / MARGINAL / NO-GO** for each band from 160 m to 6 m, to each region of the world.
* **Live space weather** from NOAA: solar flux, Kp, X-ray flares, solar wind, alerts.
* **Real reports** from PSK Reporter: who heard you and whom you heard, compared with the prediction.
* **Runs on** Linux and Android today. Windows and macOS builds share the same code.
* **Python** throughout, with the [Flet](https://flet.dev) toolkit for the screens.

> Predictions are an empirical estimate for planning. They are not a guarantee and not a
> substitute for tools such as VOACAP.
