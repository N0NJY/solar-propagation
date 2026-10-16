# Data Sources and Privacy

## Where the data comes from

| Data | Source | When it is used |
|---|---|---|
| Solar flux, Kp, X-ray flux, NOAA scales, alerts, forecast discussion, solar wind, flare odds, coronagraph and WSA-Enlil images | NOAA Space Weather Prediction Center (SWPC), `services.swpc.noaa.gov` | Whenever space weather is shown or refreshed |
| Real contact reports | PSK Reporter, `retrieve.pskreporter.info` | Only if you enter a callsign |
| US zip code to latitude and longitude | zippopotam.us (data from GeoNames) | Only when you type a zip code. Results are cached on the device |
| Approximate location from internet address | ipwho.is | Only when you press **Find me** |
| Coastlines, lakes, countries, states, cities | Natural Earth (public domain), bundled with the app | Offline, nothing is sent |

NOAA data refreshes every few minutes, so the app caches it for five minutes. PSK Reporter is
asked at most once every five minutes. If the network is down the app shows the last cached data
and says it is offline.

## What leaves your device

* **Nothing about you goes to NOAA.** The requests are the same for every user.
* **Your callsign** goes to PSK Reporter, which is how it finds your reports. Your callsign is already public there.
* **A zip code** goes to zippopotam.us when you type one.
* **Your internet address** is seen by ipwho.is when you press **Find me**, which is the point of that button.
* Every request also reveals your internet address to the server that answers it, as with any web request.
* Your **latitude and longitude are never sent anywhere.** The prediction runs entirely on your device.

## What is stored on your device

A small settings file (location, units, mode, power, antenna, noise, callsign, map options) and cached
copies of the data above, in `~/.cache/hfprop` on Linux or the app's private storage on Android.
There are no accounts, no analytics, no advertising and no tracking.
