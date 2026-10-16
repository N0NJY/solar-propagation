# Getting Started

## Linux

    git clone https://github.com/N0NJY/solar-propagation.git
    cd solar-propagation
    packaging/install.sh

This installs for your user only (no root) into `~/.local`, and adds **HF Propagation** to your
applications menu. You can also run `hfprop-app` in a terminal, which is handy because any error
message is printed there. The first launch downloads the Flet window runtime, so it needs
internet once.

Command-line version, no window: `hfprop FN31` (also accepts a zip code or `lat,lon`).

Remove it with `packaging/uninstall.sh`. Your settings in `~/.cache/hfprop` are kept.

## Android

The app is not in an app store yet. To put it on a tablet or phone yourself:

1. On the device, turn on **Developer options** (Settings, About, tap *Build number* 7 times),
   then turn on **USB debugging**.
2. Connect it by USB and accept the "Allow USB debugging?" prompt.
3. On the computer, build and install (see the [Developer Guide](Developer-Guide.md)):

       flet build apk
       adb install -r build/apk/hfprop.apk

Samsung tablets sometimes turn USB debugging off again after a reconnect. If `adb devices` shows
nothing, check that setting first.

## First run

1. Type your location in the box on the **Home** page and press **Go**:
   * a US **zip code**, for example `06111`
   * a **grid square**, from 4 to 10 characters, for example `FN31`, `FN31pr`, or `FN31pr47ab`
   * **latitude,longitude**, for example `41.71,-72.73`
2. Or press **Find me (approximate)**. It looks up your city from your internet address, which is
   accurate to about the city only. A grid square or coordinates are more exact.
3. The page fills in. Your location is remembered next time.

**Tip.** A 4-character grid is a 2 by 1 degree box and the app uses its centre, which can be
far from home (or over water). Use a 6-character grid or more, or coordinates, for close-in work.

Optional but useful: open **Settings** and enter your **callsign** to see real stations on the map
that heard you, plus your power and antenna so the predictions fit your station.
