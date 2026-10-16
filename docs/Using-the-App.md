# Using the App

The bar at the bottom switches between five pages.

## Home

* **Location box and Go.** Enter a zip, grid square, or lat,lon. **Find me** uses your internet address.
* **Alert banner.** Green means quiet. Amber or red means a flare, radio blackout, or geomagnetic
  storm is under way. Tap it to open **Space Wx**.
* **Bands open right now.** Green chips list the bands that are GO to at least one region, with how
  many regions. **Marginal** bands and **Next openings** (when a closed band is expected to open)
  appear underneath.
* **Solar tiles.** Solar flux (SFI), sunspot number estimate, Kp and A index, and X-ray class.

## Bands

* **Time selector.** *Now*, *+3h*, *+6h*, *+12h*, *+24h*. The page shows predictions for that time.
* **Best times: next 24 hours.** One row per band, one column per hour. Green is good, amber is
  marginal, dark is closed. The outlined first column is the current hour. The blue "local" row is
  approximate local solar time worked out from your longitude, not your time zone.
* **Band cards.** One per band (160 m to 6 m) with an overall GO / MARGINAL / NO-GO. Open a card
  for every region it covers, with distance, bearing and the quality of the path.

## Map

A world map with day and night shading, the sun's position, and your location.

* **Band chips** across the top choose the band shown.
* **Layers:** *Places* (coloured dots for regions: green good, amber marginal, grey not reachable),
  *Heat map* (where your signal is expected to be heard, deeper green is stronger, amber marginal),
  and *Heard* (real stations from PSK Reporter).
* **Map detail:** *Countries*, *States / provinces*, *Cities*, and *Grid squares* (Maidenhead).
* **Zoom and move.** Mouse wheel, drag, or two-finger pinch. The buttons at the right zoom in and
  out, jump to your location, or show the whole world. The scale bar follows your unit setting.
  While you zoom, the picture is briefly soft and then sharpens.
* **Tap a place** to see every band to that region. Tap a heard station to highlight it.
* **Dots are regions, not stations.** The coloured dots are representative points for 37 regions of
  the world. Real stations appear only as squares in the *Heard* layer.
* **Stations heard** button opens the Stations page.

### Stations

A list of real PSK Reporter reports for your callsign (set it in Settings).

* **Heard within** a time window, and an **Only <band>** switch.
* **They heard me / I heard them** choose the direction.
* **Mode chips** (FT8, FT4, JS8, WSPR, CW, RTTY, PSK31, plus any others heard) with counts. None
  selected means all modes.
* **Prediction check** shows how many real reports the model agrees with, and lists the ones it
  called closed. This is how you can judge the model against reality.

PSK Reporter is asked for new data at most every five minutes.

## Space Wx

NOAA space-weather scales (R radio blackouts, S radiation storms, G geomagnetic storms), solar wind
speed, density and magnetic field with a Bz chart, X-ray flare chart and flare odds, Kp bars with
the forecast, a note on CMEs with live coronagraph and WSA-Enlil imagery, active alerts, and the
full forecast discussion. A plain-language **What this means for HF** box sits at the top.

## Settings

Defaults work. Change them only if you want to.

| Setting | Effect |
|---|---|
| Units | Metric (km) or Imperial (miles) for distances, scale bar and solar wind speed |
| Mode | SSB, CW or Digital. Sets how strong a signal must be to count as workable |
| Transmit power | Watts. Your station, so a QRP station gets honest answers |
| Antenna | A rough gain figure from compromise (-6 dBi) to large beam (+11 dBi) |
| Noise level | Quiet / rural, Residential, City / noisy. Sets the receive noise floor |
| Callsign | Starts as `NOCALL`, which means none. Enter yours to show real PSK Reporter stations on the Map and Stations pages. Clear it to go back to `NOCALL` |

All of it is stored on your device.
