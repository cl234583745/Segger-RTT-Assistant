import math
from PyQt5.QtCore import Qt, QRectF, QPointF

try:
    import pyqtgraph as pg
    PYQTGRAPH_AVAILABLE = True
except ImportError:
    PYQTGRAPH_AVAILABLE = False


class OscilloscopeGridItem(pg.GraphicsObject):

    def __init__(self, h_divs: int = 10, sub_divs: int = 5):
        super().__init__()
        self._h_divs = h_divs
        self._sub_divs = sub_divs
        self._y_tick_spacing = None
        self._major_pen = pg.mkPen('#555555', width=2)
        self._minor_pen = pg.mkPen('#222222', width=1, style=Qt.DotLine)
        self._center_pen = pg.mkPen('#777777', width=2, style=Qt.DashLine)

    def boundingRect(self):
        vb = self.getViewBox()
        if vb is None:
            return QRectF()
        vr = vb.viewRange()
        return QRectF(vr[0][0], vr[1][0], vr[0][1] - vr[0][0], vr[1][1] - vr[1][0])

    def paint(self, painter, option, widget):
        vb = self.getViewBox()
        if vb is None:
            return

        vr = vb.viewRange()
        x_min, x_max = vr[0]
        y_min, y_max = vr[1]
        x_range = x_max - x_min
        y_range = y_max - y_min
        if x_range <= 0 or y_range <= 0:
            return

        h_step = x_range / self._h_divs

        painter.setPen(self._minor_pen)
        h_sub_step = h_step / self._sub_divs
        for i in range(self._h_divs * self._sub_divs + 1):
            if i % self._sub_divs == 0:
                continue
            x = x_min + i * h_sub_step
            painter.drawLine(QPointF(x, y_min), QPointF(x, y_max))

        painter.setPen(self._major_pen)
        for i in range(self._h_divs + 1):
            x = x_min + i * h_step
            painter.drawLine(QPointF(x, y_min), QPointF(x, y_max))

        cx = (x_min + x_max) / 2
        painter.setPen(self._center_pen)
        painter.drawLine(QPointF(cx, y_min), QPointF(cx, y_max))

        self._paint_y_grid(painter, x_min, x_max, y_min, y_max)

    def _paint_y_grid(self, painter, x_min, x_max, y_min, y_max):
        y_range = y_max - y_min
        if y_range <= 0:
            return

        tick_spacing = self._y_tick_spacing if self._y_tick_spacing and self._y_tick_spacing > 0 else self._nice_num(y_range / 8)
        sub_spacing = tick_spacing / self._sub_divs

        painter.setPen(self._minor_pen)
        y = math.ceil(y_min / sub_spacing) * sub_spacing
        while y <= y_max + sub_spacing * 0.001:
            is_major = abs(y % tick_spacing) < sub_spacing * 0.01 or abs(y % tick_spacing - tick_spacing) < sub_spacing * 0.01
            if not is_major:
                painter.drawLine(QPointF(x_min, y), QPointF(x_max, y))
            y += sub_spacing

        painter.setPen(self._major_pen)
        y = math.ceil(y_min / tick_spacing) * tick_spacing
        while y <= y_max + tick_spacing * 0.001:
            painter.drawLine(QPointF(x_min, y), QPointF(x_max, y))
            y += tick_spacing

        painter.setPen(self._center_pen)
        cy = (y_min + y_max) / 2
        painter.drawLine(QPointF(x_min, cy), QPointF(x_max, cy))

    def set_y_tick_spacing(self, spacing: float):
        self._y_tick_spacing = spacing if spacing and spacing > 0 else None
        self.update()

    @staticmethod
    def _nice_num(value):
        if value <= 0:
            return value
        exp = math.floor(math.log10(value))
        frac = value / (10 ** exp)
        if frac < 1.5:
            nice = 1
        elif frac < 3:
            nice = 2
        elif frac < 7:
            nice = 5
        else:
            nice = 10
        return nice * (10 ** exp)
