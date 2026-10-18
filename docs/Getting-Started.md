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

It works on a Raspberry Pi 3, 4 or 5 only if the operating system is **64-bit**. The window toolkit also needs
**Python 3.10 or newer**. Check both:

    dpkg --print-architecture      # must say arm64   (armhf means 32-bit: not supported)
    python3 --version              # 3.10 or newer (Debian 12 "Bookworm" has 3.11)

(`uname -m` alone is not enough: a 32-bit Pi OS on a 64-bit kernel also says `aarch64`.)

**If Python is 3.10 or newer** (Raspberry Pi OS Bookworm or later):

    sudo apt update
    sudo apt install git python3-venv libgtk-3-0
    git clone https://github.com/N0NJY/solar-propagation.git
    cd solar-propagation
    packaging/install.sh

**If Python is older** (Raspberry Pi OS Bullseye has 3.9), keep your system and add a newer Python next to it with the
`uv` tool, without touching the system Python. This is the route that was tested, on 64-bit Raspberry Pi OS Bullseye.
(Installing the current 64-bit Raspberry Pi OS with Raspberry Pi Imager is the other option if you can reflash the card.)

    sudo apt install git python3-venv libgtk-3-0 curl
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ~/.local/bin/uv python install 3.12
    git clone https://github.com/N0NJY/solar-propagation.git
    cd solar-propagation
    PYTHON=$(~/.local/bin/uv python find 3.12) packaging/install.sh

Then start it from the menu ("HF Propagation") or run `~/.local/bin/hfprop-app`. The first start downloads the window
runtime, so the Pi needs internet. If it complains about a missing library, install the package it names. The installer
stops with a clear message if it finds an old Python or a 32-bit system. It has been confirmed working on a 64-bit Raspberry Pi running Debian 11 "Bullseye" with Python 3.12 from `uv`. If you hit a problem on yours, please report it at
https://github.com/N0NJY/solar-propagation/issues.

## Windows

Download the zip from the latest release and run `hfprop.exe`. Full steps, including the SmartScreen "Run anyway" screen:
[Install on Windows](Install-on-Windows.md).

## macOS (untested)

A macOS version can be built, but **it has not been run on a real Mac yet**, so there is no release download for it and nothing
here is guaranteed. If you want to try:

1. Open https://github.com/N0NJY/solar-propagation/actions and click the newest successful run of
   **Build Windows and macOS apps**. (You need to be logged in to GitHub to download from it.)
2. Under **Artifacts**, download `hfprop-macos`.
3. Unzip it. It is built for Apple Silicon Macs (M1 and newer) and is not signed, so macOS will refuse to
   open it normally. Right-click the app, choose **Open**, then **Open** again. It is unlikely to run on older Intel Macs.

Please report what happens, good or bad, at https://github.com/N0NJY/solar-propagation/issues, and which macOS
version you used. Until a few people confirm it works, treat this build as experimental.

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
