"""24-hour band outlook grid: bands down the side, hours across, coloured by GO/MARGINAL/NO-GO."""
import flet as ft
import flet.canvas as cv

COLORS = {"GO": ("#2e9e4f", 1.0), "MARGINAL": ("#f0a000", 1.0), "NO-GO": ("#98a2b3", 0.22)}


def _fill(c, o=1.0):
    return ft.Paint(color=ft.Colors.with_opacity(o, c), style=ft.PaintingStyle.FILL)


def _stroke(c, w=1.0):
    return ft.Paint(color=c, style=ft.PaintingStyle.STROKE, stroke_width=w)


def _txt(x, y, s, size=10, color="#667085", bold=False):
    return cv.Text(x, y, s, ft.TextStyle(size=size, color=color,
                                         weight=ft.FontWeight.W_700 if bold else ft.FontWeight.W_400))


def draw_strip(data, w, h):
    """data = {"grid": {band: [states]}, "start_hour": UTC hour of column 0, "lon": user longitude}."""
    grid, start, lon = data["grid"], data["start_hour"], data["lon"]
    bands = list(grid)
    n = len(next(iter(grid.values())))
    L, T, B = 40, 4, 34
    cw, ch = (w - L - 4) / n, (h - T - B) / len(bands)
    shapes = []
    for r, b in enumerate(bands):
        y = T + r * ch
        shapes.append(_txt(4, y + ch / 2 - 7, b, 11, "#475467", True))
        for c, state in enumerate(grid[b]):
            col, op = COLORS[state]
            shapes.append(cv.Rect(L + c * cw + 0.5, y + 0.5, cw - 1, ch - 1, border_radius=2, paint=_fill(col, op)))
    off = round(lon / 15.0)                       # approximate local solar time offset
    for c in range(0, n, 3):
        x = L + c * cw
        utc = (start + c) % 24
        shapes.append(_txt(x, h - B + 3, f"{utc:02d}", 10))
        shapes.append(_txt(x, h - B + 16, f"{(utc + off) % 24:02d}", 10, "#1b4f9c"))
    shapes.append(_txt(4, h - B + 3, "UTC", 10))
    shapes.append(_txt(4, h - B + 16, "local", 10, "#1b4f9c"))
    shapes.append(cv.Rect(L, T, cw, h - T - B, paint=_stroke("#10233f", 1.6)))   # current hour
    return shapes
