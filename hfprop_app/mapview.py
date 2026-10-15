"""World map on a Flet canvas: zoom / pan / pinch, coastlines, lakes, borders, states, cities,
Maidenhead grid squares, night shading, heat map, region dots and real (PSK) stations."""
import math
import os
import threading
import time

import flet as ft
import flet.canvas as cv

from hfprop import mapdata, units as U
from hfprop.solar import subsolar_point
from hfprop.targets import TARGETS

OCEAN = "#cfe3ef"
LAND = "#a9c49a"
GRID = "#9fb9c8"
BORDER = "#6c7a89"
STATE = "#8b98a5"
HEARD_ME, I_HEARD, BOTH = "#1b6fd8", "#8e44c8", "#0a9e96"
STATE_FILL = {"GO": "#2e9e4f", "MARGINAL": "#f0a000", "NO-GO": "#b8bcc2"}
PROFILE = bool(os.environ.get("HFPROP_PROFILE"))      # developer aid: print draw timings
SETTLE_DELAY = float(os.environ.get("HFPROP_SETTLE", "0.25"))   # idle seconds after zoom / drag before the sharp redraw
PREVIEW_INTERVAL = 0.03       # seconds between instant (transform-only) previews


def _fill(color, opacity=1.0):
    return ft.Paint(color=ft.Colors.with_opacity(opacity, color), style=ft.PaintingStyle.FILL)


def _stroke(color, width=1.0, opacity=1.0):
    return ft.Paint(color=ft.Colors.with_opacity(opacity, color), style=ft.PaintingStyle.STROKE,
                    stroke_width=width)


def heat_step(z):
    """Heat-map cell size (degrees) for a zoom level: finer as you zoom in."""
    return 6.0 if z < 2.5 else 3.0 if z < 5 else 1.5 if z < 10 else 0.75 if z < 20 else 0.5


class MapView:
    def __init__(self, on_pick, on_pick_station=None, on_hover=None):
        self.on_pick = on_pick
        self.on_hover = on_hover      # callable(bool): pointer entered / left the map
        self.on_pick_station = on_pick_station
        self.w = self.h = 0
        self.view = mapdata.View()
        self.me = None            # (lat, lon, label)
        self.dt = None
        self.states = {}          # target name -> GO / MARGINAL
        self.selected = None      # target tuple
        self.heat_fn = None       # callable(bounds, step) -> reach_grid cells
        self.stations = []        # real PSK Reporter stations (heard layer)
        self.selected_call = None
        self.units = "metric"
        self.show_dots = self.show_heat = True
        self.show_heard = False
        self.show_borders = self.show_states = self.show_cities = True
        self.show_grid = False
        self._gesture = None
        self._drawn = None        # (z, clon, clat) the canvas was last drawn with
        self._last_preview = 0.0
        self._settle_timer = None
        self.canvas = cv.Canvas(shapes=[], on_resize=self._resize, expand=True)
        self.holder = ft.Container(content=self.canvas, expand=True)   # moved / scaled for instant previews
        self.zoom_label = ft.Text("1x", size=11, weight=ft.FontWeight.W_600, color="#10233f")
        self.control = ft.Container(
            width=1000, height=500, bgcolor=OCEAN, border_radius=10, clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            content=ft.Stack(fit=ft.StackFit.EXPAND, controls=[
                ft.GestureDetector(
                    expand=True, content=self.holder, on_tap_up=self._tap, on_scroll=self._scroll,
                    on_enter=lambda e: self._hover(True), on_exit=lambda e: self._hover(False),
                    on_scale_start=self._scale_start, on_scale_update=self._scale_update,
                    on_scale_end=self._scale_end),
                ft.Container(right=8, top=8, padding=4, border_radius=10,
                             bgcolor=ft.Colors.with_opacity(0.85, ft.Colors.WHITE),
                             content=ft.Column(spacing=0, tight=True,
                                               horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                                 self._btn(ft.Icons.ADD, "Zoom in", lambda e: self.zoom_by(2.0)),
                                 self.zoom_label,
                                 self._btn(ft.Icons.REMOVE, "Zoom out", lambda e: self.zoom_by(0.5)),
                                 self._btn(ft.Icons.MY_LOCATION, "Zoom to my location", lambda e: self.zoom_to_me()),
                                 self._btn(ft.Icons.PUBLIC, "Whole world", lambda e: self.reset_view())]))]))

    @staticmethod
    def _btn(icon, tip, handler):
        return ft.IconButton(icon, tooltip=tip, on_click=handler, icon_size=20, icon_color="#10233f",
                             width=36, height=36)

    # ---- view control ----
    def zoom_by(self, factor):
        if self.w:
            self.view.zoom_at(factor, self.w / 2, self.h / 2, self.w, self.h)
            self._view_changed()

    def zoom_to_me(self, z=8.0):
        if self.me:
            self.view.center_on(self.me[0], self.me[1], z)
            self.draw()

    def reset_view(self):
        self.view = mapdata.View()
        self.draw()

    def _resize(self, e):
        if not (0 < e.width < 1e5 and 0 < e.height < 1e5):     # layout pass can report inf/0
            return
        self.w, self.h = e.width, e.height
        self.draw()

    def set_data(self, me, dt, states, selected, heat_fn=None, stations=None, selected_call=None):
        self.me, self.dt, self.states, self.selected = me, dt, states, selected
        self.heat_fn = heat_fn
        self.stations, self.selected_call = stations or [], selected_call
        self.draw()

    # ---- gestures: mouse wheel, drag-pan, pinch (touch), tap ----
    def _scroll(self, e):
        if not self.w:
            return
        dy = getattr(e.scroll_delta, "y", 0) or 0
        if dy:
            self.view.zoom_at(1.25 if dy < 0 else 0.8, e.local_position.x, e.local_position.y, self.w, self.h)
            self._view_changed()

    def _scale_start(self, e):
        if not self.w:
            return
        fx, fy = e.local_focal_point.x, e.local_focal_point.y
        lon, lat = self.view.to_lonlat(fx, fy, self.w, self.h)
        self._gesture = (self.view.z, lon, lat)

    def _scale_update(self, e):
        if not (self.w and self._gesture):
            return
        z0, lon, lat = self._gesture
        self.view.drag_to(lon, lat, e.local_focal_point.x, e.local_focal_point.y, self.w, self.h,
                          z=z0 * (e.scale or 1.0))
        self._view_changed()

    def _scale_end(self, e):
        self._gesture = None
        self._view_changed()

    def _hover(self, inside):
        if self.on_hover:
            self.on_hover(inside)

    def _view_changed(self):
        """Zoom / pan feedback without a redraw: the already-drawn map is scaled and moved on the
        display side (cheap), then one sharp redraw is made once the view stops changing."""
        now = time.monotonic()
        if self._drawn and now - self._last_preview >= PREVIEW_INTERVAL:
            self._last_preview = now
            z0, clon0, clat0 = self._drawn
            sl, sa = 360.0 / z0, 180.0 / z0
            tx, ty = self.view.to_xy(clon0 - sl / 2, clat0 + sa / 2, self.w, self.h)   # old top-left corner
            k = self.view.z / z0
            self.holder.transform = ft.Transform(
                matrix=ft.Matrix4.translation_values(tx, ty, 0).scale(k),
                alignment=ft.Alignment.TOP_LEFT, transform_hit_tests=False)
            try:
                self.holder.update()
            except Exception:
                pass
        if self._settle_timer:
            self._settle_timer.cancel()
        self._settle_timer = threading.Timer(SETTLE_DELAY, self.draw)
        self._settle_timer.daemon = True
        self._settle_timer.start()

    def _tap(self, e):
        if not self.w:
            return
        x, y = e.local_position.x, e.local_position.y
        if self.show_heard and self.on_pick_station:
            near, nd = None, max(16.0, self.w * 0.02)
            for st in self.stations:
                px, py = self.view.to_xy(st["lon"], st["lat"], self.w, self.h)
                d = math.hypot(px - x, py - y)
                if d < nd:
                    near, nd = st, d
            if near:
                self.on_pick_station(near["call"])
                return
        if not self.show_dots:
            return
        best, bd = None, max(24.0, self.w * 0.035)
        for t in TARGETS:
            px, py = self.view.to_xy(t[3], t[2], self.w, self.h)
            d = math.hypot(px - x, py - y)
            if d < bd:
                best, bd = t, d
        if best:
            self.on_pick(best)

    # ---- drawing helpers ----
    def _path(self, flat, geo, closed, min_px):
        """Project a flat [lon, lat, ...] list to canvas path elements, dropping points closer
        than min_px to the previous kept one."""
        x0, y1, sx, sy = geo
        els, lx, ly = [], None, None
        n = len(flat)
        for i in range(0, n, 2):
            x = (flat[i] - x0) * sx
            y = (y1 - flat[i + 1]) * sy
            if lx is None:
                els.append(cv.Path.MoveTo(round(x, 1), round(y, 1)))
                lx, ly = x, y
            elif abs(x - lx) + abs(y - ly) >= min_px or i == n - 2:
                els.append(cv.Path.LineTo(round(x, 1), round(y, 1)))
                lx, ly = x, y
        if closed:
            els.append(cv.Path.Close())
        return els

    def _visible(self, bbox, vb):
        return not (bbox[2] < vb[0] or bbox[0] > vb[2] or bbox[3] < vb[1] or bbox[1] > vb[3])

    def _draw_polys(self, name, geo, vb, paint, closed, min_px, shapes):
        for bb, flat in mapdata.shapes(name):
            if self._visible(bb, vb):
                if (bb[2] - bb[0]) * geo[2] < 1.2 and (bb[3] - bb[1]) * geo[3] < 1.2:
                    continue                      # smaller than a pixel
                els = self._path(flat, geo, closed, min_px)
                if len(els) > 2:
                    shapes.append(cv.Path(els, paint=paint))

    def _legend(self):
        """Compact key in the bottom-left corner; skipped when the map is too small for it."""
        bw, bh = 232, (124 if self.show_heard else 104)
        if self.w < bw * 1.6 or self.h < bh * 2:
            return []
        x0, y0 = 10, self.h - bh - 10
        ink = ft.TextStyle(size=11, color="#10233f")
        bold = ft.TextStyle(size=11, weight=ft.FontWeight.BOLD, color="#10233f")
        out = [cv.Rect(x0, y0, bw, bh, border_radius=8, paint=_fill("#ffffff", 0.86))]

        def dot(x, y, color, label, r=5):
            out.append(cv.Circle(x, y + 7, r, _fill(color)))
            out.append(cv.Circle(x, y + 7, r, _stroke("#ffffff", 1.0)))
            out.append(cv.Text(x + 9, y, label, ink))

        def box(x, y, color, alpha, label):
            out.append(cv.Rect(x - 5, y + 2, 10, 10, paint=_fill(color, alpha)))
            out.append(cv.Text(x + 9, y, label, ink))

        out.append(cv.Text(x0 + 10, y0 + 8, "Dots = regions, not stations", bold))
        dot(x0 + 16, y0 + 28, STATE_FILL["GO"], "Good")
        dot(x0 + 70, y0 + 28, STATE_FILL["MARGINAL"], "Marginal")
        dot(x0 + 138, y0 + 28, STATE_FILL["NO-GO"], "Not reachable")
        out.append(cv.Text(x0 + 10, y0 + 50, "Shading = signal strength", bold))
        box(x0 + 16, y0 + 68, "#1f9d4a", 0.65, "Strong")
        box(x0 + 78, y0 + 68, "#1f9d4a", 0.30, "Weak")
        box(x0 + 128, y0 + 68, "#f0a000", 0.42, "Marginal")
        dot(x0 + 16, y0 + 86, "#d6246e", "You", 4)
        dot(x0 + 62, y0 + 86, "#ffd400", "Sun overhead", 4)
        out.append(cv.Rect(x0 + 146, y0 + 89, 10, 10, paint=_fill("#0b1d3a", 0.5)))
        out.append(cv.Text(x0 + 160, y0 + 86, "Night", ink))
        if self.show_heard:
            out.append(cv.Text(x0 + 10, y0 + 104, "Real reports (PSK):", ink))
            for dx, col, lab in ((112, HEARD_ME, "heard me"), (182, I_HEARD, "I heard")):
                out.append(cv.Rect(x0 + dx, y0 + 105, 9, 9, paint=_fill(col)))
                out.append(cv.Text(x0 + dx + 12, y0 + 104, lab, ink))
        return out

    def _scale_bar(self):
        if self.view.z < 2 or self.w < 360:
            return []
        km_px = self.view.km_per_pixel(self.h)
        per_px = U.km_to_unit(km_px, self.units)              # miles or km per pixel
        target = per_px * 130
        mag = 10 ** math.floor(math.log10(target))
        nice = next(m * mag for m in (5, 2, 1) if m * mag <= target)
        px = nice / per_px
        x1, y = self.w - 14, self.h - 18
        x0 = x1 - px
        label = f"{nice:g} {U.dist_unit(self.units)}"
        ink = ft.TextStyle(size=11, weight=ft.FontWeight.W_700, color="#10233f")
        return [cv.Rect(x0 - 8, y - 20, px + 16, 34, border_radius=6, paint=_fill("#ffffff", 0.78)),
                cv.Line(x0, y, x1, y, _stroke("#10233f", 2.0)),
                cv.Line(x0, y - 4, x0, y + 4, _stroke("#10233f", 2.0)),
                cv.Line(x1, y - 4, x1, y + 4, _stroke("#10233f", 2.0)),
                cv.Text(x0 + 2, y - 17, label, ink)]

    @staticmethod
    def _heard_color(st):
        return BOTH if st["heard_me"] and st["i_heard"] else HEARD_ME if st["heard_me"] else I_HEARD

    # ---- main draw ----
    def draw(self):
        if not self.w or not self.h:
            return
        t_start = time.perf_counter()
        v, w, h = self.view, self.w, self.h
        vb = v.bbox()
        geo = (vb[0], vb[3], w / (vb[2] - vb[0]), h / (vb[3] - vb[1]))
        x0, y1, sx, sy = geo
        z = v.z
        self.zoom_label.value = f"{z:g}x" if z < 10 else f"{z:.0f}x"

        def X(lon):
            return (lon - x0) * sx

        def Y(lat):
            return (y1 - lat) * sy

        mp = 1.8                                          # point-thinning distance in pixels
        detailed = z >= 2.2
        shapes = []
        # base: land (coarse when zoomed out, 50 m when zoomed in) and lakes
        self._draw_polys("land50" if detailed else "land", geo, vb, _fill(LAND), True, mp, shapes)
        if z >= 1.6:
            self._draw_polys("lakes50", geo, vb, _fill(OCEAN), True, mp, shapes)

        # heat map: finer cells as you zoom in, only for the visible area
        if self.show_heat and self.heat_fn:
            step = heat_step(z)
            pad = step
            cells = self.heat_fn((vb[0] - pad, vb[1] - pad, vb[2] + pad, vb[3] + pad), step)
            cw, ch = step * sx, step * sy
            runs = []                                     # [lat, lon0, lon1, key]: horizontal runs of like cells
            for la, lo, state, margin in cells:
                if state == "GO":
                    key = ("GO", round(min(1.0, max(0.0, margin) / 20.0) * 3) / 3)   # 4 shades of green
                else:
                    key = (state, 0)
                last = runs[-1] if runs else None
                if last and last[0] == la and last[3] == key and abs(lo - last[2] - step) < 1e-6:
                    last[2] = lo
                else:
                    runs.append([la, lo, lo, key])
            for la, lo0, lo1, (state, shade) in runs:
                if state == "GO":
                    paint = _fill("#1f9d4a", 0.30 + 0.35 * shade)
                else:
                    paint = _fill("#f0a000", 0.42)
                paint.anti_alias = False                  # exact cell edges: no double-blended seams
                shapes.append(cv.Rect(X(lo0) - cw / 2, Y(la) - ch / 2, (lo1 - lo0) * sx + cw, ch, paint=paint))

        # graticule / Maidenhead grid squares
        ppd = sx                                          # pixels per degree of longitude
        if self.show_grid:
            level = 2 if 2 * ppd >= 30 else 1
            cells = mapdata.maidenhead_cells(vb, level)
            for lab, lo0, la0, lo1, la1 in (mapdata.maidenhead_cells(vb, 1) if level == 2 else []):
                shapes.append(cv.Rect(X(lo0), Y(la1), (lo1 - lo0) * sx, (la1 - la0) * sy,
                                      paint=_stroke("#27507a", 1.3, 0.7)))
            label_cells = level == 1 or (2.0 * ppd >= 40 and len(cells) <= 700)
            for lab, lo0, la0, lo1, la1 in cells:
                rx, ry, rw, rh = X(lo0), Y(la1), (lo1 - lo0) * sx, (la1 - la0) * sy
                if level == 1:
                    shapes.append(cv.Rect(rx, ry, rw, rh, paint=_stroke("#27507a", 1.0, 0.55)))
                    if rw > 40:
                        shapes.append(cv.Text(rx + rw / 2 - 9, ry + rh / 2 - 9, lab, ft.TextStyle(
                            size=18, weight=ft.FontWeight.W_700, color=ft.Colors.with_opacity(0.45, "#27507a"))))
                else:
                    shapes.append(cv.Rect(rx, ry, rw, rh, paint=_stroke("#3b5b7a", 0.6, 0.5)))
                    if label_cells:
                        shapes.append(cv.Text(rx + 3, ry + 2, lab, ft.TextStyle(
                            size=11, weight=ft.FontWeight.W_600, color=ft.Colors.with_opacity(0.8, "#27507a"))))
        else:
            gstep = 30 if z < 4 else 10 if z < 12 else 5 if z < 30 else 1
            for lon in range(-180, 181, gstep):
                if vb[0] <= lon <= vb[2]:
                    shapes.append(cv.Line(X(lon), 0, X(lon), h, _stroke(GRID, 0.6, 0.6)))
            for lat in range(-90, 91, gstep):
                if vb[1] <= lat <= vb[3]:
                    shapes.append(cv.Line(0, Y(lat), w, Y(lat), _stroke(GRID, 0.6, 0.6)))

        # political lines
        if self.show_borders:
            self._draw_polys("borders", geo, vb, _stroke(BORDER, 0.9 if z < 4 else 1.3, 0.85), False, 1.8, shapes)
        if self.show_states and z >= 1.6:
            self._draw_polys("states", geo, vb, _stroke(STATE, 0.6 if z < 4 else 0.9, 0.8), False, 1.5, shapes)

        # cities (greedy label placement so text does not pile up)
        if self.show_cities:
            max_rank = int(math.log2(z) * 2.0) + 0
            taken, count = set(), 0
            halo = ft.TextStyle(size=10, color=ft.Colors.with_opacity(0.85, "#ffffff"))
            ink = ft.TextStyle(size=10, color="#26323f")
            for name, lat, lon, rank, pop, cap, iso in mapdata.cities():
                if rank > max_rank:
                    break                                  # list is sorted by rank
                if not (vb[0] <= lon <= vb[2] and vb[1] <= lat <= vb[3]):
                    continue
                cx, cy = X(lon), Y(lat)
                shapes.append(cv.Circle(cx, cy, 2.6 if cap else 2.0, _fill("#26323f" if not cap else "#7d0f3e")))
                key = (int(cx // 80), int(cy // 14))
                if key in taken or count >= 70 or z < 2:
                    continue
                taken.add(key)
                count += 1
                shapes.append(cv.Text(cx + 5, cy - 6, name, halo))
                shapes.append(cv.Text(cx + 4, cy - 7, name, ink))

        # night side
        if self.dt:
            pts, dark = mapdata.night_outline(self.dt, max(0.25, 4.0 / z), (vb[0] - 3, vb[2] + 3))
            edge = h + 600 if dark == "S" else -600
            els = [cv.Path.MoveTo(X(pts[0][0]), Y(pts[0][1]))]
            els += [cv.Path.LineTo(X(lo), Y(la)) for lo, la in pts[1:]]
            els += [cv.Path.LineTo(X(pts[-1][0]), edge), cv.Path.LineTo(X(pts[0][0]), edge), cv.Path.Close()]
            shapes.append(cv.Path(els, paint=_fill("#0b1d3a", 0.38)))
            slat, slon = subsolar_point(self.dt)
            if vb[0] <= slon <= vb[2] and vb[1] <= slat <= vb[3]:
                shapes.append(cv.Circle(X(slon), Y(slat), 6, _fill("#ffd400")))
                shapes.append(cv.Circle(X(slon), Y(slat), 6, _stroke("#b38f00", 1.2)))

        r = max(4.0, self.w / 150)
        # path to the selected region
        if self.me and self.selected:
            for seg in mapdata.great_circle(self.me[0], self.me[1], self.selected[2], self.selected[3]):
                for (lo1, la1), (lo2, la2) in zip(seg, seg[1:]):
                    shapes.append(cv.Line(X(lo1), Y(la1), X(lo2), Y(la2), _stroke("#1b4f9c", 2.0)))
        # real stations: lines then squares
        if self.show_heard and self.me:
            shown = self.stations[:60]
            for st in shown:
                col = self._heard_color(st)
                sel = st["call"] == self.selected_call
                for seg in mapdata.great_circle(self.me[0], self.me[1], st["lat"], st["lon"], 16):
                    for (lo1, la1), (lo2, la2) in zip(seg, seg[1:]):
                        shapes.append(cv.Line(X(lo1), Y(la1), X(lo2), Y(la2),
                                              _stroke(col, 2.2 if sel else 1.0, 0.95 if sel else 0.40)))
        # region dots
        if self.show_dots:
            for t in TARGETS:
                lon, lat = t[3], t[2]
                if not (vb[0] <= lon <= vb[2] and vb[1] <= lat <= vb[3]):
                    continue
                state = self.states.get(t[0], "NO-GO")
                px, py = X(lon), Y(lat)
                shapes.append(cv.Circle(px, py, r, _fill(STATE_FILL[state])))
                shapes.append(cv.Circle(px, py, r, _stroke("#ffffff", 1.2)))
        if self.show_heard and self.me:
            q = max(4.0, self.w / 190)
            label_all = z >= 5
            for st in self.stations[:60]:
                if not (vb[0] <= st["lon"] <= vb[2] and vb[1] <= st["lat"] <= vb[3]):
                    continue
                px, py = X(st["lon"]), Y(st["lat"])
                col = self._heard_color(st)
                shapes.append(cv.Rect(px - q, py - q, 2 * q, 2 * q, paint=_fill(col)))
                shapes.append(cv.Rect(px - q, py - q, 2 * q, 2 * q, paint=_stroke("#ffffff", 1.3)))
                if st["call"] == self.selected_call:
                    shapes.append(cv.Rect(px - q - 3, py - q - 3, 2 * q + 6, 2 * q + 6, paint=_stroke("#10233f", 2.0)))
                if st["call"] == self.selected_call or label_all:
                    shapes.append(cv.Text(px + q + 5, py - 7, st["call"], ft.TextStyle(
                        size=12, weight=ft.FontWeight.W_700, color="#10233f")))
        if self.selected and vb[0] <= self.selected[3] <= vb[2] and vb[1] <= self.selected[2] <= vb[3]:
            t = self.selected
            px, py = X(t[3]), Y(t[2])
            shapes.append(cv.Circle(px, py, r + 3, _stroke("#1b4f9c", 2.2)))
            shapes.append(cv.Text(px + r + 5, py - 7, t[0], ft.TextStyle(size=12, weight=ft.FontWeight.W_600,
                                                                     color="#10233f")))
        if self.me:
            px, py = X(self.me[1]), Y(self.me[0])
            shapes.append(cv.Circle(px, py, r + 2, _fill("#d6246e")))
            shapes.append(cv.Circle(px, py, r + 2, _stroke("#ffffff", 2.0)))
            shapes.append(cv.Text(px + r + 5, py - 7, "You", ft.TextStyle(size=12, weight=ft.FontWeight.BOLD,
                                                                       color="#7d0f3e")))
        shapes += self._legend()
        shapes += self._scale_bar()
        self.canvas.shapes = shapes
        self.holder.transform = None
        self._drawn = (v.z, v.clon, v.clat)
        t_built = time.perf_counter()
        try:
            self.holder.update()
            self.zoom_label.update()
        except Exception:
            pass   # not on screen yet; shapes are kept and redrawn when it mounts
        if PROFILE:
            t_end = time.perf_counter()
            print(f"draw z={z:g} shapes={len(shapes)} build={(t_built - t_start) * 1000:.0f}ms "
                  f"update={(t_end - t_built) * 1000:.0f}ms", flush=True)
