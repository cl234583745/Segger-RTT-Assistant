try:
    import pyqtgraph as pg
    PYQTGRAPH_AVAILABLE = True
except ImportError:
    PYQTGRAPH_AVAILABLE = False

from .view_mode_strategy import ViewModeStrategy
from .time_base_manager import TimeBaseManager


class FreeExploreViewStrategy(ViewModeStrategy):

    def __init__(self, tb_manager: TimeBaseManager):
        self._tb_mgr = tb_manager

    def activate(self, plot_widget, channels) -> None:
        vb = plot_widget.getViewBox()
        vb.setMouseEnabled(x=True, y=False)
        plot_widget.showGrid(x=True, y=True, alpha=0.3)

    def deactivate(self, plot_widget) -> None:
        pass

    def apply_time_base(self, plot_widget, time_base_us: int,
                        center_x: float) -> None:
        x_range = time_base_us * 10 / 1_000_000.0
        vr = plot_widget.viewRange()
        x_center = (vr[0][0] + vr[0][1]) / 2.0
        plot_widget.setXRange(x_center - x_range / 2,
                              x_center + x_range / 2, padding=0)

    def update_view_range(self, plot_widget,
                          x_min: float, x_max: float,
                          y_min: float, y_max: float) -> None:
        time_base_us = self._tb_mgr.current_value()
        x_range_seconds = time_base_us * 10 / 1_000_000.0
        span = x_max - x_min
        if span <= 0:
            span = x_range_seconds
        x_view_start = max(x_min, x_max - x_range_seconds)
        plot_widget.setXRange(x_view_start, x_max, padding=0)

    def handle_wheel(self, plot_widget, delta: int,
                     current_tb_idx: int) -> int:
        if delta > 0:
            return max(current_tb_idx - 1, 0)
        elif delta < 0:
            return min(current_tb_idx + 1, len(TimeBaseManager.STEPS_US) - 1)
        return current_tb_idx

    def set_drag_enabled(self, plot_widget,
                         x_enabled: bool, y_enabled: bool) -> None:
        vb = plot_widget.getViewBox()
        vb.setMouseEnabled(x=True, y=False)
