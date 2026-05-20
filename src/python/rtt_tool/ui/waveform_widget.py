from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QToolBar, QComboBox,
                              QLabel, QHBoxLayout, QAction, QPushButton,
                              QSpinBox, QMenu)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal

try:
    import pyqtgraph as pg
    from pyqtgraph import SignalProxy
    PYQTGRAPH_AVAILABLE = True
except ImportError:
    PYQTGRAPH_AVAILABLE = False

from ..processors.waveform_processor import DataFormat


TIME_BASE_STEPS_US = [
    1, 2, 5,
    10, 20, 50,
    100, 200, 500,
    1000, 2000, 5000,
    10000, 20000, 50000,
    100000, 200000, 500000,
    1000000, 2000000, 5000000,
    10000000, 20000000, 50000000,
    100000000, 200000000, 500000000,
]


def _us_to_display(us_val):
    if us_val < 1000:
        return f"{us_val} µs/div", us_val
    elif us_val < 1000000:
        return f"{us_val / 1000:.3g} ms/div", us_val
    else:
        return f"{us_val / 1000000:.3g} s/div", us_val


COLOR_SCHEMES = [
    ("默认", ['#00FF00', '#FF6600', '#00AAFF', '#FF00FF', '#FFFF00', '#00FFFF', '#FF8888', '#88FF88']),
    ("暖色", ['#FF4444', '#FF8800', '#FFCC00', '#FF6688', '#FFaa66', '#FF4488', '#FF7744', '#FF5599']),
    ("冷色", ['#00CCFF', '#0088FF', '#00FFCC', '#4488FF', '#66CCFF', '#00AA88', '#3399FF', '#00DDAA']),
    ("灰阶", ['#FFFFFF', '#CCCCCC', '#999999', '#666666', '#BBBBBB', '#888888', '#AAAAAA', '#777777']),
]

DRAW_STYLES = ["线条", "点", "线+点", "矩形"]


class WaveformWidget(QWidget):
    """基于 PyQtGraph 的实时波形显示组件。"""

    acquisition_start = pyqtSignal()
    acquisition_stop = pyqtSignal()
    acquisition_pause = pyqtSignal()
    acquisition_resume = pyqtSignal()
    sampling_rate_changed = pyqtSignal(float)
    theme_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        _t0 = __import__('time').perf_counter()
        self._channels = {}
        self._time_base_idx = 9
        self._trigger_mode = 'auto'
        self._vertical_scale = 'auto'
        self._color_theme = 'dark'
        self._color_scheme_idx = 0
        self._draw_style_idx = 0
        self._last_frequency = {}
        self._y_range_auto = True
        self._render_paused = False
        self._sampling_interval = 0
        self._pending_data = {}
        self._display_timer = QTimer()
        self._display_timer.setInterval(33)
        self._display_timer.timeout.connect(self._flush_display)

        if PYQTGRAPH_AVAILABLE:
            self._init_ui()
        else:
            layout = QVBoxLayout(self)
            label = QLabel("pyqtgraph 未安装，示波器模式不可用。\n请执行: pip install pyqtgraph")
            label.setAlignment(Qt.AlignCenter)
            layout.addWidget(label)
        print(f"[perf] WaveformWidget.__init__: {(__import__('time').perf_counter()-_t0)*1000:.0f}ms")

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        toolbar = QToolBar()
        toolbar.setMovable(False)

        self._create_acquisition_buttons(toolbar)
        toolbar.addSeparator()

        toolbar.addWidget(QLabel(" 时基: "))
        self._time_base_combo = QComboBox()
        for us_val in TIME_BASE_STEPS_US:
            display, _ = _us_to_display(us_val)
            self._time_base_combo.addItem(display, us_val)
        self._time_base_combo.setCurrentIndex(self._time_base_idx)
        self._time_base_combo.currentIndexChanged.connect(self._on_time_base_changed)
        toolbar.addWidget(self._time_base_combo)

        toolbar.addWidget(QLabel(" 触发: "))
        self._trigger_combo = QComboBox()
        self._trigger_combo.addItems(["自动", "正常", "单次"])
        self._trigger_combo.currentIndexChanged.connect(self._on_trigger_changed)
        toolbar.addWidget(self._trigger_combo)

        toolbar.addWidget(QLabel(" 配色: "))
        self._color_scheme_combo = QComboBox()
        for name, _ in COLOR_SCHEMES:
            self._color_scheme_combo.addItem(name)
        self._color_scheme_combo.currentIndexChanged.connect(self._on_color_scheme_changed)
        toolbar.addWidget(self._color_scheme_combo)

        toolbar.addWidget(QLabel(" 样式: "))
        self._draw_style_combo = QComboBox()
        self._draw_style_combo.addItems(DRAW_STYLES)
        self._draw_style_combo.currentIndexChanged.connect(self._on_draw_style_changed)
        toolbar.addWidget(self._draw_style_combo)

        self._create_format_sampling_controls(toolbar)

        layout.addWidget(toolbar)

        _pt = __import__('time').perf_counter()
        self._plot_widget = pg.PlotWidget()
        print(f"[perf]   pg.PlotWidget(): {(__import__('time').perf_counter()-_pt)*1000:.0f}ms")
        self._plot_widget.setBackground('k')
        self._plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self._plot_widget.setLabel('left', 'Value')
        self._plot_widget.setLabel('bottom', 'Time (s)')
        self._plot_widget.addLegend(offset=(10, 10))

        vb = self._plot_widget.getViewBox()
        vb.setMouseEnabled(x=True, y=False)
        vb.sigRangeChanged.connect(self._on_view_range_changed)

        vb.menu = QMenu()
        vb.menu.setTitle("示波器")
        act_auto = vb.menu.addAction("自动范围")
        act_auto.triggered.connect(lambda: self._plot_widget.enableAutoRange())
        act_reset = vb.menu.addAction("重置视图")
        act_reset.triggered.connect(lambda: self._plot_widget.autoRange())
        vb.menu.addSeparator()
        act_grid = vb.menu.addAction("显示网格")
        act_grid.setCheckable(True)
        act_grid.setChecked(True)
        act_grid.toggled.connect(lambda checked: self._plot_widget.showGrid(x=checked, y=checked, alpha=0.3 if checked else 0))

        self._plot_widget.wheelEvent = self._on_wheel_event

        self._vline = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('y', width=1, style=Qt.DashLine))
        self._hline = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('y', width=1, style=Qt.DashLine))
        self._plot_widget.addItem(self._vline, ignoreBounds=True)
        self._plot_widget.addItem(self._hline, ignoreBounds=True)

        self._cursor_label = pg.TextItem(text='', color='y', anchor=(0, 1))
        self._plot_widget.addItem(self._cursor_label, ignoreBounds=True)

        self._proxy = SignalProxy(self._plot_widget.scene().sigMouseMoved, rateLimit=60, slot=self._on_mouse_moved)

        layout.addWidget(self._plot_widget)

    def _on_wheel_event(self, ev):
        ev.accept()
        delta = ev.angleDelta().y()
        if delta > 0:
            new_idx = max(self._time_base_idx - 1, 0)
        elif delta < 0:
            new_idx = min(self._time_base_idx + 1, len(TIME_BASE_STEPS_US) - 1)
        else:
            return
        if new_idx != self._time_base_idx:
            self._time_base_idx = new_idx
            self._time_base_combo.blockSignals(True)
            self._time_base_combo.setCurrentIndex(new_idx)
            self._time_base_combo.blockSignals(False)
            self._apply_time_base()

    def _apply_time_base(self):
        us_val = TIME_BASE_STEPS_US[self._time_base_idx]
        x_range = us_val * 10 / 1000000.0
        vr = self._plot_widget.viewRange()
        x_center = (vr[0][0] + vr[0][1]) / 2.0
        self._plot_widget.setXRange(x_center - x_range / 2, x_center + x_range / 2, padding=0)

    def _on_view_range_changed(self, vb, ranges):
        vr = self._plot_widget.viewRange()
        x_max = vr[0][1]
        y_max = vr[1][1]
        for ch_info in self._channels.values():
            if 'freq_text' in ch_info:
                ch_info['freq_text'].setPos(x_max, y_max)

    def _on_mouse_moved(self, evt):
        pos = evt[0]
        if self._plot_widget.sceneBoundingRect().contains(pos):
            mouse_point = self._plot_widget.getViewBox().mapSceneToView(pos)
            x, y = mouse_point.x(), mouse_point.y()
            self._vline.setPos(x)
            self._hline.setPos(y)
            nearest_val = None
            for ch_info in self._channels.values():
                curve = ch_info['curve']
                x_data = curve.xData
                y_data = curve.yData
                if x_data is not None and len(x_data) > 0:
                    idx = int(round(x))
                    if 0 <= idx < len(y_data):
                        nearest_val = y_data[idx]
                        break
            if nearest_val is not None:
                self._cursor_label.setText(f"x={x:.0f}  y={nearest_val:.4g}")
            else:
                self._cursor_label.setText(f"x={x:.0f}  y={y:.4g}")
            vr = self._plot_widget.viewRange()
            self._cursor_label.setPos(vr[0][0], vr[1][0])
        else:
            self._vline.setVisible(False)
            self._hline.setVisible(False)
            self._cursor_label.setVisible(False)

    def _create_acquisition_buttons(self, toolbar: QToolBar) -> None:
        self._start_stop_btn = QPushButton("开始")
        self._start_stop_btn.clicked.connect(self._on_start_stop_clicked)
        toolbar.addWidget(self._start_stop_btn)

        self._pause_btn = QPushButton("暂停")
        self._pause_btn.setEnabled(False)
        self._pause_btn.clicked.connect(self._on_pause_clicked)
        toolbar.addWidget(self._pause_btn)

        self._clear_btn = QPushButton("清除")
        self._clear_btn.clicked.connect(self._on_clear_clicked)
        toolbar.addWidget(self._clear_btn)

    def _create_format_sampling_controls(self, toolbar: QToolBar) -> None:
        toolbar.addSeparator()

        toolbar.addWidget(QLabel(" 格式: "))
        self._format_label = QLabel("自动识别")
        self._format_label.setStyleSheet("color: #00AAFF; font-weight: bold;")
        toolbar.addWidget(self._format_label)

        toolbar.addWidget(QLabel("  MCU缓冲: "))
        self._mcu_buf_label = QLabel("?")
        self._mcu_buf_label.setStyleSheet("color: #888888;")
        self._mcu_buf_label.setToolTip("MCU侧RTT上行缓冲区大小")
        toolbar.addWidget(self._mcu_buf_label)

        toolbar.addSeparator()

        toolbar.addWidget(QLabel(" 采样率: "))
        self._sample_rate_spin = QSpinBox()
        self._sample_rate_spin.setRange(0, 1000000)
        self._sample_rate_spin.setSuffix(" Hz")
        self._sample_rate_spin.setSpecialValueText("自动")
        self._sample_rate_spin.setValue(0)
        self._sample_rate_spin.setToolTip("采样率(Hz)。0=自动估算，即尽可能快地采样")
        self._sample_rate_spin.valueChanged.connect(self._on_sampling_rate_changed)
        toolbar.addWidget(self._sample_rate_spin)

    def _on_start_stop_clicked(self) -> None:
        if self._start_stop_btn.text() == "开始":
            self.acquisition_start.emit()
        else:
            self.acquisition_stop.emit()

    def _on_clear_clicked(self) -> None:
        self.clear_all()

    def set_format_text(self, text: str) -> None:
        self._format_label.setText(text)

    def set_mcu_buffer_info(self, channel: int, size: int, name: str = ""):
        txt = f"CH{channel}={size}B" if size > 0 else "?"
        self._mcu_buf_label.setText(txt)
        if name:
            self._mcu_buf_label.setToolTip(f"CH{channel}: \"{name}\" 大小={size}B")

    def _on_sampling_rate_changed(self, value: int) -> None:
        if value > 0:
            self._sampling_interval = 1.0 / value
        else:
            self._sampling_interval = 0
        self.sampling_rate_changed.emit(float(value))

    def _on_pause_clicked(self) -> None:
        if self._pause_btn.text() == "暂停":
            self.acquisition_pause.emit()
        else:
            self.acquisition_resume.emit()

    def update_acquisition_buttons(self, state: str) -> None:
        if state == 'idle':
            self._start_stop_btn.setEnabled(True)
            self._start_stop_btn.setText("开始")
            self._pause_btn.setEnabled(False)
            self._pause_btn.setText("暂停")
            self._display_timer.stop()
            self._pending_data.clear()
        elif state == 'running':
            self._start_stop_btn.setEnabled(True)
            self._start_stop_btn.setText("停止")
            self._pause_btn.setEnabled(True)
            self._pause_btn.setText("暂停")
            self._display_timer.start()
        elif state == 'paused':
            self._start_stop_btn.setEnabled(True)
            self._start_stop_btn.setText("停止")
            self._pause_btn.setEnabled(True)
            self._pause_btn.setText("恢复")
            self._display_timer.stop()

    def _get_channel_color(self, channel: int) -> str:
        _, colors = COLOR_SCHEMES[self._color_scheme_idx]
        return colors[channel % len(colors)]

    def _get_draw_kwargs(self, color: str) -> dict:
        style = self._draw_style_idx
        kwargs = {}
        if style == 0:
            kwargs['pen'] = pg.mkPen(color, width=2)
            kwargs['symbol'] = None
        elif style == 1:
            kwargs['pen'] = None
            kwargs['symbol'] = 'o'
            kwargs['symbolSize'] = 4
            kwargs['symbolBrush'] = color
        elif style == 2:
            kwargs['pen'] = pg.mkPen(color, width=2)
            kwargs['symbol'] = 'o'
            kwargs['symbolSize'] = 3
            kwargs['symbolBrush'] = color
        elif style == 3:
            kwargs['pen'] = pg.mkPen(color, width=1)
            kwargs['fillLevel'] = 0
            kwargs['brush'] = pg.mkBrush(color + '44')
            kwargs['symbol'] = None
        return kwargs

    def add_channel(self, channel: int, name: str = None):
        if not PYQTGRAPH_AVAILABLE:
            return
        if channel in self._channels:
            return
        if name is None:
            name = f"CH{channel}"
        color = self._get_channel_color(channel)
        draw_kwargs = self._get_draw_kwargs(color)
        curve = self._plot_widget.plot(name=name, **draw_kwargs)

        vr = self._plot_widget.viewRange()
        freq_text = pg.TextItem(text='', color=color, anchor=(1, 0))
        freq_text.setPos(vr[0][1], vr[1][1])
        self._plot_widget.addItem(freq_text)

        curve.setDownsampling(ds=True, auto=True, method='peak')

        self._channels[channel] = {
            'curve': curve,
            'name': name,
            'color': color,
            'freq_text': freq_text,
        }

    def _redraw_all_channels(self):
        for ch, ch_info in list(self._channels.items()):
            curve = ch_info['curve']
            x_data = curve.xData
            y_data = curve.yData
            color = self._get_channel_color(ch)
            draw_kwargs = self._get_draw_kwargs(color)
            self._plot_widget.removeItem(curve)
            new_curve = self._plot_widget.plot(name=ch_info['name'], **draw_kwargs)
            if x_data is not None and y_data is not None:
                new_curve.setData(x_data, y_data)
            ch_info['curve'] = new_curve
            ch_info['color'] = color

    def remove_channel(self, channel: int):
        if not PYQTGRAPH_AVAILABLE:
            return
        ch_info = self._channels.pop(channel, None)
        if ch_info is not None:
            self._plot_widget.removeItem(ch_info['curve'])
            if 'freq_text' in ch_info:
                self._plot_widget.removeItem(ch_info['freq_text'])

    def update_data(self, channel: int, timestamps: list, values: list):
        if not PYQTGRAPH_AVAILABLE:
            return
        if channel not in self._channels:
            self.add_channel(channel)
            import logging
            logging.getLogger(__name__).info(f"自动添加示波器通道 CH{channel}")
        if not timestamps or not values:
            return

        self._pending_data[channel] = (timestamps, values)

    def _flush_display(self):
        if not self._pending_data:
            return
        for channel, (timestamps, values) in self._pending_data.items():
            if channel not in self._channels:
                continue
            self._channels[channel]['curve'].setData(timestamps, values)

            if self._y_range_auto and values:
                vmin = min(values)
                vmax = max(values)
                margin = max(abs(vmax - vmin) * 0.1, 0.001)
                self._plot_widget.setYRange(vmin - margin, vmax + margin)

            if not self._render_paused and len(timestamps) > 1:
                x_max = timestamps[-1]
                x_min = timestamps[0]
                us_val = TIME_BASE_STEPS_US[self._time_base_idx]
                x_range_seconds = us_val * 10 / 1000000.0
                span = x_max - x_min
                if span <= 0:
                    span = x_range_seconds
                x_view_start = max(x_min, x_max - x_range_seconds)
                self._plot_widget.setXRange(x_view_start, x_max, padding=0)

            if len(values) >= 3:
                frequency = self._calculate_frequency(timestamps, values)
                if frequency is not None and frequency > 0:
                    self._last_frequency[channel] = frequency
                    if 'freq_text' in self._channels[channel]:
                        if frequency < 1000:
                            freq_str = f"{frequency:.1f} Hz"
                        else:
                            freq_str = f"{frequency/1000:.2f} kHz"
                        period = 1.0 / frequency * 1000
                        self._channels[channel]['freq_text'].setText(f"{freq_str}\nT={period:.3f}ms")
        self._pending_data.clear()

    def _calculate_frequency(self, timestamps: list, values: list) -> float:
        if len(values) < 10:
            return None
        peaks = []
        for i in range(1, len(values) - 1):
            if values[i] > values[i-1] and values[i] > values[i+1]:
                peaks.append(i)
        if len(peaks) < 2:
            return None
        intervals = []
        for i in range(1, len(peaks)):
            dt = timestamps[peaks[i]] - timestamps[peaks[i-1]]
            if dt > 0:
                intervals.append(dt)
        if not intervals:
            return None
        avg_period = sum(intervals) / len(intervals)
        return 1.0 / avg_period

    def set_time_base(self, us_per_div: int):
        idx = None
        for i, v in enumerate(TIME_BASE_STEPS_US):
            if v == us_per_div:
                idx = i
                break
        if idx is None:
            closest = min(range(len(TIME_BASE_STEPS_US)), key=lambda i: abs(TIME_BASE_STEPS_US[i] - us_per_div))
            idx = closest
        self._time_base_idx = idx
        self._time_base_combo.blockSignals(True)
        self._time_base_combo.setCurrentIndex(idx)
        self._time_base_combo.blockSignals(False)
        self._apply_time_base()

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
        self._y_range_auto = (mode == 'auto')
        if mode == 'auto' and PYQTGRAPH_AVAILABLE:
            self._plot_widget.enableAutoRange(axis='y')

    def clear_all(self):
        for ch_info in list(self._channels.values()):
            self._plot_widget.removeItem(ch_info['curve'])
            if 'freq_text' in ch_info:
                self._plot_widget.removeItem(ch_info['freq_text'])
        self._channels.clear()
        self._last_frequency.clear()
        self._pending_data.clear()

    def _on_time_base_changed(self, index):
        self._time_base_idx = index
        self._apply_time_base()

    def _on_trigger_changed(self, index):
        modes = ['auto', 'normal', 'single']
        if 0 <= index < len(modes):
            self._trigger_mode = modes[index]

    def _on_color_scheme_changed(self, index):
        self._color_scheme_idx = index
        self._redraw_all_channels()

    def _on_draw_style_changed(self, index):
        self._draw_style_idx = index
        self._redraw_all_channels()

    def _on_scale_changed(self, index):
        modes = ['auto', 'manual']
        if 0 <= index < len(modes):
            self.set_vertical_scale(modes[index])
