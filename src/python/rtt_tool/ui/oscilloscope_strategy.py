try:
    import pyqtgraph as pg
    PYQTGRAPH_AVAILABLE = True
except ImportError:
    PYQTGRAPH_AVAILABLE = False

from .view_mode_strategy import ViewModeStrategy
from .time_base_manager import TimeBaseManager
from .oscilloscope_grid_item import OscilloscopeGridItem
from .fixed_tick_axis_item import FixedTickAxisItem


class OscilloscopeViewStrategy(ViewModeStrategy):

    HORIZONTAL_DIVS = 10

    def __init__(self, tb_manager: TimeBaseManager):
        self._tb_mgr = tb_manager
        self._grid_item = None
        self._x_axis_item = None
        self._original_axis = None

    def activate(self, plot_widget, channels) -> None:
        vb = plot_widget.getViewBox()
        vb.setMouseEnabled(x=False, y=True)
        vb.enableAutoRange(x=False, y=False)

        self._original_axis = plot_widget.getAxis('bottom')
        self._x_axis_item = FixedTickAxisItem(orientation='bottom')
        plot_widget.setAxisItems({'bottom': self._x_axis_item})

        plot_widget.showGrid(x=False, y=False, alpha=0)

        self._grid_item = OscilloscopeGridItem(
            h_divs=self.HORIZONTAL_DIVS)
        vb.addItem(self._grid_item, ignoreBounds=True)

        self._apply_initial_range(plot_widget)

    def _apply_initial_range(self, plot_widget) -> None:
        time_base_us = self._tb_mgr.current_value()
        x_range_sec = time_base_us * self.HORIZONTAL_DIVS / 1_000_000.0
        vr = plot_widget.viewRange()
        x_center = (vr[0][0] + vr[0][1]) / 2.0
        x_min = x_center - x_range_sec / 2
        x_max = x_center + x_range_sec / 2
        plot_widget.setXRange(x_min, x_max, padding=0)
        if self._x_axis_item:
            self._x_axis_item.set_time_base(time_base_us)

    def deactivate(self, plot_widget) -> None:
        vb = plot_widget.getViewBox()
        if self._grid_item:
            vb.removeItem(self._grid_item)
            self._grid_item = None

        if self._original_axis:
            plot_widget.setAxisItems({'bottom': self._original_axis})
            self._original_axis = None
        self._x_axis_item = None

        plot_widget.showGrid(x=True, y=True, alpha=0.3)
        vb.setMouseEnabled(x=True, y=False)
        vb.enableAutoRange(x=True, y=True)

    def apply_time_base(self, plot_widget, time_base_us: int,
                        center_x: float) -> None:
        x_range_sec = time_base_us * self.HORIZONTAL_DIVS / 1_000_000.0
        x_min = center_x - x_range_sec / 2
        x_max = center_x + x_range_sec / 2
        plot_widget.setXRange(x_min, x_max, padding=0)
        if self._x_axis_item:
            self._x_axis_item.set_time_base(time_base_us)

    def update_view_range(self, plot_widget,
                          x_min: float, x_max: float,
                          y_min: float, y_max: float) -> None:
        time_base_us = self._tb_mgr.current_value()
        x_range_sec = time_base_us * self.HORIZONTAL_DIVS / 1_000_000.0
        new_x_min = x_max - x_range_sec
        plot_widget.setXRange(new_x_min, x_max, padding=0)
        if self._x_axis_item:
            self._x_axis_item.set_time_base(time_base_us)

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
        vb.setMouseEnabled(x=x_enabled, y=True)
