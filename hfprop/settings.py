"""User settings and last location, persisted as JSON in the cache dir."""
import json
from dataclasses import dataclass, asdict, field, fields

from .storage import cache_path

NO_CALL = "NOCALL"             # placeholder callsign: nothing is looked up until the user enters their own


@dataclass
class Settings:
    where: str = ""              # what the user typed last
    lat: float = 0.0
    lon: float = 0.0
    label: str = ""
    mode: str = "ssb"            # ssb | cw | digital
    power_w: float = 100.0
    noise: str = "residential"   # quiet | residential | city
    gain_dbi: float = 0.0
    callsign: str = NO_CALL      # optional; a real callsign enables PSK Reporter 'heard recently'
    units: str = "metric"        # metric | imperial
    map_detail: list = field(default_factory=lambda: ["borders", "states", "cities"])

    @property
    def has_callsign(self):
        return self.callsign.strip().upper() not in ("", NO_CALL)

    @property
    def has_location(self):
        return bool(self.label)

    def station(self):
        from .predict import Station
        need = {"ssb": 6.0, "cw": -3.0, "digital": -18.0}[self.mode]
        return Station(power_w=self.power_w, gain_dbi=self.gain_dbi,
                       snr_needed=need, noise=self.noise)


def load():
    try:
        raw = json.loads(cache_path("settings.json").read_text())
        names = {f.name for f in fields(Settings)}
        s = Settings(**{k: v for k, v in raw.items() if k in names})
        s.callsign = s.callsign.strip().upper() or NO_CALL
        return s
    except Exception:
        return Settings()


def save(s):
    try:
        cache_path("settings.json").write_text(json.dumps(asdict(s)))
    except Exception:
        pass
