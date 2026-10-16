# Install on Android

You do not need a computer, a Google account, or the Play Store. You download one file and tap it.

**Needs:** Android 7.0 or newer, and an internet connection when you use it (it fetches live space weather).

## Step 1: Download the app

On your phone or tablet, open this page in your browser:

**https://github.com/N0NJY/solar-propagation/releases/latest**

Scroll down to **Assets** and tap the file for your device:

| File | Use it on |
|---|---|
| **`hfprop-1.0.0-arm64-v8a.apk`** | Almost every phone and tablet made since about 2017. **Choose this one if you are unsure.** |
| `hfprop-1.0.0-armeabi-v7a.apk` | Older 32-bit devices. Use it only if the first one says it is not compatible |
| `hfprop-1.0.0-x86_64.apk` | Chromebooks and emulators. Almost nobody needs this |

Direct link for most devices:
**https://github.com/N0NJY/solar-propagation/releases/download/v1.0.0/hfprop-1.0.0-arm64-v8a.apk**

The file is about 55 MB. Your browser may warn that this type of file can harm your device. That
warning appears for every app that does not come from the Play Store. Tap **Download anyway** or **OK**.

## Step 2: Allow the install

1. When the download finishes, tap **Open** (or open your **Downloads** or **Files** app and tap the file).
2. Android will say it cannot install apps from this source. Tap **Settings**, switch on **Allow from this source**,
   then press the back button.
   * You are only allowing your browser (or Files app) to install, and you can switch it off again afterwards.
3. Tap **Install**.
4. If **Play Protect** shows a message such as "App scan recommended" or "Unsafe app blocked", tap **More details**,
   then **Install anyway** (or **Scan app** and then install). The app is open source, and every line of its code is on
   this page: https://github.com/N0NJY/solar-propagation
5. Tap **Open**.

## Step 3: First run

1. On the **Home** page, type your location in the box and press **Go**. Any one of these works:
   * a US zip code, for example `06111`
   * a grid square, for example `FN31pr` (more characters means more exact)
   * latitude,longitude, for example `41.71,-72.73`

   Or press **Find me (approximate)**. It guesses your city from your internet address.
2. The page fills in with live space weather and the bands open to you right now. Your location is remembered.
3. Optional: open **Settings** and enter your callsign, power, antenna and noise level. Entering your callsign
   shows real stations that heard you (from PSK Reporter) on the **Map**. It starts as `NOCALL`, which means none.

See [Using the App](Using-the-App.md) for a tour of every page.

## Updating

When a new version is released, download the new file the same way and tap it. It installs over the old one and keeps
your settings. Releases are always signed with the same key, which Android needs to allow an update.

## Checking the download (optional)

Each release lists a SHA-256 checksum for every file. On a computer, `sha256sum hfprop-1.0.0-arm64-v8a.apk` should give
the same value. The signing certificate's SHA-256 fingerprint is:

    4E:ED:24:22:09:0C:A8:E8:D2:48:0D:99:8A:69:C0:02:D7:B0:36:5D:D9:EC:0F:19:D9:17:FF:79:A9:81:E9:39

## Removing it

Press and hold the app icon, then choose **Uninstall**, or use Settings, Apps, HF Propagation, Uninstall.

## Problems

| What you see | What to do |
|---|---|
| "App not installed" or "not compatible" | Try the `armeabi-v7a` file, and check the device runs Android 7.0 or newer |
| "App not installed" on an update | You may have an older test build signed with a different key. Uninstall it first, then install the new one |
| The Install button is greyed out or the install is blocked | Switch on **Allow from this source** (Step 2). On some phones this is under Settings, Apps, Special access, Install unknown apps |
| It opens but shows no data | Check the internet connection, then open the **Space Wx** page and press the refresh button |
| Anything else | See [Troubleshooting](Troubleshooting.md), or open an issue at https://github.com/N0NJY/solar-propagation/issues |

Windows and macOS builds exist but are untested and not published as downloads. Linux and Raspberry Pi users: see [Getting Started](Getting-Started.md).
