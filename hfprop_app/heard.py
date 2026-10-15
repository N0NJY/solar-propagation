"""'Heard recently' panel: real PSK Reporter reports with window / direction / mode / band filters."""
import asyncio
import time

import flet as ft

from hfprop import psk, units

WINDOWS = [(1800, "30 min"), (3600, "1 hour"), (10800, "3 hours"), (21600, "6 hours"), (86400, "24 hours")]
C_ME, C_THEM, C_BOTH = "#1b6fd8", "#8e44c8", "#0a9e96"


def station_color(st):
    return C_BOTH if st["heard_me"] and st["i_heard"] else C_ME if st["heard_me"] else C_THEM


def ago(seconds):
    m = int(seconds // 60)
    return f"{m} min ago" if m < 90 else f"{m // 60} h ago"


COMMON_MODES = ("FT8", "FT4", "JS8", "WSPR", "CW", "RTTY", "PSK31")


def m_rank(m):
    return (COMMON_MODES.index(m) if m in COMMON_MODES else len(COMMON_MODES), m)


class Heard:
    def __init__(self, page, get_settings, get_state, save_settings, redraw):
        self.page, self.get_s, self.get_state, self.save, self.redraw = page, get_settings, get_state, save_settings, redraw
        self.rows, self.age, self.err, self.busy = [], None, None, False
        self.window, self.dirs, self.modes, self.band_only = 3600, {"heard_me", "i_heard"}, set(), False
        self.selected = None
        self.enabled = False                      # layer switched on
        self.title = ft.Text("Heard recently (PSK Reporter)", size=16, weight=ft.FontWeight.W_600)
        self.status = ft.Text(size=12, opacity=0.65)
        self.spin = ft.ProgressRing(width=16, height=16, visible=False)
        self.call_field = ft.TextField(label="Your callsign", width=200, text_size=14, dense=True,
                                       on_submit=self._save_call)
        self.call_box = ft.Row(wrap=True, spacing=8, controls=[
            self.call_field, ft.FilledButton("Show who hears me", on_click=self._save_call)])
        self.filters = ft.Column(spacing=8)
        self.summary = ft.Text(size=14)
        self.check = ft.Column(spacing=2)
        self.listing = ft.Column(spacing=0)
        self.control = ft.Card(visible=False, content=ft.Container(padding=14, content=ft.Column(spacing=10, controls=[
            ft.Row([self.title, self.spin, ft.IconButton(ft.Icons.REFRESH, tooltip="Refresh (at most every 5 min)",
                                                          on_click=self._manual_refresh)]),
            self.status, self.call_box, self.filters, self.summary, self.check, self.listing])))

    # ---- data ----
    def _now(self):
        return time.time()

    def _rows_for(self, band, ignore_modes=False):
        return psk.select(self.rows, self._now(), self.window, tuple(self.dirs),
                          () if ignore_modes else tuple(self.modes), band if self.band_only else None)

    def stations(self, band):
        s = self.get_s()
        if not self.enabled or not s.callsign:
            return []
        return psk.stations(self._rows_for(band), s.lat, s.lon)

    async def refresh(self, force=False):
        s = self.get_s()
        if not s.callsign or self.busy:
            self.render()
            return
        self.busy = True
        self.spin.visible = True
        self.page.update()
        offline = self.get_state().get("offline", False)
        self.rows, self.age, self.err = await asyncio.to_thread(psk.get_spots, s.callsign, offline, force)
        self.busy = False
        self.spin.visible = False
        self.render()
        self.redraw()

    async def maybe_refresh(self):
        if self.enabled and self.get_s().callsign and (self.age is None or self.age > psk.TTL):
            await self.refresh()

    async def _manual_refresh(self, e):
        await self.refresh(force=True)

    async def _save_call(self, e):
        s = self.get_s()
        s.callsign = self.call_field.value.strip().upper()
        self.save(s)
        self.rows, self.age = [], None
        await self.refresh()

    # ---- interaction ----
    def pick(self, call):
        self.selected = call
        self.render()
        self.redraw()

    def _set(self, attr, value):
        setattr(self, attr, value)
        self.render()
        self.redraw()

    def _toggle(self, collection, key):
        collection.symmetric_difference_update({key})
        self.render()
        self.redraw()

    # ---- rendering ----
    def render(self):
        s, st = self.get_s(), self.get_state()
        self.control.visible = self.enabled
        if not self.enabled:
            return
        band = st.get("band")
        self.call_box.visible = not s.callsign
        self.filters.visible = bool(s.callsign)
        if not s.callsign:
            self.status.value = "Enter your callsign to see real stations that heard you, and stations you heard."
            self.summary.value = ""
            self.check.controls, self.listing.controls = [], []
            return
        age = f" Updated {ago(self.age)}." if self.age is not None else ""
        self.status.value = (self.err + ". " if self.err else "") + f"{s.callsign} - real reports from PSK Reporter.{age}"
        base = self._rows_for(band, ignore_modes=True)
        counts = psk.mode_counts(base)
        for m in list(COMMON_MODES) + sorted(self.modes):
            counts.setdefault(m, 0)
        rows = self._rows_for(band)
        stations = psk.stations(rows, s.lat, s.lon)

        win = ft.Dropdown(label="Heard within", value=str(self.window), width=150, dense=True,
                          options=[ft.DropdownOption(key=str(k), text=t) for k, t in WINDOWS],
                          on_select=lambda e: self._set("window", int(e.control.value)))
        dirs = ft.Row(wrap=True, spacing=6, controls=[
            ft.Chip(label=ft.Text("They heard me"), selected="heard_me" in self.dirs, show_checkmark=False,
                    on_click=lambda e: self._toggle(self.dirs, "heard_me")),
            ft.Chip(label=ft.Text("I heard them"), selected="i_heard" in self.dirs, show_checkmark=False,
                    on_click=lambda e: self._toggle(self.dirs, "i_heard"))])
        modes = ft.Row(wrap=True, spacing=6, run_spacing=4, controls=[
            ft.Chip(label=ft.Text(f"{m} ({n})"), selected=m in self.modes, show_checkmark=False,
                    on_click=lambda e, m=m: self._toggle(self.modes, m))
            for m, n in sorted(counts.items(), key=lambda kv: (-kv[1], m_rank(kv[0])))] or
            [ft.Text("No reports in this window.", size=12, opacity=0.65)])
        only = ft.Switch(label=f"Only {band}", value=self.band_only,
                         on_change=lambda e: self._set("band_only", e.control.value))
        self.filters.controls = [ft.Row(wrap=True, spacing=12, controls=[win, only]), dirs,
                                 ft.Text("Modes (tap to filter; none selected = all):", size=12, opacity=0.65), modes]

        me = sum(1 for x in stations if x["heard_me"])
        them = sum(1 for x in stations if x["i_heard"])
        self.summary.value = (f"{me} station{'s' if me != 1 else ''} heard you, {them} you heard, "
                              f"{len(rows)} reports in the last {dict(WINDOWS)[self.window]}.") if rows else \
            "Nothing heard in this window. Try a longer window or other filters."
        self.check.controls = []
        sw = st.get("sw")
        if rows and sw:
            ag = psk.agreement(rows, s.lat, s.lon, sw, s.station())
            pct = 100 * ag["agree"] // max(1, ag["total"])
            self.check.controls.append(ft.Text(
                f"Prediction check: the model matched {ag['agree']} of {ag['total']} real reports ({pct}%).",
                size=13, weight=ft.FontWeight.W_600))
            if ag["misses"]:
                self.check.controls.append(ft.ExpansionTile(
                    title=ft.Text(f"{len(ag['misses'])} heard but predicted closed", size=12),
                    controls=[ft.Text(f"{m['call']}  {m['band']} {m['mode']}  {units.dist(m['km'], s.units)}  (model MUF {m['muf']:.1f} MHz)",
                                      size=12) for m in ag["misses"][:15]]))
        tiles = []
        for x in stations[:25]:
            sel = x["call"] == self.selected
            tiles.append(ft.ListTile(
                dense=True, selected=sel, on_click=lambda e, c=x["call"]: self.pick(c),
                leading=ft.Container(width=14, height=14, bgcolor=station_color(x), border_radius=2),
                title=ft.Text(f"{x['call']}   {x['grid']}", size=13, weight=ft.FontWeight.W_600),
                subtitle=ft.Text(f"{units.dist(x['km'], s.units)}, {x['bearing']:.0f}\N{DEGREE SIGN}  -  {', '.join(x['bands'])}  -  "
                                 f"{', '.join(x['modes'])}  -  best SNR {x['best_snr'] if x['best_snr'] is not None else '?'} dB  -  "
                                 f"{ago(self._now() - x['last'])}", size=11)))
        self.listing.controls = tiles
