"""Flet front end for hfprop.  Run:  hfprop-app   (or: python -m hfprop_app)"""
import asyncio
import os
from datetime import datetime, timezone, timedelta

import flet as ft

from hfprop import geo, predict, settings as cfg, spaceweather, summary, swx
from hfprop_app import spacewx
from hfprop_app.heard import Heard
from hfprop_app.mapview import MapView, STATE_FILL
from hfprop_app.spacewx import Chart
from hfprop_app.strip import draw_strip

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
    page.window.width, page.window.height = 1000, 780
    page.window.min_width, page.window.min_height = 420, 560
    s = cfg.load()
    if os.environ.get("HFPROP_CALL"):                 # developer aid
        s.callsign = os.environ["HFPROP_CALL"].upper()
    app = {"sw": None, "rows": None, "strip": None, "scales": None, "updated": None, "offset": 0, "band": "20m", "target": None}

    where = ft.TextField(label="Zip code, grid square (FN31), or lat,lon", value=s.where,
                         expand=True, on_submit=lambda e: page.run_task(go))
    loc_text = ft.Text(size=16, weight=ft.FontWeight.W_600)
    err = ft.Text(color=ft.Colors.RED_400, size=13)
    spin = ft.ProgressRing(width=22, height=22, visible=False)
    tiles = ft.Row(wrap=True, spacing=10, run_spacing=10)
    notes = ft.Column(spacing=4)
    bands = ft.Column(spacing=6)
    bands_header = ft.Text(size=13, opacity=0.7)

    banner = ft.Container(visible=False, border_radius=12, padding=12, ink=True, on_click=lambda e: go_tab(3))
    open_card = ft.Column(spacing=8)

    def go_tab(i):
        page.navigation_bar.selected_index = i
        body.content = views[i]
        page.update()
        if i == 3:
            page.run_task(swx_maybe)
        if i == 2:
            page.run_task(heard.maybe_refresh)

    def build_banner():
        sw = app["sw"]
        if not sw:
            banner.visible = False
            return
        level, msgs = summary.alerts(sw, app["scales"])
        color = [ft.Colors.GREEN_600, ft.Colors.AMBER_700, ft.Colors.ORANGE_800, ft.Colors.RED_700][level]
        icon = [ft.Icons.CHECK_CIRCLE, ft.Icons.INFO, ft.Icons.WARNING_AMBER, ft.Icons.REPORT][level]
        banner.bgcolor = ft.Colors.with_opacity(0.14, color)
        banner.border = ft.Border.all(1, ft.Colors.with_opacity(0.5, color))
        banner.content = ft.Row(vertical_alignment=ft.CrossAxisAlignment.START, controls=[
            ft.Icon(icon, color=color),
            ft.Column(spacing=2, expand=True, controls=(
                [ft.Text(m, size=14, weight=ft.FontWeight.W_600) for m in msgs] if msgs else
                [ft.Text("Quiet: no flares or storms. HF follows the normal solar-flux pattern.",
                         size=14, weight=ft.FontWeight.W_600)]) +
                [ft.Text("Tap for details on the Space Wx page.", size=11, opacity=0.6)])])
        banner.visible = True

    def build_open():
        rows = app["rows"]
        open_card.controls.clear()
        if not rows:
            return
        go, marginal = summary.open_now(rows)
        when = "right now" if app["offset"] == 0 else f"at +{app['offset']} h"
        open_card.controls.append(ft.Text(f"Bands open {when}", size=16, weight=ft.FontWeight.W_600))
        if go:
            open_card.controls.append(ft.Row(wrap=True, spacing=8, run_spacing=8, controls=[
                ft.Container(padding=ft.Padding.symmetric(horizontal=12, vertical=8), border_radius=10,
                             bgcolor=STATE_COLOR["GO"],
                             content=ft.Text(f"{b}  \u00b7  {n} regions", color=ft.Colors.WHITE,
                                             weight=ft.FontWeight.BOLD, size=14)) for b, n in go]))
        else:
            open_card.controls.append(ft.Text("No band looks reliable at the moment.", size=14))
        if marginal:
            open_card.controls.append(ft.Text("Marginal: " + ", ".join(marginal), size=13, opacity=0.8))
        if app["strip"] and app["offset"] == 0:
            nxt = summary.next_openings(app["strip"])
            if nxt:
                open_card.controls.append(ft.Text(
                    "Next openings: " + "; ".join(f"{b} in {h} h ({u:02d}Z)" for b, h, u in nxt),
                    size=13, opacity=0.8))

    def build_home():
        build_banner()
        build_open()
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
        upd = f"  -  updated {app['updated']:%H:%M}" if app["updated"] else ""
        notes.controls.append(ft.Text(f"Data: NOAA SWPC ({age}){upd}", size=12, opacity=0.6))

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

    strip_chart = Chart(300, draw_strip)
    strip_card = ft.Card(content=ft.Container(padding=14, content=ft.Column(spacing=8, controls=[
        ft.Text("Best times: next 24 hours", size=16, weight=ft.FontWeight.W_600),
        ft.Text("Each row is a band; each column an hour starting now (outlined). Green = good, "
                "amber = marginal, faint = closed. Local time is approximate (from your longitude).",
                size=12, opacity=0.65),
        strip_chart.control])))

    band_chips = ft.Row(scroll=ft.ScrollMode.AUTO, spacing=6)
    map_when = ft.Text(size=13, opacity=0.7)
    target_title = ft.Text(size=15, weight=ft.FontWeight.W_600)
    target_row = ft.Row(wrap=True, spacing=6, run_spacing=6)

    def pick_target(t):
        app["target"] = t
        update_map()
        page.update()

    def heard_redraw():
        update_map()
        page.update()

    heard = Heard(page, lambda: s, lambda: {"band": app["band"], "sw": app["sw"]}, cfg.save, heard_redraw)
    mapview = MapView(on_pick=pick_target, on_pick_station=heard.pick)

    def fit_map(e=None):
        """Size the 2:1 map to fit the window so the whole map and its legend are visible."""
        w, h = page.width or 1000, page.height or 700
        mapview.control.width = max(300, min(w - 32, 2 * (h - 270)))
        mapview.control.height = mapview.control.width / 2
        try:
            page.update()
        except Exception:
            pass

    page.on_resize = fit_map

    def layers_change(e):
        sel = set(e.control.selected)
        mapview.show_dots, mapview.show_heat = "places" in sel, "heat" in sel
        mapview.show_heard = heard.enabled = "heard" in sel
        update_map()
        target_title.visible = mapview.show_dots
        target_row.visible = mapview.show_dots
        page.update()
        if heard.enabled:
            page.run_task(heard.maybe_refresh)

    heard.enabled = mapview.show_heard = bool(s.callsign)
    layers = ft.SegmentedButton(selected=["places", "heat"] + (["heard"] if s.callsign else []),
                                allow_multiple_selection=True,
                                allow_empty_selection=True, on_change=layers_change,
                                segments=[ft.Segment(value="places", label=ft.Text("Places")),
                                          ft.Segment(value="heat", label=ft.Text("Heat map")),
                                          ft.Segment(value="heard", label=ft.Text("Heard"))])

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
        freq = dict(predict.BANDS)[app["band"]]
        heat = predict.reach_grid(s.lat, s.lon, freq, when, app["sw"], s.station(), mapview.heat_step)
        mapview.set_data((s.lat, s.lon, s.label), when, states, app["target"], heat,
                         heard.stations(app["band"]), heard.selected)
        heard.render()
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
                                color=ft.Colors.WHITE if r["state"] != "NO-GO" else ft.Colors.BLACK_87)))

    def refresh_views():
        if app["strip"]:
            strip_chart.set_data(app["strip"])
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
        first = dt.replace(minute=0, second=0, microsecond=0)
        strip = {"grid": predict.day_strip(s.lat, s.lon, first, sw, s.station()),
                 "start_hour": first.hour, "lon": s.lon}
        return sw, predict.band_table(s.lat, s.lon, dt, sw, s.station()), strip, swx.get_scales()

    async def recompute():
        spin.visible = True
        page.update()
        try:
            app["sw"], app["rows"], app["strip"], app["scales"] = await asyncio.to_thread(compute, app["offset"])
            app["updated"] = datetime.now()
            err.value = ""
        except Exception as ex:
            err.value = f"Could not update: {ex}"
        spin.visible = False
        refresh_views()

    async def go(e=None):
        err.value = ""
        err.color = ft.Colors.RED_400
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
    async def find_me(e):
        err.value = ""
        spin.visible = True
        page.update()
        try:
            lat, lon, label = await asyncio.to_thread(geo.locate_by_ip)
        except Exception as ex:
            spin.visible = False
            err.value = str(ex) if isinstance(ex, ValueError) else "Could not look up your location (need internet). Type a zip or grid instead."
            page.update()
            return
        grid = geo.latlon_to_grid(lat, lon)
        where.value = grid
        s.where, s.lat, s.lon, s.label = grid, lat, lon, f"{label} ({grid})"
        cfg.save(s)
        await recompute()

    home = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=14, controls=[
        ft.Row([where, ft.FilledButton("Go", on_click=go, height=48), spin]),
        ft.Row(wrap=True, spacing=8, controls=[
            ft.OutlinedButton("Find me (approximate)", icon=ft.Icons.MY_LOCATION, on_click=find_me),
            ft.Text("Uses your internet address; accurate to about the city.", size=12, opacity=0.6)]),
        err, loc_text, banner, open_card, tiles, notes])
    bands_view = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=8, controls=[
        ft.SegmentedButton(selected=["Now"], allow_empty_selection=False, on_change=set_offset,
                           segments=[ft.Segment(value=n, label=ft.Text(n)) for n, _ in OFFSETS]),
        bands_header, strip_card, bands])

    def save_set(e=None):
        s.mode = mode.selected and list(mode.selected)[0]
        try:
            s.power_w = max(1.0, float(power.value))
        except ValueError:
            pass
        s.noise = noise.value
        s.gain_dbi = float(antenna.value)
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
    async def save_call(e):
        s.callsign = call.value.strip().upper()
        call.value = s.callsign
        cfg.save(s)
        heard.call_field.value = s.callsign
        heard.rows, heard.age = [], None
        if s.callsign and not heard.enabled:
            heard.enabled = mapview.show_heard = True
            layers.selected = sorted(set(layers.selected) | {"heard"})
        await heard.refresh()

    call = ft.TextField(label="Your callsign (optional)", value=s.callsign, width=220,
                        on_blur=save_call, on_submit=save_call, capitalization=ft.TextCapitalization.CHARACTERS)
    noise = ft.Dropdown(label="Your noise level", value=s.noise, width=220, on_select=apply_set,
                        options=[ft.DropdownOption(key=k, text=t) for k, t in
                                 (("quiet", "Quiet / rural"), ("residential", "Residential"), ("city", "City / noisy"))])
    gains = [(-6.0, "Compromise / indoor / loaded (-6 dBi)"), (-2.0, "Vertical or ground-mounted (-2 dBi)"),
             (0.0, "Dipole or wire (0 dBi)"), (6.0, "Small beam (+6 dBi)"), (11.0, "Large beam (+11 dBi)")]
    gain_now = min(gains, key=lambda g: abs(g[0] - s.gain_dbi))[0]
    antenna = ft.Dropdown(label="Your antenna", value=str(gain_now), width=340, on_select=apply_set,
                          options=[ft.DropdownOption(key=str(g), text=t) for g, t in gains])
    settings_view = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=16, controls=[
        ft.Text("Defaults work fine - change these only if you want to.", opacity=0.7),
        ft.Text("Mode"), mode, power, antenna, noise, call,
        ft.Text("A callsign shows real stations that heard you on the map (PSK Reporter).", size=12, opacity=0.65),
        ft.Text("Predictions are an empirical estimate for planning, not a guarantee.", size=12, opacity=0.6)])

    legend = ft.Row(spacing=14, controls=[
        ft.Row(spacing=5, controls=[ft.Container(width=12, height=12, border_radius=6, bgcolor=STATE_FILL[k]),
                                    ft.Text(t, size=12)])
        for k, t in (("GO", "Good"), ("MARGINAL", "Marginal"), ("NO-GO", "Not reachable"))] +
        [ft.Row(spacing=5, controls=[ft.Container(width=12, height=12, border_radius=6, bgcolor="#ffd400"),
                                     ft.Text("Sun overhead", size=12)])])
    legend_note = ft.Text("Dots are representative points for each region, not stations. "
                          "Heat map: green = signal expected, deeper green = stronger; amber = marginal; "
                          "no color = not reachable.", size=12, opacity=0.65)
    map_view = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=10, controls=[
        band_chips, ft.Row([map_when, layers], alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            wrap=True), ft.Row([mapview.control], alignment=ft.MainAxisAlignment.CENTER), legend, legend_note, heard.control, target_title, target_row])

    swx_view, swx_refresh, swx_maybe = spacewx.build(page)
    views = [home, bands_view, map_view, swx_view, settings_view]
    start = int(os.environ.get("HFPROP_TAB", "0"))   # developer aid: open on a given tab
    body = ft.Container(content=views[start], padding=16, expand=True)

    def nav_change(e):
        body.content = views[e.control.selected_index]
        page.update()
        if e.control.selected_index == 3:
            page.run_task(swx_maybe)
        if e.control.selected_index == 2:
            page.run_task(heard.maybe_refresh)

    page.navigation_bar = ft.NavigationBar(selected_index=start, on_change=nav_change, destinations=[
        ft.NavigationBarDestination(icon=ft.Icons.HOME, label="Home"),
        ft.NavigationBarDestination(icon=ft.Icons.SIGNAL_CELLULAR_ALT, label="Bands"),
        ft.NavigationBarDestination(icon=ft.Icons.PUBLIC, label="Map"),
        ft.NavigationBarDestination(icon=ft.Icons.WB_SUNNY, label="Space Wx"),
        ft.NavigationBarDestination(icon=ft.Icons.TUNE, label="Settings")])
    page.add(ft.SafeArea(expand=True, content=body))

    fit_map()
    if not s.has_location:
        err.value = "Welcome! Enter a zip code, grid square, or lat,lon above, or press Find me."
        err.color = ft.Colors.BLUE_GREY
    heard.call_field.value = s.callsign
    if start == 3:
        await swx_maybe()
    if s.has_location:
        await recompute()
    if heard.enabled and s.callsign:
        await heard.refresh()
    async def ticker():
        """Keep 'now' fresh while the app stays open."""
        while True:
            await asyncio.sleep(600)
            try:
                if s.has_location:
                    await recompute()
                if heard.enabled and s.callsign:
                    await heard.maybe_refresh()
            except Exception:
                return                              # window closed

    page.run_task(ticker)
    if os.environ.get("HFPROP_SCROLL"):          # developer aid for screenshots
        await asyncio.sleep(2)
        await views[start].scroll_to(offset=int(os.environ["HFPROP_SCROLL"]), duration=0)


def run():
    ft.run(main)


if __name__ == "__main__":
    run()
