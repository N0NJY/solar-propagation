# How the Predictions Work

The question the app answers for each band and each region is: **if I transmit from here, will my
signal be workable there?** It works this out from a physical model of the ionosphere, today's
space weather, and your station. It does not look anything up in a table of past results.

## The steps

1. **Where is the ionosphere dense enough?** For any point and time the model estimates **foF2**,
   the highest frequency the F2 layer can reflect straight up. It rises with solar activity
   (sunspot number), is strongest with the sun high overhead, falls at night to about 40 percent
   of its daytime value, falls toward the poles, has a bump near 15 degrees latitude, and is
   depressed by geomagnetic storms (high Kp).
2. **How does the signal travel?** The path is split into hops of at most 4,000 km. Each hop bounces
   off the layer at about 300 km height. The steeper the angle, the higher the frequency that can
   get through: this is the **MUF** (maximum usable frequency) for the path. Frequencies above about
   10 percent over the MUF are NO-GO.
3. **How much signal is lost?** Free-space loss over the slanted path, **D-layer absorption** (heavy
   by day and at low bands, worse during X-ray flares), a loss at each ground bounce, and 5 dB for
   everything else (polarisation, focusing).
4. **How loud is the noise?** The receive noise floor is the larger of man-made and atmospheric noise
   at that frequency and time of day, set by your **Noise level** setting.
5. **Your station.** Transmit power plus antenna gain (counted at both ends).
6. **Is it enough?** The resulting signal-to-noise ratio is compared with what your **Mode** needs:
   about +6 dB for SSB, -3 dB for CW and -18 dB for digital modes such as FT8.

## What the colours mean

| State | Meaning |
|---|---|
| **GO** | The predicted signal is at or above what the mode needs |
| **MARGINAL** | Within 6 dB of what is needed, or the band is right at the MUF so it is open only on some days |
| **NO-GO** | Not expected to work |

A band is GO if **any** region in the list is GO, and the Bands page counts how many regions are open.

## Where the numbers come from

* **Solar flux (SFI)** and **Kp** from NOAA are the main inputs. The sunspot number used by the
  model is estimated from the solar flux.
* **X-ray flux** from the GOES satellites adds flare absorption on the sunlit side.
* The 24-hour outlook repeats the calculation for each hour with today's space weather.

## Limits you should know about

* It is an **empirical estimate**, deliberately simple so it runs on a phone. It is not VOACAP or
  ITU-R P.533, and it does not replace them for serious circuit design.
* **No sporadic E**, so unexpected summer 6 m and 10 m openings are not predicted.
* The 160 m result is optimistic: it does not model the details of low-band noise and absorption well.
* High-latitude and auroral paths are handled crudely.
* The antenna is a single gain number, not a pattern, so it does not know your beam heading.
* The model treats each region as one representative point.

## Checking it against reality

Enter your callsign and open the **Stations** page. The **Prediction check** compares the model
with real PSK Reporter reports and shows the percentage that agree, and which real contacts the model
called closed. In early checks, short easy paths on 40 m and 20 m digital modes agreed almost
completely. That check is the best way to see how far to trust it from your own location, and the
mismatches are what guide future tuning of the model.
