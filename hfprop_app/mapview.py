"""World map on a Flet canvas: zoom / pan / pinch, coastlines, lakes, borders, states, cities,
Maidenhead grid squares, night shading, heat map, region dots and real (PSK) stations."""
import math
import os
import threading
import time

import flet as ft
import flet.canvas as cv

from hfprop import mapdata, units as U
from hfprop.geo import latlon_to_grid
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
OFFSCREEN = 60                # pixels beyond the view edge before geometry is trimmed
PREVIEW_INTERVAL = 0.03       # seconds between instant (transform-only) previews


def _fill(color, opacity=1.0):
    return ft.Paint(color=ft.Colors.with_opacity(opacity, color), style=ft.PaintingStyle.FILL)


def _stroke(color, width=1.0, opacity=1.0):
    return ft.Paint(color=ft.Colors.with_opacity(opacity, color), style=ft.PaintingStyle.STROKE,
                    stroke_width=width)


def _rect_els(x, y, w, h):
    x, y, w, h = round(x, 1), round(y, 1), round(w, 1), round(h, 1)
    return [cv.Path.MoveTo(x, y), cv.Path.LineTo(x + w, y), cv.Path.LineTo(x + w, y + h),
            cv.Path.LineTo(x, y + h), cv.Path.Close()]


def _dots(points, diameter, color, opacity=1.0):
    """Many round dots as ONE shape (the display cost is per shape, not per point)."""
    return cv.Points(points=[ft.Offset(round(x, 1), round(y, 1)) for x, y in points],
                     point_mode=cv.PointMode.POINTS,
                     paint=ft.Paint(color=ft.Colors.with_opacity(opacity, color), style=ft.PaintingStyle.STROKE,
                                    stroke_width=diameter, stroke_cap=ft.StrokeCap.ROUND))


def heat_step(z):
    """Heat-map cell size (degrees) for a zoom level: finer as you zoom in."""
    return 6.0 if z < 2.5 else 3.0 if z < 5 else 1.5 if z < 10 else 0.75 if z < 20 else 0.5


class MapView:
    def __init__(self, on_pick, on_pick_station=None):
        self.on_pick = on_pick
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
        self._draw_lock = threading.Lock()
        self._heat_cache = None   # (heat_fn, step, bounds, cells)
        self._redraw_wanted = False
        self._settle_timer = None
        self.canvas = cv.Canvas(shapes=[], on_resize=self._resize, expand=True)
        self.holder = ft.Container(content=self.canvas, expand=True)   # moved / scaled for instant previews
        self.zoom_label = ft.Text("1x", size=11, weight=ft.FontWeight.W_600, color="#10233f")
        self.control = ft.Container(
            width=1000, height=500, bgcolor=OCEAN, border_radius=10, clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            content=ft.Stack(fit=ft.StackFit.EXPAND, controls=[
                ft.GestureDetector(
                    expand=True, content=self.holder, on_tap_up=self._tap, on_scroll=self._scroll,
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
        """Project a flat [lon, lat, ...] list to canvas path elements. Points are dropped when they
        sit closer than min_px to the previous kept one, and when they and both neighbours lie
        beyond the same edge of the view (invisible, and the chord between them stays outside too)."""
        x0, y1, sx, sy = geo
        xs = [(v - x0) * sx for v in flat[0::2]]
        ys = [(y1 - v) * sy for v in flat[1::2]]
        lo_x, hi_x, lo_y, hi_y = -OFFSCREEN, self.w + OFFSCREEN, -OFFSCREEN, self.h + OFFSCREEN
        oc = [(x < lo_x) | ((x > hi_x) << 1) | ((y < lo_y) << 2) | ((y > hi_y) << 3) for x, y in zip(xs, ys)]
        els, lx, ly = [], None, None
        last = len(xs) - 1
        for i, (x, y) in enumerate(zip(xs, ys)):
            if 0 < i < last and oc[i - 1] & oc[i] & oc[i + 1]:
                continue
            if lx is None:
                els.append(cv.Path.MoveTo(round(x, 1), round(y, 1)))
                lx, ly = x, y
            elif abs(x - lx) + abs(y - ly) >= min_px or i == last:
                els.append(cv.Path.LineTo(round(x, 1), round(y, 1)))
                lx, ly = x, y
        if closed:
            els.append(cv.Path.Close())
        return els

    def _heat_cells(self, vb, step):
        """Heat-map cells for the view. The (slow) reach grid is computed for a region a bit larger than
        the view and reused while you pan or zoom within it."""
        want = (max(-180.0, vb[0] - step), max(-90.0, vb[1] - step), min(180.0, vb[2] + step), min(90.0, vb[3] + step))
        c = self._heat_cache
        if not (c and c[0] is self.heat_fn and c[1] == step and c[2][0] <= want[0] and c[2][1] <= want[1]
                and c[2][2] >= want[2] and c[2][3] >= want[3]):
            mx, my = (want[2] - want[0]) * 0.25, (want[3] - want[1]) * 0.25
            big = (max(-180.0, want[0] - mx), max(-90.0, want[1] - my), min(180.0, want[2] + mx), min(90.0, want[3] + my))
            c = self._heat_cache = (self.heat_fn, step, big, self.heat_fn(big, step))
        return [x for x in c[3] if want[0] - step <= x[1] <= want[2] + step and want[1] - step <= x[0] <= want[3] + step]

    def _visible(self, bbox, vb):
        return not (bbox[2] < vb[0] or bbox[0] > vb[2] or bbox[3] < vb[1] or bbox[1] > vb[3])

    def _draw_polys(self, name, geo, vb, paint, closed, min_px, shapes):
        """All visible polygons / lines of a layer go into a single Path shape."""
        all_els = []
        for bb, flat in mapdata.shapes(name):
            if self._visible(bb, vb):
                if (bb[2] - bb[0]) * geo[2] < 1.2 and (bb[3] - bb[1]) * geo[3] < 1.2:
                    continue                      # smaller than a pixel
                els = self._path(flat, geo, closed, min_px)
                if len(els) > 2:
                    all_els += els
        if all_els:
            shapes.append(cv.Path(all_els, paint=paint))

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
        """Redraw; if a draw is already running (they can take 0.3 s+), just ask it to go again."""
        if not self._draw_lock.acquire(blocking=False):
            self._redraw_wanted = True
            return
        try:
            self._redraw_wanted = True
            while self._redraw_wanted:
                self._redraw_wanted = False
                self._draw_once()
        finally:
            self._draw_lock.release()

    def _draw_once(self):
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

        mp = 1.8 if z >= 2 else 2.4                       # point-thinning distance in pixels
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
            cells = self._heat_cells(vb, step)
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
            by_key = {}
            for la, lo0, lo1, key in runs:
                by_key.setdefault(key, []).extend(
                    _rect_els(X(lo0) - cw / 2, Y(la) - ch / 2, (lo1 - lo0) * sx + cw, ch))
            for (state, shade), els in by_key.items():     # one shape per colour, not per cell
                paint = _fill("#1f9d4a", 0.30 + 0.35 * shade) if state == "GO" else _fill("#f0a000", 0.42)
                paint.anti_alias = False                  # exact cell edges: no double-blended seams
                shapes.append(cv.Path(els, paint=paint))

        # graticule / Maidenhead grid squares
        ppd = sx                                          # pixels per degree of longitude
        if self.show_grid:
            level = 2 if 2 * ppd >= 30 else 1
            cells = mapdata.maidenhead_cells(vb, level)
            fields = []
            for lab, lo0, la0, lo1, la1 in (mapdata.maidenhead_cells(vb, 1) if level == 2 else []):
                fields += _rect_els(X(lo0), Y(la1), (lo1 - lo0) * sx, (la1 - la0) * sy)
            if fields:
                shapes.append(cv.Path(fields, paint=_stroke("#27507a", 1.3, 0.7)))
            boxes = []                                    # grid outlines: one shape, labels separate
            label_cells = level == 1 or (2.0 * ppd >= 40 and len(cells) <= 700)
            for lab, lo0, la0, lo1, la1 in cells:
                rx, ry, rw, rh = X(lo0), Y(la1), (lo1 - lo0) * sx, (la1 - la0) * sy
                boxes += _rect_els(rx, ry, rw, rh)
                if level == 1:
                    if rw > 40:
                        shapes.append(cv.Text(rx + rw / 2 - 9, ry + rh / 2 - 9, lab, ft.TextStyle(
                            size=18, weight=ft.FontWeight.W_700, color=ft.Colors.with_opacity(0.45, "#27507a"))))
                else:
                    if label_cells:
                        shapes.append(cv.Text(rx + 3, ry + 2, lab, ft.TextStyle(
                            size=11, weight=ft.FontWeight.W_600, color=ft.Colors.with_opacity(0.8, "#27507a"))))
            if boxes:
                shapes.append(cv.Path(boxes, paint=_stroke("#27507a", 1.0, 0.55) if level == 1
                                      else _stroke("#3b5b7a", 0.6, 0.5)))
        else:
            gstep = 30 if z < 4 else 10 if z < 12 else 5 if z < 30 else 1
            lines = []
            for lon in range(-180, 181, gstep):
                if vb[0] <= lon <= vb[2]:
                    lines += [cv.Path.MoveTo(round(X(lon), 1), 0), cv.Path.LineTo(round(X(lon), 1), h)]
            for lat in range(-90, 91, gstep):
                if vb[1] <= lat <= vb[3]:
                    lines += [cv.Path.MoveTo(0, round(Y(lat), 1)), cv.Path.LineTo(w, round(Y(lat), 1))]
            if lines:
                shapes.append(cv.Path(lines, paint=_stroke(GRID, 0.6, 0.6)))

        # political lines
        if self.show_borders:
            self._draw_polys("borders", geo, vb, _stroke(BORDER, 0.9 if z < 4 else 1.3, 0.85), False, 1.8, shapes)
        if self.show_states and z >= 1.6:
            self._draw_polys("states", geo, vb, _stroke(STATE, 0.6 if z < 4 else 0.9, 0.8), False, 1.5, shapes)

        # cities (greedy label placement so text does not pile up)
        if self.show_cities:
            max_rank = int(math.log2(z) * 2.0) + 0
            taken, count = set(), 0
            dots_plain, dots_cap = [], []
            ink = ft.TextStyle(size=10, color="#26323f")
            for name, lat, lon, rank, pop, cap, iso in mapdata.cities():
                if rank > max_rank:
                    break                                  # list is sorted by rank
                if not (vb[0] <= lon <= vb[2] and vb[1] <= lat <= vb[3]):
                    continue
                cx, cy = X(lon), Y(lat)
                (dots_cap if cap else dots_plain).append((cx, cy))
                key = (int(cx // 80), int(cy // 14))
                if key in taken or count >= 70 or z < 2:
                    continue
                taken.add(key)
                count += 1
                shapes.append(cv.Text(cx + 4, cy - 7, name, ink))
            if dots_plain:
                shapes.append(_dots(dots_plain, 4.0, "#26323f"))
            if dots_cap:
                shapes.append(_dots(dots_cap, 5.2, "#7d0f3e"))

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
            els = []
            for seg in mapdata.great_circle(self.me[0], self.me[1], self.selected[2], self.selected[3]):
                els.append(cv.Path.MoveTo(X(seg[0][0]), Y(seg[0][1])))
                els += [cv.Path.LineTo(X(lo), Y(la)) for lo, la in seg[1:]]
            if els:
                shapes.append(cv.Path(els, paint=_stroke("#1b4f9c", 2.0)))
        # real stations: lines then squares
        if self.show_heard and self.me:
            by_look = {}                                  # (colour, selected) -> path elements: one shape per look
            for st in self.stations[:60]:
                els = by_look.setdefault((self._heard_color(st), st["call"] == self.selected_call), [])
                for seg in mapdata.great_circle(self.me[0], self.me[1], st["lat"], st["lon"], 16):
                    els.append(cv.Path.MoveTo(X(seg[0][0]), Y(seg[0][1])))
                    els += [cv.Path.LineTo(X(lo), Y(la)) for lo, la in seg[1:]]
            for (col, sel), els in sorted(by_look.items(), key=lambda kv: kv[0][1]):
                shapes.append(cv.Path(els, paint=_stroke(col, 2.2 if sel else 1.0, 0.95 if sel else 0.40)))
        # region dots
        if self.show_dots:
            by_state = {}
            for t in TARGETS:
                lon, lat = t[3], t[2]
                if not (vb[0] <= lon <= vb[2] and vb[1] <= lat <= vb[3]):
                    continue
                by_state.setdefault(self.states.get(t[0], "NO-GO"), []).append((X(lon), Y(lat)))
            allpts = [p for pts in by_state.values() for p in pts]
            if allpts:                                    # white ring = a bigger white dot under the coloured one
                shapes.append(_dots(allpts, 2 * r + 2.4, "#ffffff"))
            for state, pts in by_state.items():
                shapes.append(_dots(pts, 2 * r, STATE_FILL[state]))
        if self.show_heard and self.me:
            q = max(4.0, self.w / 190)
            label_all = z >= 5
            squares, outline, ring, labels = {}, [], [], []
            for st in self.stations[:60]:
                if not (vb[0] <= st["lon"] <= vb[2] and vb[1] <= st["lat"] <= vb[3]):
                    continue
                px, py = X(st["lon"]), Y(st["lat"])
                box = _rect_els(px - q, py - q, 2 * q, 2 * q)
                squares.setdefault(self._heard_color(st), []).extend(box)
                outline += box
                if st["call"] == self.selected_call:
                    ring += _rect_els(px - q - 3, py - q - 3, 2 * q + 6, 2 * q + 6)
                if st["call"] == self.selected_call or label_all:
                    labels.append(cv.Text(px + q + 5, py - 7, st["call"], ft.TextStyle(
                        size=12, weight=ft.FontWeight.W_700, color="#10233f")))
            for col, els in squares.items():              # one shape per colour, not per station
                shapes.append(cv.Path(els, paint=_fill(col)))
            if outline:
                shapes.append(cv.Path(outline, paint=_stroke("#ffffff", 1.3)))
            if ring:
                shapes.append(cv.Path(ring, paint=_stroke("#10233f", 2.0)))
            shapes += labels
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
            you = "You" if z < 6 else f"You  {latlon_to_grid(self.me[0], self.me[1], 6 if z < 16 else 10)}"
            shapes.append(cv.Text(px + r + 5, py - 7, you, ft.TextStyle(size=12, weight=ft.FontWeight.BOLD,
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
