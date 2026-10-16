# Troubleshooting

## The app says it is offline, or numbers look old
It could not reach NOAA, so it is showing the last cached values. Check the connection, then press
the refresh button on the Space Wx page. The app also refreshes by itself every 10 minutes.

## Find me puts me in the wrong city
It uses your internet address, which can point at your provider's hub. Enter a grid square or
latitude,longitude instead.

## My location is in the ocean, or far from home
A 4-character grid such as `FN31` is plotted at the centre of a 2 by 1 degree box. Use a 6, 8 or
10-character grid (`FN31pr47ab`) or coordinates.

## The Stations page is empty
Stations needs your callsign (Settings). If you have one and still see nothing, PSK Reporter has no
reports for it in that window. Try a longer *Heard within* window. If you expect reports, check that
your decoding software is uploading spots (in WSJT-X: Settings, Reporting, *Upload spots*).
The mode chips show a count of 0 for modes with no reports. That is normal.

## The map is slow
Turn off layers you are not using: the *Heat map*, *Grid squares* and *Cities* are the heaviest.
Zooming shows a soft picture first and sharpens a moment later.

## The zoom or the recentre buttons do nothing (desktop)
Make sure you are running a current build. Start from a terminal with `hfprop-app` and send any
message printed there.

## WSJT-X or JS8Call shows no signals even though the radio has audio
Not an app issue, but a common one. Check the sound input in the decoder is the radio's USB audio
device, the dial frequency is right (FT8 20 m is 14.074 MHz USB, WSPR 20 m is 14.0956 MHz USB), and the
computer clock is within about a second (`timedatectl`).

## Android: the app does not install
Turn on USB debugging, accept the prompt on the device, and check `adb devices` shows `device`.
Reinstall with `adb install -r build/apk/hfprop.apk`.

## An error box appears
Copy its text and report it with what you tapped. On Linux, run `hfprop-app` from a terminal to
see the full message.
