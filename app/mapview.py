"""World map drawn on a Flet canvas: coastlines, night shading, targets coloured by band state."""
import flet as ft
import flet.canvas as cv

from hfprop import mapdata
from hfprop.solar import subsolar_point
from hfprop.targets import TARGETS

OCEAN = "#cfe3ef"
LAND = "#a9c49a"
GRID = "#9fb9c8"
STATE_FILL = {"GO": "#2e9e4f", "MARGINAL": "#f0a000", "NO-GO": "#b8bcc2"}


def _fill(color, opacity=1.0):
    return ft.Paint(color=ft.Colors.with_opacity(opacity, color), style=ft.PaintingStyle.FILL)


def _stroke(color, width=1.0, opacity=1.0):
    return ft.Paint(color=ft.Colors.with_opacity(opacity, color), style=ft.PaintingStyle.STROKE,
                    stroke_width=width)


class MapView:
    def __init__(self, on_pick):
        self.on_pick = on_pick
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
            aspect_ratio=2, bgcolor=OCEAN, border_radius=10, clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            content=ft.GestureDetector(content=self.canvas, on_tap_down=self._tap))

    # --- projection (equirectangular; container is locked to 2:1) ---
    def _x(self, lon):
        return (lon + 180.0) / 360.0 * self.w

    def _y(self, lat):
        return (90.0 - lat) / 180.0 * self.h

    def _resize(self, e):
        self.w, self.h = e.width, e.height
        self.draw()

    def set_data(self, me, dt, states, selected, heat=None):
        self.me, self.dt, self.states, self.selected = me, dt, states, selected
        self.heat = heat or []
        self.draw()

    # --- interaction ---
    def _tap(self, e):
        if not self.w or not self.show_dots:
            return
        x, y = e.local_position.x, e.local_position.y
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
        self.canvas.shapes = shapes
        try:
            self.canvas.update()
        except Exception:
            pass   # not on screen yet; shapes are kept and redrawn when it mounts
