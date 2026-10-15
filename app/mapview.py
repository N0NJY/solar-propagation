"""World map drawn on a Flet canvas: coastlines, night shading, targets coloured by band state."""
import flet as ft
import flet.canvas as cv

from hfprop import mapdata
from hfprop.solar import subsolar_point
from hfprop.targets import TARGETS

OCEAN = "#cfe3ef"
LAND = "#a9c49a"
GRID = "#9fb9c8"
HEARD_ME, I_HEARD, BOTH = "#1b6fd8", "#8e44c8", "#0a9e96"
STATE_FILL = {"GO": "#2e9e4f", "MARGINAL": "#f0a000", "NO-GO": "#b8bcc2"}


def _fill(color, opacity=1.0):
    return ft.Paint(color=ft.Colors.with_opacity(opacity, color), style=ft.PaintingStyle.FILL)


def _stroke(color, width=1.0, opacity=1.0):
    return ft.Paint(color=ft.Colors.with_opacity(opacity, color), style=ft.PaintingStyle.STROKE,
                    stroke_width=width)


class MapView:
    def __init__(self, on_pick, on_pick_station=None):
        self.on_pick = on_pick
        self.on_pick_station = on_pick_station
        self.stations = []        # real PSK Reporter stations (heard layer)
        self.selected_call = None
        self.show_heard = False
        self.w = self.h = 0
        self.me = None            # (lat, lon, label)
        self.dt = None
        self.states = {}          # target name -> GO / MARGINAL
        self.selected = None      # target tuple
        self.heat = []            # reach_grid cells
        self.heat_step = 6
        self.show_dots = True
        self.show_heat = True
        self._land_key = None
        self._land_shapes = []
        self.canvas = cv.Canvas(shapes=[], on_resize=self._resize, expand=True)
        self.control = ft.Container(
            width=1000, height=500, bgcolor=OCEAN, border_radius=10, clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            content=ft.GestureDetector(content=self.canvas, on_tap_down=self._tap))

    # --- projection (equirectangular; container is locked to 2:1) ---
    def _x(self, lon):
        return (lon + 180.0) / 360.0 * self.w

    def _y(self, lat):
        return (90.0 - lat) / 180.0 * self.h

    def _resize(self, e):
        if not (0 < e.width < 1e5 and 0 < e.height < 1e5):   # layout pass can report inf/0
            return
        self.w, self.h = e.width, e.height
        self.draw()

    def set_data(self, me, dt, states, selected, heat=None, stations=None, selected_call=None):
        self.me, self.dt, self.states, self.selected = me, dt, states, selected
        self.heat = heat or []
        self.stations, self.selected_call = stations or [], selected_call
        self.draw()

    # --- interaction ---
    def _tap(self, e):
        if not self.w:
            return
        x, y = e.local_position.x, e.local_position.y
        if self.show_heard and self.on_pick_station:
            near, nd = None, max(16.0, self.w * 0.02)
            for st in self.stations:
                d = ((self._x(st["lon"]) - x) ** 2 + (self._y(st["lat"]) - y) ** 2) ** 0.5
                if d < nd:
                    near, nd = st, d
            if near:
                self.on_pick_station(near["call"])
                return
        if not self.show_dots:
            return
        best, bd = None, max(24.0, self.w * 0.035)
        for t in TARGETS:
            d = ((self._x(t[3]) - x) ** 2 + (self._y(t[2]) - y) ** 2) ** 0.5
            if d < bd:
                best, bd = t, d
        if best:
            self.on_pick(best)

    # --- drawing ---
    def _land(self):
        key = (round(self.w), round(self.h))
        if key != self._land_key:
            shapes = []
            for ring in mapdata.land_rings():
                els = [cv.Path.MoveTo(self._x(ring[0]), self._y(ring[1]))]
                els += [cv.Path.LineTo(self._x(ring[i]), self._y(ring[i + 1]))
                        for i in range(2, len(ring), 2)]
                els.append(cv.Path.Close())
                shapes.append(cv.Path(els, paint=_fill(LAND)))
            self._land_key, self._land_shapes = key, shapes
        return self._land_shapes

    @staticmethod
    def _heard_color(st):
        return BOTH if st["heard_me"] and st["i_heard"] else HEARD_ME if st["heard_me"] else I_HEARD

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

    def draw(self):
        if not self.w or not self.h:
            return
        shapes = list(self._land())
        if self.show_heat:
            cw, ch = self.heat_step / 360.0 * self.w, self.heat_step / 180.0 * self.h
            for la, lo, state, margin in self.heat:
                if state == "GO":
                    paint = _fill("#1f9d4a", 0.30 + 0.35 * min(1.0, max(0.0, margin) / 20.0))
                else:
                    paint = _fill("#f0a000", 0.42)
                paint.anti_alias = False   # exact cell edges: no double-blended seams
                shapes.append(cv.Rect(self._x(lo) - cw / 2, self._y(la) - ch / 2, cw, ch, paint=paint))
        for lon in range(-150, 181, 30):
            shapes.append(cv.Line(self._x(lon), 0, self._x(lon), self.h, _stroke(GRID, 0.6, 0.6)))
        for lat in (-60, -30, 0, 30, 60):
            shapes.append(cv.Line(0, self._y(lat), self.w, self._y(lat), _stroke(GRID, 0.6, 0.6)))
        if self.dt:
            pts, dark = mapdata.night_outline(self.dt)
            edge = self.h if dark == "S" else 0
            els = [cv.Path.MoveTo(self._x(pts[0][0]), self._y(pts[0][1]))]
            els += [cv.Path.LineTo(self._x(lo), self._y(la)) for lo, la in pts[1:]]
            els += [cv.Path.LineTo(self.w, edge), cv.Path.LineTo(0, edge), cv.Path.Close()]
            shapes.append(cv.Path(els, paint=_fill("#0b1d3a", 0.38)))
            slat, slon = subsolar_point(self.dt)
            shapes.append(cv.Circle(self._x(slon), self._y(slat), 6, _fill("#ffd400")))
            shapes.append(cv.Circle(self._x(slon), self._y(slat), 6, _stroke("#b38f00", 1.2)))
        r = max(4.0, self.w / 150)
        if self.me and self.selected:
            for seg in mapdata.great_circle(self.me[0], self.me[1], self.selected[2], self.selected[3]):
                for (lo1, la1), (lo2, la2) in zip(seg, seg[1:]):
                    shapes.append(cv.Line(self._x(lo1), self._y(la1), self._x(lo2), self._y(la2),
                                          _stroke("#1b4f9c", 2.0)))
        for t in (TARGETS if self.show_dots else []):
            state = self.states.get(t[0], "NO-GO")
            x, y = self._x(t[3]), self._y(t[2])
            shapes.append(cv.Circle(x, y, r, _fill(STATE_FILL[state])))
            shapes.append(cv.Circle(x, y, r, _stroke("#ffffff", 1.2)))
        if self.show_heard and self.me:
            shown = self.stations[:60]
            for st in shown:
                col = self._heard_color(st)
                sel = st["call"] == self.selected_call
                for seg in mapdata.great_circle(self.me[0], self.me[1], st["lat"], st["lon"], 16):
                    for (lo1, la1), (lo2, la2) in zip(seg, seg[1:]):
                        shapes.append(cv.Line(self._x(lo1), self._y(la1), self._x(lo2), self._y(la2),
                                              _stroke(col, 2.2 if sel else 1.0, 0.95 if sel else 0.40)))
            q = max(4.0, self.w / 190)
            for st in shown:
                x, y = self._x(st["lon"]), self._y(st["lat"])
                col = self._heard_color(st)
                shapes.append(cv.Rect(x - q, y - q, 2 * q, 2 * q, paint=_fill(col)))
                shapes.append(cv.Rect(x - q, y - q, 2 * q, 2 * q, paint=_stroke("#ffffff", 1.3)))
                if st["call"] == self.selected_call:
                    shapes.append(cv.Rect(x - q - 3, y - q - 3, 2 * q + 6, 2 * q + 6, paint=_stroke("#10233f", 2.0)))
                    shapes.append(cv.Text(x + q + 6, y - 7, st["call"], ft.TextStyle(size=12, weight=ft.FontWeight.W_700, color="#10233f")))
        if self.selected:
            t = self.selected
            x, y = self._x(t[3]), self._y(t[2])
            shapes.append(cv.Circle(x, y, r + 3, _stroke("#1b4f9c", 2.2)))
            shapes.append(cv.Text(x + r + 5, y - 7, t[0], ft.TextStyle(size=12, weight=ft.FontWeight.W_600,
                                                                     color="#10233f")))
        if self.me:
            x, y = self._x(self.me[1]), self._y(self.me[0])
            shapes.append(cv.Circle(x, y, r + 2, _fill("#d6246e")))
            shapes.append(cv.Circle(x, y, r + 2, _stroke("#ffffff", 2.0)))
            shapes.append(cv.Text(x + r + 5, y - 7, "You", ft.TextStyle(size=12, weight=ft.FontWeight.BOLD,
                                                                       color="#7d0f3e")))
        shapes += self._legend()
        self.canvas.shapes = shapes
        try:
            self.canvas.update()
        except Exception:
            pass   # not on screen yet; shapes are kept and redrawn when it mounts
