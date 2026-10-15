# solar-propagation

Simple HF / ionospheric propagation prediction for ham radio operators and SWLs.

Enter a zip code, grid square, or lat/long and get live space weather plus a band-by-band
GO / MARGINAL / NO-GO table showing what you can reach from your location.

Python. Linux first, Android to follow. See [PLAN.md](PLAN.md) for the roadmap.

## Try it (command line)

    python3 -m venv .venv && .venv/bin/pip install pytest
    .venv/bin/python -m hfprop FN31
    .venv/bin/python -m hfprop 90210 --hours 6 --mode cw --details
    .venv/bin/python -m pytest

Space weather comes from NOAA SWPC. The prediction model is empirical and meant for
go/no-go planning, not a substitute for VOACAP.
