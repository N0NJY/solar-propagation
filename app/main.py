"""Flet front end for hfprop.  Run:  .venv/bin/python -m app.main"""
import asyncio
import os
from datetime import datetime, timezone, timedelta

import flet as ft

from hfprop import geo, predict, settings as cfg, spaceweather

STATE_COLOR = {"GO": ft.Colors.GREEN_600, "MARGINAL": ft.Colors.AMBER_700, "NO-GO": ft.Colors.RED_600}
STATE_ICON = {"GO": ft.Icons.CHECK_CIRCLE, "MARGINAL": ft.Icons.WARNING_AMBER, "NO-GO": ft.Icons.CANCEL}
OFFSETS = [("Now", 0), ("+3h", 3), ("+6h", 6), ("+12h", 12), ("+24h", 24)]


def tile(title, value, sub="", color=None):
    return ft.Container(
        width=150, padding=12, border_radius=12,
        bgcolor=ft.Colors.with_opacity(0.10, color or ft.Colors.BLUE_GREY),
        content=ft.Column(spacing=2, controls=[
            ft.Text(title, size=12, opacity=0.7),
            ft.Text(value, size=24, weight=ft.FontWeight.BOLD, color=color),
            ft.Text(sub, size=11, opacity=0.7)]))


def sfi_color(v):
    return ft.Colors.GREEN_600 if v >= 110 else ft.Colors.AMBER_700 if v >= 85 else ft.Colors.RED_600


def kp_color(v):
    return ft.Colors.GREEN_600 if v < 4 else ft.Colors.AMBER_700 if v < 5 else ft.Colors.RED_600


def xr_color(f):
    return ft.Colors.GREEN_600 if f < 1e-5 else ft.Colors.AMBER_700 if f < 1e-4 else ft.Colors.RED_600


async def main(page: ft.Page):
    page.title = "HF Propagation"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.padding = 0
    s = cfg.load()
    app = {"sw": None, "rows": None, "offset": 0, "busy": False}

    where = ft.TextField(label="Zip code, grid square (FN31), or lat,lon", value=s.where,
                         expand=True, on_submit=lambda e: page.run_task(go))
    loc_text = ft.Text(size=16, weight=ft.FontWeight.W_600)
    err = ft.Text(color=ft.Colors.RED_400, size=13)
    spin = ft.ProgressRing(width=22, height=22, visible=False)
    tiles = ft.Row(wrap=True, spacing=10, run_spacing=10)
    notes = ft.Column(spacing=4)
    bands = ft.Column(spacing=6)
    bands_header = ft.Text(size=13, opacity=0.7)

    def build_home():
        sw = app["sw"]
        tiles.controls.clear()
        notes.controls.clear()
        if not sw:
            return
        tiles.controls += [
            tile("Solar flux", f"{sw.sfi:.0f}", f"SSN ~{sw.ssn:.0f}", sfi_color(sw.sfi)),
            tile("Kp index", f"{sw.kp:.1f}", f"A = {sw.a_index:.0f}", kp_color(sw.kp)),
            tile("X-ray", sw.xray_class, "GOES flare class", xr_color(sw.xray_flux))]
        for k, v in spaceweather.summarize(sw).items():
            notes.controls.append(ft.Text(f"• {v}", size=14))
        age = "live" if sw.live else (f"offline - {sw.age_hours:.0f} h old data" if sw.fetched
                                      else "offline - no data yet, using defaults")
        notes.controls.append(ft.Text(f"Data: NOAA SWPC ({age})", size=12, opacity=0.6))

    def build_bands():
        bands.controls.clear()
        rows = app["rows"]
        if not rows:
            return
        for r in rows:
            reach = r["go"] + r["marginal"]
            reach.sort(key=lambda e: -e["snr"])
            subtitle = (", ".join(e["target"] for e in r["go"][:4]) or "nothing reliable right now")
            items = [ft.ListTile(
                dense=True, leading=ft.Icon(STATE_ICON["GO" if e in r["go"] else "MARGINAL"],
                                            color=STATE_COLOR["GO" if e in r["go"] else "MARGINAL"]),
                title=ft.Text(e["target"]),
                subtitle=ft.Text(f'{e["km"]:.0f} km  •  bearing {e["bearing"]:.0f}°  •  {e["hops"]} hop(s)'))
                for e in reach] or [ft.ListTile(title=ft.Text("No reachable places on this band."))]
            bands.controls.append(ft.Card(content=ft.ExpansionTile(
                leading=ft.Container(
                    width=88, padding=ft.Padding.symmetric(vertical=8), border_radius=8,
                    bgcolor=STATE_COLOR[r["overall"]], alignment=ft.Alignment.CENTER,
                    content=ft.Text(r["band"], weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, size=16)),
                title=ft.Text(r["overall"], weight=ft.FontWeight.BOLD, color=STATE_COLOR[r["overall"]]),
                subtitle=ft.Text(f'{len(r["go"])} good, {len(r["marginal"])} marginal  •  {subtitle}', size=12),
                controls=items)))

    def refresh_views():
        build_home()
        build_bands()
        if s.has_location:
            loc_text.value = f"{s.label}   ({s.lat:.2f}, {s.lon:.2f})   grid {geo.latlon_to_grid(s.lat, s.lon)}"
            when = datetime.now(timezone.utc) + timedelta(hours=app["offset"])
            bands_header.value = f"{loc_text.value}\nPredicted for {when:%Y-%m-%d %H:%M} UTC"
        page.update()

    def compute(offset):
        sw = spaceweather.get_space_weather()
        dt = datetime.now(timezone.utc) + timedelta(hours=offset)
        return sw, predict.band_table(s.lat, s.lon, dt, sw, s.station())

    async def recompute():
        spin.visible = True
        page.update()
        try:
            app["sw"], app["rows"] = await asyncio.to_thread(compute, app["offset"])
        except Exception as ex:
            err.value = f"Could not update: {ex}"
        spin.visible = False
        refresh_views()

    async def go(e=None):
        err.value = ""
        text = where.value.strip()
        if not text:
            err.value = "Enter a zip code, grid square, or lat,lon."
            page.update()
            return
        spin.visible = True
        page.update()
        try:
            lat, lon, label = await asyncio.to_thread(geo.parse_location, text)
        except Exception as ex:
            spin.visible = False
            err.value = str(ex) if isinstance(ex, ValueError) else "Zip lookup needs internet the first time."
            page.update()
            return
        s.where, s.lat, s.lon, s.label = text, lat, lon, label
        cfg.save(s)
        await recompute()

    async def set_offset(e):
        app["offset"] = dict(OFFSETS)[list(e.control.selected)[0]]
        if s.has_location:
            await recompute()

    # ---- screens ----
    home = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=14, controls=[
        ft.Row([where, ft.FilledButton("Go", on_click=go, height=48), spin]),
        err, loc_text, tiles, notes])
    bands_view = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=8, controls=[
        ft.SegmentedButton(selected=["Now"], allow_empty_selection=False, on_change=set_offset,
                           segments=[ft.Segment(value=n, label=ft.Text(n)) for n, _ in OFFSETS]),
        bands_header, bands])

    def save_set(e=None):
        s.mode = mode.selected and list(mode.selected)[0]
        try:
            s.power_w = max(1.0, float(power.value))
        except ValueError:
            pass
        s.noise = noise.value
        cfg.save(s)

    async def apply_set(e):
        save_set()
        if s.has_location:
            await recompute()

    mode = ft.SegmentedButton(selected=[s.mode], allow_empty_selection=False, on_change=apply_set,
                              segments=[ft.Segment(value=v, label=ft.Text(t)) for v, t in
                                        (("ssb", "SSB"), ("cw", "CW"), ("digital", "Digital"))])
    power = ft.TextField(label="Transmit power (watts)", value=f"{s.power_w:g}", width=220,
                         on_blur=apply_set, on_submit=apply_set)
    noise = ft.Dropdown(label="Your noise level", value=s.noise, width=220, on_select=apply_set,
                        options=[ft.DropdownOption(key=k, text=t) for k, t in
                                 (("quiet", "Quiet / rural"), ("residential", "Residential"), ("city", "City / noisy"))])
    settings_view = ft.Column(spacing=16, controls=[
        ft.Text("Defaults work fine - change these only if you want to.", opacity=0.7),
        ft.Text("Mode"), mode, power, noise,
        ft.Text("Predictions are an empirical estimate for planning, not a guarantee.", size=12, opacity=0.6)])

    views = [home, bands_view, settings_view]
    start = int(os.environ.get("HFPROP_TAB", "0"))   # developer aid: open on a given tab
    body = ft.Container(content=views[start], padding=16, expand=True)

    def nav_change(e):
        body.content = views[e.control.selected_index]
        page.update()

    page.navigation_bar = ft.NavigationBar(selected_index=start, on_change=nav_change, destinations=[
        ft.NavigationBarDestination(icon=ft.Icons.HOME, label="Home"),
        ft.NavigationBarDestination(icon=ft.Icons.SIGNAL_CELLULAR_ALT, label="Bands"),
        ft.NavigationBarDestination(icon=ft.Icons.TUNE, label="Settings")])
    page.add(ft.SafeArea(expand=True, content=body))

    if s.has_location:
        await recompute()


if __name__ == "__main__":
    ft.run(main)
