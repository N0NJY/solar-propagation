# Install on Windows

You do not need an installer, an account, or administrator rights. You download one zip file, unzip it, and run the program.

**Needs:** a 64-bit Windows PC and an internet connection (it fetches live space weather).

**Status:** tested on one Windows 11 laptop. The app, map, Space Wx, location entry and settings all worked. Station reports
(PSK Reporter) have not been checked on Windows yet. Please report what you find at https://github.com/N0NJY/solar-propagation/issues.

## Step 1: Download

**https://github.com/N0NJY/solar-propagation/releases/latest**

Under **Assets**, download **`hfprop-1.0.0-windows-x64.zip`** (about 39 MB).

Direct link: **https://github.com/N0NJY/solar-propagation/releases/download/v1.0.0/hfprop-1.0.0-windows-x64.zip**

## Step 2: Unzip it

Right-click the zip file and choose **Extract All**, then **Extract**. Do not run the program from inside the zip: it needs the
other files beside it. Put the folder somewhere permanent, such as `Documents`.

## Step 3: Run it

Open the folder and double-click **`hfprop.exe`**.

Windows SmartScreen will probably say **"Windows protected your PC"**. This happens for every program that is not
code-signed, and this one is not. Click **More info**, then **Run anyway**. The program is open source and all of its code is
on this page: https://github.com/N0NJY/solar-propagation

The first start may take a few seconds longer than later ones.

## Step 4: First run

Type your location in the box on the **Home** page and press **Go**. A US zip code (`06111`), a grid square (`FN31pr`, more
characters is more exact) or `latitude,longitude` (`41.71,-72.73`) all work. Your location is remembered.
See [Using the App](Using-the-App.md) for a tour of every page.

## Updating and removing

* **Update:** download the new zip, extract it to a new folder, and run it from there. Settings are kept separately, so they carry over.
* **Remove:** delete the folder. Settings and cached data are in a separate folder under your user profile and can be deleted too.

## Checking the download (optional)

Each release lists SHA-256 checksums in the `SHA256SUMS` file. In PowerShell:

    Get-FileHash .\hfprop-1.0.0-windows-x64.zip -Algorithm SHA256

The result should match the line for that file in `SHA256SUMS`.

## If it does not work

See [Troubleshooting](Troubleshooting.md). If the window does not open, or closes at once, please open an issue and say which version of Windows you have.
