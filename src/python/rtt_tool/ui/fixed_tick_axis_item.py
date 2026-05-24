try:
    import pyqtgraph as pg
    PYQTGRAPH_AVAILABLE = True
except ImportError:
    PYQTGRAPH_AVAILABLE = False


class FixedTickAxisItem(pg.AxisItem):

    def __init__(self, orientation='bottom', **kwargs):
        super().__init__(orientation, **kwargs)
        self._time_base_us: int = 2000

    def set_time_base(self, time_base_us: int) -> None:
        self._time_base_us = time_base_us
        self.update()

    def tickValues(self, min_val, max_val, size):
        n_ticks = 11
        spacing = (max_val - min_val) / (n_ticks - 1)
        if spacing <= 0:
            return []
        values = [min_val + i * spacing for i in range(n_ticks)]
        return [(spacing, values)]

    def tickStrings(self, values, scale, spacing):
        tb_us = self._time_base_us
        strings = []
        for i, v in enumerate(values):
            n_div = i
            total_us = n_div * tb_us
            if tb_us < 1000:
                strings.append(f"{total_us:.0f}µs")
            elif tb_us < 1_000_000:
                strings.append(f"{total_us / 1000:.3g}ms")
            else:
                strings.append(f"{total_us / 1_000_000:.3g}s")
        return strings
