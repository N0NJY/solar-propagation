"""Flet front end for hfprop.  Run:  .venv/bin/python -m app.main"""
import asyncio
import os
from datetime import datetime, timezone, timedelta

import flet as ft

from hfprop import geo, predict, settings as cfg, spaceweather
from app.mapview import MapView, STATE_FILL

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
    app = {"sw": None, "rows": None, "offset": 0, "band": "20m", "target": None}

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

    band_chips = ft.Row(scroll=ft.ScrollMode.AUTO, spacing=6)
    map_when = ft.Text(size=13, opacity=0.7)
    target_title = ft.Text(size=15, weight=ft.FontWeight.W_600)
    target_row = ft.Row(wrap=True, spacing=6, run_spacing=6)

    def pick_target(t):
        app["target"] = t
        update_map()
        page.update()

    mapview = MapView(on_pick=pick_target)

    def pick_band(name):
        app["band"] = name
        update_map()
        page.update()

    def update_map():
        rows = app["rows"]
        band_chips.controls = [
            ft.Chip(label=ft.Text(b), selected=(b == app["band"]), show_checkmark=False,
                    on_click=lambda e, b=b: pick_band(b)) for b, _ in predict.BANDS]
        if not rows or not s.has_location:
            return
        row = next((r for r in rows if r["band"] == app["band"]), rows[0])
        states = {e["target"]: "GO" for e in row["go"]}
        states.update({e["target"]: "MARGINAL" for e in row["marginal"]})
        when = datetime.now(timezone.utc) + timedelta(hours=app["offset"])
        map_when.value = f'{app["band"]} - {row["overall"]} - {when:%Y-%m-%d %H:%M} UTC'
        mapview.set_data((s.lat, s.lon, s.label), when, states, app["target"])
        t = app["target"]
        target_row.controls.clear()
        if not t:
            target_title.value = "Tap a place on the map to see every band to it."
            return
        d = geo.distance_km(s.lat, s.lon, t[2], t[3])
        b = geo.bearing_deg(s.lat, s.lon, t[2], t[3])
        target_title.value = f"{t[0]}  -  {d:,.0f} km, bearing {b:.0f}\N{DEGREE SIGN}"
        for r in predict.target_bands(s.lat, s.lon, t, when, app["sw"], s.station()):
            target_row.controls.append(ft.Container(
                padding=ft.Padding.symmetric(horizontal=10, vertical=6), border_radius=8,
                bgcolor=STATE_FILL[r["state"]],
                content=ft.Text(r["band"], size=13, weight=ft.FontWeight.BOLD,
                                color=ft.Colors.WHITE if r["state"] != "NO-GO" else ft.Colors.BLACK87)))

    def refresh_views():
        build_home()
        build_bands()
        update_map()
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

    legend = ft.Row(spacing=14, controls=[
        ft.Row(spacing=5, controls=[ft.Container(width=12, height=12, border_radius=6, bgcolor=STATE_FILL[k]),
                                    ft.Text(t, size=12)])
        for k, t in (("GO", "Good"), ("MARGINAL", "Marginal"), ("NO-GO", "Not reachable"))] +
        [ft.Row(spacing=5, controls=[ft.Container(width=12, height=12, border_radius=6, bgcolor="#ffd400"),
                                     ft.Text("Sun overhead", size=12)])])
    map_view = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=10, controls=[
        band_chips, map_when, mapview.control, legend, target_title, target_row])

    views = [home, bands_view, map_view, settings_view]
    start = int(os.environ.get("HFPROP_TAB", "0"))   # developer aid: open on a given tab
    body = ft.Container(content=views[start], padding=16, expand=True)

    def nav_change(e):
        body.content = views[e.control.selected_index]
        page.update()

    page.navigation_bar = ft.NavigationBar(selected_index=start, on_change=nav_change, destinations=[
        ft.NavigationBarDestination(icon=ft.Icons.HOME, label="Home"),
        ft.NavigationBarDestination(icon=ft.Icons.SIGNAL_CELLULAR_ALT, label="Bands"),
        ft.NavigationBarDestination(icon=ft.Icons.PUBLIC, label="Map"),
        ft.NavigationBarDestination(icon=ft.Icons.TUNE, label="Settings")])
    page.add(ft.SafeArea(expand=True, content=body))

    if s.has_location:
        await recompute()


if __name__ == "__main__":
    ft.run(main)
