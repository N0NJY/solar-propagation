"""Space Wx page: NOAA scales, solar wind, X-ray flares, Kp, alerts, CMEs."""
import asyncio
import math
import time
from datetime import datetime, timezone

import flet as ft
import flet.canvas as cv

from hfprop import swx, units

LEVEL_COLOR = ["#2e9e4f", "#c9b200", "#e08a00", "#e0600b", "#d63b2f", "#a8122a"]
SCALE_NAME = {"R": "Radio blackouts", "S": "Radiation storms", "G": "Geomagnetic storms"}


def _fill(c, o=1.0):
    return ft.Paint(color=ft.Colors.with_opacity(o, c), style=ft.PaintingStyle.FILL)


def _stroke(c, w=1.0, o=1.0):
    return ft.Paint(color=ft.Colors.with_opacity(o, c), style=ft.PaintingStyle.STROKE, stroke_width=w)


class Chart:
    """A canvas that redraws itself at the size it is given: draw(w, h) -> shapes."""

    def __init__(self, height, draw):
        self.draw_fn, self.data = draw, None
        self.w = self.h = 0
        self.canvas = cv.Canvas(shapes=[], on_resize=self._resize, expand=True)
        self.control = ft.Container(height=height, content=self.canvas, border_radius=8,
                                    bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.BLUE_GREY))

    def _resize(self, e):
        if not (0 < e.width < 1e5 and 0 < e.height < 1e5):
            return
        self.w, self.h = e.width, e.height
        self.redraw()

    def set_data(self, data):
        self.data = data
        self.redraw()

    def redraw(self):
        if not (self.w and self.h):
            return
        self.canvas.shapes = self.draw_fn(self.data, self.w, self.h) if self.data else []
        try:
            self.canvas.update()
        except Exception:
            pass


def _label(x, y, text, size=10, color="#667085", align=None):
    return cv.Text(x, y, text, ft.TextStyle(size=size, color=color))


# ---------- chart drawers ----------
def draw_xray(rows, w, h):
    lo, hi, L, R, T, B = -8.0, -3.0, 34, 8, 8, 18
    def y(flux):
        v = math.log10(max(flux, 1e-9))
        return T + (hi - min(max(v, lo), hi)) / (hi - lo) * (h - T - B)
    shapes = []
    for exp, name in ((-8, "A"), (-7, "B"), (-6, "C"), (-5, "M"), (-4, "X")):
        yy = y(10 ** exp)
        shapes.append(cv.Line(L, yy, w - R, yy, _stroke("#98a2b3", 0.8, 0.5)))
        shapes.append(_label(6, yy - 7, name, 11, "#475467"))
    n = len(rows)
    pts = [(L + i / max(1, n - 1) * (w - L - R), y(f)) for i, (_, f) in enumerate(rows)]
    els = [cv.Path.MoveTo(*pts[0])] + [cv.Path.LineTo(*p) for p in pts[1:]]
    shapes.append(cv.Path(els, paint=_stroke("#1b4f9c", 1.8)))
    shapes.append(_label(L, h - 14, "6 hours ago", 10))
    shapes.append(_label(w - R - 22, h - 14, "now", 10))
    return shapes


def draw_bz(rows, w, h):
    """Bz over time; south (negative) filled red, north blue."""
    vals = [r.get("bz") for r in rows if r.get("bz") is not None]
    if len(vals) < 2:
        return []
    span = max(10.0, max(abs(v) for v in vals) * 1.15)
    L, R, T, B = 34, 8, 8, 18
    y0 = T + (h - T - B) / 2
    def y(v):
        return y0 - v / span * (h - T - B) / 2
    shapes = [cv.Line(L, y0, w - R, y0, _stroke("#667085", 1.0, 0.7)),
              cv.Line(L, y(-5), w - R, y(-5), _stroke("#e08a00", 0.8, 0.6)),
              _label(4, y0 - 7, "0", 10), _label(4, y(-5) - 7, "-5", 10, "#c26e00"),
              _label(4, T - 2, f"+{span:.0f}", 10), _label(4, h - B - 12, f"-{span:.0f}", 10)]
    n = len(vals)
    pts = [(L + i / (n - 1) * (w - L - R), y(v)) for i, v in enumerate(vals)]
    shapes.append(cv.Path([cv.Path.MoveTo(*pts[0])] + [cv.Path.LineTo(*p) for p in pts[1:]],
                          paint=_stroke("#d63b2f" if vals[-1] < -5 else "#1b4f9c", 1.8)))
    shapes.append(_label(L, h - 14, f"{n} min ago", 10))
    shapes.append(_label(w - R - 22, h - 14, "now", 10))
    return shapes


def kp_color(kp):
    return LEVEL_COLOR[0] if kp < 4 else LEVEL_COLOR[1] if kp < 5 else LEVEL_COLOR[2] if kp < 6 else \
        LEVEL_COLOR[3] if kp < 7 else LEVEL_COLOR[4] if kp < 8 else LEVEL_COLOR[5]


def draw_kp(rows, w, h):
    L, R, T, B = 22, 6, 8, 18
    n = len(rows)
    slot = (w - L - R) / n
    shapes = []
    for k in (0, 3, 5, 7, 9):
        yy = T + (9 - k) / 9 * (h - T - B)
        shapes.append(cv.Line(L, yy, w - R, yy, _stroke("#98a2b3", 0.6, 0.5)))
        shapes.append(_label(4, yy - 7, str(k), 10))
    last_day = None
    for i, r in enumerate(rows):
        top = T + (9 - min(r["kp"], 9)) / 9 * (h - T - B)
        x = L + i * slot
        shapes.append(cv.Rect(x + 1, top, max(1.0, slot - 2), h - B - top,
                              paint=_fill(kp_color(r["kp"]), 0.95 if r["observed"] else 0.40)))
        day = r["t"][5:10]
        if day != last_day and r["t"][11:13] == "00":
            shapes.append(cv.Line(x, T, x, h - B, _stroke("#667085", 0.8, 0.5)))
            shapes.append(_label(x + 2, h - 14, day, 10))
        last_day = day
    return shapes


# ---------- page ----------
def card(title, *controls, subtitle=None):
    head = [ft.Text(title, size=16, weight=ft.FontWeight.W_600)]
    if subtitle:
        head.append(ft.Text(subtitle, size=12, opacity=0.65))
    return ft.Card(content=ft.Container(padding=14, content=ft.Column(spacing=10, controls=head + list(controls))))


def stat(title, value, sub="", color=None, width=150):
    return ft.Container(width=width, padding=10, border_radius=10,
                        bgcolor=ft.Colors.with_opacity(0.10, color or ft.Colors.BLUE_GREY),
                        content=ft.Column(spacing=1, controls=[
                            ft.Text(title, size=12, opacity=0.7),
                            ft.Text(value, size=22, weight=ft.FontWeight.BOLD, color=color),
                            ft.Text(sub, size=11, opacity=0.7)]))


def hf_impact(d):
    """Plain-English HF consequences from the current readings."""
    out = []
    sc, wind, kp = d.get("scales"), d.get("wind"), d.get("kp")
    if sc:
        r, g, s = sc["now"]["R"], sc["now"]["G"], sc["now"]["S"]
        if r >= 1: out.append(f"R{r} radio blackout under way: {swx.SCALE_TEXT['R'][r]}.")
        if g >= 1: out.append(f"G{g} geomagnetic storm: {swx.SCALE_TEXT['G'][g]}.")
        if s >= 1: out.append(f"S{s} radiation storm: {swx.SCALE_TEXT['S'][s]}.")
        if max(sc["day1"]["G"], sc["day2"]["G"], sc["day3"]["G"]) >= 1 and g == 0:
            out.append("NOAA forecasts a geomagnetic storm in the next 3 days.")
    if wind:
        bz, speed = swx.latest(wind, "bz"), swx.latest(wind, "speed")
        if bz is not None and bz <= -10:
            out.append("Strong southward Bz: geomagnetic activity may rise soon; high-latitude HF paths can degrade.")
        elif bz is not None and bz <= -5:
            out.append("Bz is southward: watch for rising geomagnetic activity.")
        if speed and speed >= 600:
            out.append("Fast solar wind (>=600 km/s): disturbed polar and auroral paths likely.")
    if kp:
        obs = [r for r in kp if r["observed"]]
        if obs and obs[-1]["kp"] >= 5:
            out.append("Kp is at storm level now.")
    return out or ["No space-weather disturbances right now: HF conditions follow the normal solar-flux pattern."]


def build(page: ft.Page, get_offline=lambda: False, get_units=lambda: "metric"):
    """Returns (control, refresh_coro, maybe_refresh_coro)."""
    state = {"t": 0.0, "busy": False}
    status = ft.Text(size=12, opacity=0.65)
    spin = ft.ProgressRing(width=18, height=18, visible=False)
    impact = ft.Column(spacing=4)
    scale_row = ft.Row(wrap=True, spacing=10, run_spacing=10)
    scale_fc = ft.Text(size=12, opacity=0.7)
    wind_row = ft.Row(wrap=True, spacing=10, run_spacing=10)
    wind_note = ft.Text(size=12, opacity=0.65)
    bz_chart = Chart(130, draw_bz)
    xray_chart = Chart(150, draw_xray)
    xray_now = ft.Text(size=13)
    flare_txt = ft.Column(spacing=2)
    kp_chart = Chart(140, draw_kp)
    alerts = ft.Column(spacing=4)
    cme_text = ft.Text(size=14)
    cme_img = ft.Image(src=swx.IMAGES["lasco_c2"], height=260, fit=ft.BoxFit.CONTAIN)
    enlil_img = ft.Image(src=swx.IMAGES["enlil"], height=260, fit=ft.BoxFit.CONTAIN)
    discussion = ft.Column(spacing=8)

    def fill(d):
        impact.controls = [ft.Text(f"• {t}", size=14) for t in hf_impact(d)]
        sc = d.get("scales")
        if sc:
            scale_row.controls = [
                stat(f"{SCALE_NAME[k]}", f"{k}{sc['now'][k]}",
                     swx.SCALE_TEXT[k][sc["now"][k]].split(":")[0], LEVEL_COLOR[sc["now"][k]], width=170)
                for k in "RSG"]
            scale_fc.value = "Forecast next 3 days:  " + "   ".join(
                f"{k}: " + " / ".join(str(sc[f'day{i}'][k]) for i in (1, 2, 3)) for k in "RSG")
        wind = d.get("wind")
        if wind:
            last = wind[-1]
            def col(v, good, warn):
                return LEVEL_COLOR[0] if v < good else LEVEL_COLOR[1] if v < warn else LEVEL_COLOR[4]
            sp, de, bt, bz = (swx.latest(wind, k) for k in ("speed", "density", "bt", "bz"))
            wind_row.controls = [
                stat("Speed", units.speed(sp, get_units()) if sp else "-", "solar wind", col(sp or 0, 450, 600)),
                stat("Density", f"{de:.1f} /cm³" if de else "-", "protons", None),
                stat("Bt", f"{bt:.1f} nT" if bt else "-", "field strength", None),
                stat("Bz", f"{bz:+.1f} nT" if bz is not None else "-", "south (-) is geoeffective",
                     LEVEL_COLOR[0] if (bz or 0) > -5 else LEVEL_COLOR[2] if bz > -10 else LEVEL_COLOR[4])]
            wind_note.value = f"Latest reading {last['t'].replace('T', ' ')} UTC (L1 spacecraft, ~30-60 min ahead of Earth)."
            bz_chart.set_data(wind)
        xr = d.get("xray")
        if xr:
            from hfprop.spaceweather import xray_class
            xray_now.value = f"Now: {xray_class(xr[-1][1])}  (GOES 0.1-0.8 nm)"
            xray_chart.set_data(xr)
        fp = d.get("flares")
        if fp:
            flare_txt.controls = [ft.Text(f"{r['date']}:  C-class {r['C']}%   M-class {r['M']}%   X-class {r['X']}%"
                                          f"   protons {r['proton']}%", size=13) for r in fp]
        if d.get("kp"):
            kp_chart.set_data(d["kp"])
        al = d.get("alerts") or []
        alerts.controls = [ft.ExpansionTile(
            title=ft.Text(a["title"], size=13), subtitle=ft.Text(f"{a['kind']}  -  {a['time']} UTC", size=11),
            controls=[ft.Container(padding=10, content=ft.Text(a["text"], size=11, selectable=True))])
            for a in al] or [ft.Text("No current alerts.", size=13, opacity=0.7)]
        disc = d.get("discussion")
        if disc:
            sec = disc["sections"]
            mention = swx.cme_mentions(sec.get("Solar Activity", ""))
            cme_text.value = mention or "No CME or filament eruption mentioned in NOAA's current discussion."
            discussion.controls = [ft.ExpansionTile(
                title=ft.Text(name, size=13),
                controls=[ft.Container(padding=10, content=ft.Text(txt, size=12, selectable=True))])
                for name, txt in sec.items()]
            status.value = f"NOAA SWPC. Forecast discussion issued {disc['issued']}. Updated {datetime.now():%H:%M}."

    async def refresh(e=None):
        if state["busy"]:
            return
        state["busy"] = True
        spin.visible = True
        page.update()
        try:
            d = await asyncio.to_thread(swx.fetch_all, get_offline())
            fill(d)
            state["t"] = time.time()
        except Exception as ex:
            status.value = f"Could not update: {ex}"
        spin.visible = False
        state["busy"] = False
        page.update()

    async def maybe_refresh():
        if time.time() - state["t"] > 300:
            await refresh()

    content = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=12, horizontal_alignment=ft.CrossAxisAlignment.STRETCH, controls=[
        ft.Row([ft.Text("Space weather", size=20, weight=ft.FontWeight.BOLD), spin,
                ft.IconButton(ft.Icons.REFRESH, tooltip="Refresh", on_click=refresh)]),
        status,
        card("What this means for HF", impact),
        card("NOAA space-weather scales", scale_row, scale_fc,
             subtitle="R = radio blackouts (flares), S = radiation storms, G = geomagnetic storms. 0 is quiet, 5 is extreme."),
        card("Solar wind", wind_row, wind_note, ft.Text("Bz over the last hour (nT)", size=12), bz_chart.control,
             subtitle="Measured about 1.5 million km sunward of Earth. A sustained southward Bz opens the door to storms."),
        card("Solar flares (X-ray flux)", xray_now, xray_chart.control, flare_txt,
             subtitle="Flares cause sudden HF blackouts on the sunlit side. Probabilities are chances in each 24 h."),
        card("Geomagnetic activity (Kp)", kp_chart.control,
             ft.Text("Solid = observed, faded = forecast. Kp 5+ is a storm; high-latitude HF suffers first.",
                     size=12, opacity=0.65)),
        card("CMEs and solar activity", cme_text,
             ft.Row(wrap=True, spacing=12, controls=[
                 ft.Column(spacing=4, controls=[cme_img, ft.Text("SOHO LASCO C2 coronagraph (live). CMEs look like expanding clouds.", size=11, opacity=0.65, width=360)]),
                 ft.Column(spacing=4, controls=[enlil_img, ft.Text("NOAA WSA-Enlil CME model.", size=11, opacity=0.65, width=360)])]),
             subtitle="From NOAA's forecast discussion and live imagery. NASA's DONKI CME catalog is not available right now."),
        card("Alerts, watches and warnings", alerts),
        card("Full NOAA forecast discussion", discussion),
        ft.Container(height=12)])
    return content, refresh, maybe_refresh
