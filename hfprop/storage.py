"""Where cached files live (desktop cache dir; HFPROP_DATA overrides; Flet sets FLET_APP_STORAGE_DATA on Android)."""
import os
from pathlib import Path


def cache_dir():
    base = os.environ.get("HFPROP_DATA") or os.environ.get("FLET_APP_STORAGE_DATA") or os.path.join(
        os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"), "hfprop")
    p = Path(base)
    p.mkdir(parents=True, exist_ok=True)
    return p


def cache_path(name):
    return cache_dir() / name
