from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QToolBar, QComboBox,
                              QLabel, QHBoxLayout, QAction)
from PyQt5.QtCore import Qt, pyqtSignal

try:
    import pyqtgraph as pg
    PYQTGRAPH_AVAILABLE = True
except ImportError:
    PYQTGRAPH_AVAILABLE = False


class WaveformWidget(QWidget):
    """基于 PyQtGraph 的实时波形显示组件。"""

    CHANNEL_COLORS = ['#00FF00', '#FF6600', '#00AAFF', '#FF00FF',
                       '#FFFF00', '#00FFFF', '#FF8888', '#88FF88']
    TIME_BASE_OPTIONS = [1, 5, 10, 50, 100, 500, 1000]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._channels = {}
        self._time_base_ms = 100
        self._trigger_mode = 'auto'
        self._vertical_scale = 'auto'
        self._color_theme = 'dark'

        if PYQTGRAPH_AVAILABLE:
            self._init_ui()
        else:
            layout = QVBoxLayout(self)
            label = QLabel("pyqtgraph 未安装，示波器模式不可用。\n请执行: pip install pyqtgraph")
            label.setAlignment(Qt.AlignCenter)
            layout.addWidget(label)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        toolbar = QToolBar()
        toolbar.setMovable(False)

        toolbar.addWidget(QLabel(" 时基: "))
        self._time_base_combo = QComboBox()
        for ms in self.TIME_BASE_OPTIONS:
            self._time_base_combo.addItem(f"{ms} ms/div", ms)
        self._time_base_combo.setCurrentIndex(2)
        self._time_base_combo.currentIndexChanged.connect(self._on_time_base_changed)
        toolbar.addWidget(self._time_base_combo)

        toolbar.addWidget(QLabel(" 触发: "))
        self._trigger_combo = QComboBox()
        self._trigger_combo.addItems(["自动", "正常", "单次"])
        self._trigger_combo.currentIndexChanged.connect(self._on_trigger_changed)
        toolbar.addWidget(self._trigger_combo)

        toolbar.addWidget(QLabel(" 缩放: "))
        self._scale_combo = QComboBox()
        self._scale_combo.addItems(["自动", "手动"])
        self._scale_combo.currentIndexChanged.connect(self._on_scale_changed)
        toolbar.addWidget(self._scale_combo)

        toolbar.addWidget(QLabel(" 主题: "))
        self._theme_combo = QComboBox()
        self._theme_combo.addItems(["暗色", "亮色"])
        self._theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        toolbar.addWidget(self._theme_combo)

        layout.addWidget(toolbar)

        self._plot_widget = pg.PlotWidget()
        self._plot_widget.setBackground('k')
        self._plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self._plot_widget.setLabel('left', 'Value')
        self._plot_widget.setLabel('bottom', 'Time', units='s')
        self._plot_widget.addLegend(offset=(10, 10))

        layout.addWidget(self._plot_widget)

    def add_channel(self, channel: int, name: str = None):
        if not PYQTGRAPH_AVAILABLE:
            return
        if channel in self._channels:
            return
        if name is None:
            name = f"CH{channel}"
        color = self.CHANNEL_COLORS[channel % len(self.CHANNEL_COLORS)]
        curve = self._plot_widget.plot(pen=pg.mkPen(color, width=2), name=name)
        self._channels[channel] = {
            'curve': curve,
            'name': name,
            'color': color,
        }

    def remove_channel(self, channel: int):
        if not PYQTGRAPH_AVAILABLE:
            return
        ch_info = self._channels.pop(channel, None)
        if ch_info is not None:
            self._plot_widget.removeItem(ch_info['curve'])

    def update_data(self, channel: int, timestamps: list, values: list):
        if not PYQTGRAPH_AVAILABLE:
            return
        if channel not in self._channels:
            return
        if not timestamps or not values:
            return
        t0 = timestamps[0]
        t_rel = [t - t0 for t in timestamps]
        self._channels[channel]['curve'].setData(t_rel, values)

        if self._vertical_scale == 'auto' and values:
            import math
            vmin = min(values)
            vmax = max(values)
            margin = max(abs(vmax - vmin) * 0.1, 0.001)
            self._plot_widget.setYRange(vmin - margin, vmax + margin)

    def set_time_base(self, ms_per_div: int):
        self._time_base_ms = ms_per_div
        if PYQTGRAPH_AVAILABLE:
            self._plot_widget.setXRange(0, ms_per_div * 10 / 1000.0)

    def set_trigger_mode(self, mode: str):
        self._trigger_mode = mode

    def set_color_theme(self, theme: str):
        self._color_theme = theme
        if not PYQTGRAPH_AVAILABLE:
            return
        if theme == 'light':
            self._plot_widget.setBackground('w')
        else:
            self._plot_widget.setBackground('k')

    def set_vertical_scale(self, mode: str):
        self._vertical_scale = mode
        if mode == 'auto' and PYQTGRAPH_AVAILABLE:
            self._plot_widget.enableAutoRange(axis='y')

    def clear_all(self):
        for ch_info in self._channels.values():
            ch_info['curve'].setData([], [])
        self._channels.clear()

    def _on_time_base_changed(self, index):
        ms = self._time_base_combo.itemData(index)
        if ms is not None:
            self.set_time_base(ms)

    def _on_trigger_changed(self, index):
        modes = ['auto', 'normal', 'single']
        if 0 <= index < len(modes):
            self._trigger_mode = modes[index]

    def _on_scale_changed(self, index):
        modes = ['auto', 'manual']
        if 0 <= index < len(modes):
            self.set_vertical_scale(modes[index])

    def _on_theme_changed(self, index):
        themes = ['dark', 'light']
        if 0 <= index < len(themes):
            self.set_color_theme(themes[index])
