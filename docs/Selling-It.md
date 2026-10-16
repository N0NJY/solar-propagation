# Selling It

> **Status: on hold.** The project is released under the **MIT licence** as open source, and selling it is not
> planned for now. This page is kept for reference if that changes. Under MIT, anyone (including you) may sell copies.

This page collects what it takes to sell HF Propagation: the licences it depends on, the terms of the data
services, what the app stores need, and a checklist. It is a practical guide and not legal advice. Before
charging money, have a lawyer or an accountant look at the licence, the privacy policy and your business setup.

## 1. Can it be sold at all?

Yes, nothing in the tools it is built on stops you.

* **Flet** (the app framework) is Apache 2.0, **Flutter** is BSD, **Python** is PSF. All allow commercial software.
  Keep the notices in `THIRD_PARTY_NOTICES.md` with the app.
* **The licence is MIT** (see `LICENSE`). Anyone may use, modify, redistribute and even sell the software, provided the
  copyright and licence notice stay with it. If you ever wanted to sell it exclusively, that would need a different licence.
* **Map data** is Natural Earth, public domain, so there is nothing to pay or credit.

## 2. The data services (the real risk)

The app does not run its own server. Every copy talks directly to free public services. That keeps your costs at
zero, but it means you depend on terms you do not control.

| Service | What it gives | Terms found | What to do |
|---|---|---|---|
| **NOAA SWPC** | All space weather | Open US Government data. NOAA asks for credit and that you do not imply endorsement | Keep the credit line. Easy |
| **PSK Reporter** | Real "who heard me" reports | Its developer page lists **no commercial terms**. It asks clients to query no more than every 5 minutes (the app does), reserves the right to block heavy users, and asks apps to send an `appcontact=<email>` parameter so the owner can reach you | **Email the owner and get written permission before selling.** Add the `appcontact` parameter. This is the one to settle first, because the Stations page and the prediction check depend on it |
| **ipwho.is** | City from internet address ("Find me") | Free plan states **commercial use allowed**, 1,000 requests per day per address, no uptime guarantee | Fine. Each user has their own address, so the limit is per user. Keep the fallback to typing a location |
| **zippopotam.us** | US zip code to coordinates | No terms page found. Data comes from GeoNames, which is Creative Commons Attribution | Confirm the terms with the maintainer, add the GeoNames credit, and consider bundling a zip table so it works offline and cannot disappear |

Two protections already exist: every fetch falls back to cached data, and the prediction engine runs entirely on the
device. If you ever have many thousands of users, the safe design is a small server of your own that fetches NOAA and PSK
Reporter once and serves everybody from its cache. That also lets you change the sources without releasing a new app.

## 3. What to say to users (and what not to)

* **Never imply endorsement** by NOAA, PSK Reporter, or any amateur radio organisation. The notices page already says so.
* **Call the predictions what they are.** Planning estimates, not guarantees, not for any safety-critical use. Put a short
  disclaimer in the app and the store listing. The Settings page already has one line.
* **Privacy policy.** Google Play and the Apple store require a public one. The facts are on
  [Data Sources and Privacy](Data-Sources-and-Privacy.md): no accounts, no analytics, location never leaves the device, and the
  callsign, zip code or internet address go to the named services only when a feature needs them. Host the policy on a web page.
* **Name.** "HF Propagation" is generic and likely taken, and it describes the product too plainly to protect. Pick a distinctive
  name and search trademarks and the app stores before printing anything.

## 4. Choices that are yours

| Decision | Options | Notes |
|---|---|---|
| **Licence** | **Decided: MIT, open source.** | Ham radio users expect free tools, and open source builds trust |
| **Price model** | One-time purchase, free with a paid unlock (maps, 24-hour outlook, Stations), tip or donation, or free base plus paid support | There are no server costs, so a subscription is hard to justify and users dislike it |
| **Where to sell** | Google Play (one-time developer fee), Amazon Appstore, direct download with a payment service for Windows, Mac and Linux, Microsoft Store (small one-time fee), Apple App Store (yearly fee) | Check current fees. Start with one channel |
| **Who sells** | You as an individual, or a business entity | Taxes and liability differ. Ask an accountant |

An honest market note: this is a niche audience and several free propagation tools exist. The app's edge is that it
is simple, works from a grid square or zip, shows a prediction **checked against real reports**, and runs on Linux and
Android. That is the story to sell, and it is why the PSK Reporter permission matters.

## 5. Technical work before a store release

* [ ] **Signed release build.** Make an upload key for Android and keep it **outside the repository** and backed up. Losing it
      means you cannot update the app. Google Play needs an app bundle (`.aab`) or signed APK.
* [ ] **Smaller download.** Build per device type (the universal APK is 141 MB). Play handles this for bundles.
* [ ] **Icon, screenshots, short and long descriptions** for the store listing. The current icon is Flet's default.
* [ ] **Version numbers.** `pyproject.toml` has `0.1.0`. Use a real version and bump it for each release.
* [ ] **Test on more devices:** a phone, portrait mode, small screens, no network, and a first run with no saved settings.
* [ ] **Windows and macOS builds.** They use the same code, but `flet build` for those must run on those systems, or in a
      build service such as GitHub Actions.
* [ ] **Zip lookup offline** (bundle a zip table) so the one remaining small dependency cannot break the first run.
* [ ] **`appcontact` parameter** and a descriptive User-Agent for PSK Reporter, with a support email address.
* [ ] **Crash reporting** only if you add it, and only as an opt-in, and update the privacy policy to say so.
* [ ] **Model tuning.** Log the "prediction check" results over a few weeks and adjust the model before asking for money.
      The agreement score is the product's credibility.
* [ ] **Support channel:** an email address, and a place for bug reports.

## 6. Suggested order

1. Email the PSK Reporter owner. Decide the licence and price model.
2. Pick a name, check it, make an icon.
3. Run a free beta on your own tablet and a few fellow hams. Collect the prediction-check numbers and bugs.
4. Write the privacy policy and a one-page end-user licence.
5. Make the signed Android release and a store listing. Add Windows and macOS later.
