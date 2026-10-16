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

### Raspberry Pi (64-bit OS only)

It works on a Raspberry Pi 3, 4 or 5 only if the operating system is **64-bit** and recent. Two checks first, because
`uname -m` alone is not enough (a 32-bit Pi OS on a 64-bit kernel also says `aarch64`):

    dpkg --print-architecture      # must say arm64   (armhf means 32-bit: not supported)
    python3 --version              # must be 3.10 or newer (Debian 12 "Bookworm" has 3.11)
    cat /etc/os-release | head -2  # Debian 12 or newer

If either check fails, install the current **64-bit Raspberry Pi OS** (Raspberry Pi Imager, choose "Raspberry Pi OS (64-bit)").
The installer also stops with a clear message if it finds an old Python or a 32-bit system. When the checks pass:

    sudo apt update
    sudo apt install git python3-venv libgtk-3-0
    git clone https://github.com/N0NJY/solar-propagation.git
    cd solar-propagation
    packaging/install.sh

If it complains about a missing library when it starts, install the package it names. Only the Pi's browser-free
command-line version (`hfprop FN31`) works on older systems, because that part needs nothing but Python 3.10.
This route has not been tested on a Pi yet, so please report what happens at https://github.com/N0NJY/solar-propagation/issues.

## Android

Download the app file from the releases page and tap it. No computer is needed. Follow the step-by-step guide:
**[Install on Android](Install-on-Android.md)**, or go straight to
https://github.com/N0NJY/solar-propagation/releases/latest

Developers who want to build it from the source can use `flet build apk`; see the [Developer Guide](Developer-Guide.md).

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
