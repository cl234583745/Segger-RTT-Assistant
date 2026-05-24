from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QToolBar, QComboBox,
                              QLabel, QHBoxLayout, QAction, QPushButton,
                              QSpinBox, QMenu, QCheckBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPixmap, QIcon, QColor

try:
    import pyqtgraph as pg
    from pyqtgraph import SignalProxy
    PYQTGRAPH_AVAILABLE = True
except ImportError:
    PYQTGRAPH_AVAILABLE = False

from ..processors.waveform_processor import DataFormat
from .time_base_manager import TimeBaseManager
from .view_mode_strategy import ViewModeStrategy
from .free_explore_strategy import FreeExploreViewStrategy
from .oscilloscope_strategy import OscilloscopeViewStrategy


DEFAULT_CHANNEL_COLORS = [
    '#00FF00', '#FF6600', '#00AAFF', '#FF00FF',
    '#FFFF00', '#00FFFF', '#FF8888', '#88FF88',
    '#AA88FF', '#FFAA88',
]

DRAW_STYLES = ["线条", "点", "线+点", "矩形"]

V_DIV_STEPS = [
    0.001, 0.002, 0.005,
    0.01, 0.02, 0.05,
    0.1, 0.2, 0.5,
    1, 2, 5,
    10, 20, 50,
    100, 200, 500,
    1000, 2000, 5000,
]


class WaveformWidget(QWidget):

    acquisition_start = pyqtSignal()
    acquisition_stop = pyqtSignal()
    acquisition_pause = pyqtSignal()
    acquisition_resume = pyqtSignal()
    sampling_rate_changed = pyqtSignal(float)
    theme_changed = pyqtSignal(str)
    view_mode_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        _t0 = __import__('time').perf_counter()
        self._channels = {}
        self._tb_manager = TimeBaseManager(default_idx=9)
        self._trigger_mode = 'auto'
        self._vertical_scale = 'auto'
        self._color_theme = 'dark'
        self._channel_colors = {}
        self._channel_styles = {}
        self._channel_vdiv = {}
        self._channel_yoffset = {}
        self._channel_enabled = {}
        self._last_frequency = {}
        self._hs_frequencies = {}
        self._is_high_speed = False
        self._y_range_auto = True
        self._render_paused = False
        self._sampling_interval = 0
        self._pending_data = {}
        self._display_timer = QTimer()
        self._display_timer.setInterval(33)
        self._display_timer.timeout.connect(self._flush_display)

        self._view_mode = "oscilloscope"
        self._osc_strategy = None
        self._free_strategy = None
        self._current_strategy = None

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

        self._toolbar = QToolBar()
        self._toolbar.setMovable(False)

        self._create_acquisition_buttons(self._toolbar)
        self._toolbar.addSeparator()

        self._toolbar.addWidget(QLabel(" 视图: "))
        self._view_mode_combo = QComboBox()
        self._view_mode_combo.addItems(["自由探索", "示波器"])
        self._view_mode_combo.setCurrentIndex(1)
        self._view_mode_combo.currentIndexChanged.connect(self._on_view_mode_changed)
        self._toolbar.addWidget(self._view_mode_combo)

        self._toolbar.addSeparator()

        self._toolbar.addWidget(QLabel(" 时基: "))
        self._time_base_combo = QComboBox()
        for us_val in TimeBaseManager.STEPS_US:
            display = TimeBaseManager.to_display_string(us_val)
            self._time_base_combo.addItem(display, us_val)
        self._time_base_combo.setCurrentIndex(self._tb_manager.index)
        self._time_base_combo.currentIndexChanged.connect(self._on_time_base_changed)
        self._toolbar.addWidget(self._time_base_combo)

        self._toolbar.addWidget(QLabel(" 触发: "))
        self._trigger_combo = QComboBox()
        self._trigger_combo.addItems(["自动", "正常", "单次"])
        self._trigger_combo.currentIndexChanged.connect(self._on_trigger_changed)
        self._toolbar.addWidget(self._trigger_combo)

        self._create_sampling_control(self._toolbar)

        layout.addWidget(self._toolbar)

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

        self._proxy = SignalProxy(self._plot_widget.scene().sigMouseMoved, rateLimit=60, slot=self._on_mouse_moved)

        layout.addWidget(self._plot_widget)

        self._free_strategy = FreeExploreViewStrategy(self._tb_manager)
        self._osc_strategy = OscilloscopeViewStrategy(self._tb_manager)
        self._current_strategy = self._osc_strategy
        self._current_strategy.activate(self._plot_widget, self._channels)

    def _on_view_mode_changed(self, index):
        modes = ["free_explore", "oscilloscope"]
        new_mode = modes[index]
        if new_mode == self._view_mode:
            return
        self._current_strategy.deactivate(self._plot_widget)
        self._view_mode = new_mode
        if new_mode == "oscilloscope":
            self._current_strategy = self._osc_strategy
        else:
            self._current_strategy = self._free_strategy
        self._current_strategy.activate(self._plot_widget, self._channels)
        self._apply_time_base()
        self.view_mode_changed.emit(new_mode)
        if hasattr(self, '_config_service') and self._config_service:
            self._config_service.set('scope_view_mode', new_mode)
            self._config_service.save()

    def set_config_service(self, config_service):
        self._config_service = config_service
        if config_service:
            saved = config_service.get('scope_view_mode', 'oscilloscope')
            if saved in ('free_explore', 'oscilloscope'):
                idx = 0 if saved == 'free_explore' else 1
                self._view_mode_combo.setCurrentIndex(idx)

    def set_view_mode(self, mode):
        if mode == self._view_mode:
            return
        idx = 0 if mode == "free_explore" else 1
        self._view_mode_combo.setCurrentIndex(idx)

    def get_view_mode(self):
        return self._view_mode

    def _on_wheel_event(self, ev):
        ev.accept()
        delta = ev.angleDelta().y()
        new_idx = self._current_strategy.handle_wheel(
            self._plot_widget, delta, self._tb_manager.index)
        if new_idx != self._tb_manager.index:
            self._tb_manager.index = new_idx
            self._time_base_combo.blockSignals(True)
            self._time_base_combo.setCurrentIndex(new_idx)
            self._time_base_combo.blockSignals(False)
            self._apply_time_base()

    def _apply_time_base(self):
        vr = self._plot_widget.viewRange()
        center_x = (vr[0][0] + vr[0][1]) / 2.0
        self._current_strategy.apply_time_base(
            self._plot_widget, self._tb_manager.current_value(), center_x)

    def _on_view_range_changed(self, vb, ranges):
        vr = self._plot_widget.viewRange()
        x_max = vr[0][1]
        y_max = vr[1][1]
        y_range = vr[1][1] - vr[1][0]
        ch_idx = 0
        for ch_info in self._channels.values():
            if 'freq_text' in ch_info:
                ch_info['freq_text'].setPos(x_max, y_max - ch_idx * y_range * 0.08)
                ch_idx += 1

    def _on_mouse_moved(self, evt):
        pos = evt[0]
        if self._plot_widget.sceneBoundingRect().contains(pos):
            mouse_point = self._plot_widget.getViewBox().mapSceneToView(pos)
            self._vline.setPos(mouse_point.x())
            self._hline.setPos(mouse_point.y())
        else:
            self._vline.setVisible(False)
            self._hline.setVisible(False)

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

    def _create_sampling_control(self, toolbar: QToolBar) -> None:
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
            self._current_strategy.set_drag_enabled(
                self._plot_widget, x_enabled=True, y_enabled=False)
        elif state == 'running':
            self._start_stop_btn.setEnabled(True)
            self._start_stop_btn.setText("停止")
            self._pause_btn.setEnabled(True)
            self._pause_btn.setText("暂停")
            self._display_timer.start()
            self._current_strategy.set_drag_enabled(
                self._plot_widget, x_enabled=False, y_enabled=False)
        elif state == 'paused':
            self._start_stop_btn.setEnabled(True)
            self._start_stop_btn.setText("停止")
            self._pause_btn.setEnabled(True)
            self._pause_btn.setText("恢复")
            self._display_timer.stop()
            self._current_strategy.set_drag_enabled(
                self._plot_widget, x_enabled=True, y_enabled=False)

    def _get_channel_color(self, channel: int) -> str:
        if channel in self._channel_colors:
            return self._channel_colors[channel]
        default = DEFAULT_CHANNEL_COLORS[(channel - 1) % len(DEFAULT_CHANNEL_COLORS)]
        self._channel_colors[channel] = default
        return default

    def _get_channel_style(self, channel: int) -> int:
        return self._channel_styles.get(channel, 0)

    def _get_channel_vdiv(self, channel: int) -> float:
        return self._channel_vdiv.get(channel, 1.0)

    def _get_channel_yoffset(self, channel: int) -> float:
        return self._channel_yoffset.get(channel, 0.0)

    def _get_channel_enabled(self, channel: int) -> bool:
        return self._channel_enabled.get(channel, True)

    def _get_draw_kwargs(self, color: str, style: int) -> dict:
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
        style = self._get_channel_style(channel)
        draw_kwargs = self._get_draw_kwargs(color, style)
        curve = self._plot_widget.plot(name=name, **draw_kwargs)

        freq_text = pg.TextItem(text='', color=color, anchor=(1, 0))
        vr = self._plot_widget.viewRange()
        y_range = vr[1][1] - vr[1][0] if vr[1][1] != vr[1][0] else 1.0
        ch_idx = len(self._channels)
        freq_text.setPos(vr[0][1], vr[1][1] - ch_idx * y_range * 0.08)
        self._plot_widget.addItem(freq_text)

        curve.setDownsampling(ds=True, auto=True, method='peak')

        self._channels[channel] = {
            'curve': curve,
            'name': name,
            'color': color,
            'style': style,
            'vdiv': self._get_channel_vdiv(channel),
            'yoffset': self._get_channel_yoffset(channel),
            'enabled': self._get_channel_enabled(channel),
            'freq_text': freq_text,
            'has_data': False,
        }

    def _redraw_channel(self, channel: int):
        ch_info = self._channels[channel]
        old_curve = ch_info['curve']
        x_data = old_curve.xData
        y_data = old_curve.yData
        color = ch_info['color']
        style = ch_info['style']
        draw_kwargs = self._get_draw_kwargs(color, style)
        self._plot_widget.removeItem(old_curve)
        new_curve = self._plot_widget.plot(name=ch_info['name'], **draw_kwargs)
        new_curve.setDownsampling(ds=True, auto=True, method='peak')
        if x_data is not None and y_data is not None and ch_info['has_data']:
            vdiv = ch_info['vdiv']
            yoffset = ch_info['yoffset']
            if vdiv != 1.0 or yoffset != 0.0:
                scaled_y = [(v - yoffset) / vdiv for v in y_data]
                new_curve.setData(x_data, scaled_y)
            else:
                new_curve.setData(x_data, y_data)
        ch_info['curve'] = new_curve
        new_curve.setVisible(ch_info['enabled'])
        if 'freq_text' in ch_info:
            ch_info['freq_text'].setColor(color)

    def _redraw_all_channels(self):
        for ch in list(self._channels.keys()):
            self._redraw_channel(ch)

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

    def update_frequency(self, channel: int, frequency: float):
        self._hs_frequencies[channel] = frequency

    def set_high_speed_mode(self, enabled: bool):
        self._is_high_speed = enabled
        if not enabled:
            self._hs_frequencies.clear()

    def _flush_display(self):
        if not self._pending_data:
            return
        import time
        t0 = time.perf_counter()
        ch_count = 0
        for channel, (timestamps, values) in self._pending_data.items():
            if channel not in self._channels:
                continue
            ch_info = self._channels[channel]
            ch_info['has_data'] = True
            ch_count += 1

            vdiv = ch_info['vdiv']
            yoffset = ch_info['yoffset']
            if vdiv != 1.0 or yoffset != 0.0:
                scaled_values = [(v - yoffset) / vdiv for v in values]
                ch_info['curve'].setData(timestamps, scaled_values)
            else:
                ch_info['curve'].setData(timestamps, values)

            ch_info['curve'].setVisible(ch_info['enabled'])

            if self._y_range_auto and values and self._view_mode != "oscilloscope":
                vmin = min(values)
                vmax = max(values)
                margin = max(abs(vmax - vmin) * 0.1, 0.001)
                self._plot_widget.setYRange(vmin - margin, vmax + margin)

            if not self._render_paused and len(timestamps) > 1:
                x_max = timestamps[-1]
                x_min = timestamps[0]
                vr = self._plot_widget.viewRange()
                self._current_strategy.update_view_range(
                    self._plot_widget, x_min, x_max,
                    vr[1][0], vr[1][1])

            if len(values) >= 3 and ch_info['enabled']:
                if self._is_high_speed and channel in self._hs_frequencies:
                    frequency = self._hs_frequencies[channel]
                else:
                    frequency = self._calculate_frequency(timestamps, values)
                if frequency is not None and frequency > 0:
                    self._last_frequency[channel] = frequency
                    if 'freq_text' in ch_info:
                        if frequency < 1000:
                            freq_str = f"{frequency:.1f} Hz"
                        else:
                            freq_str = f"{frequency/1000:.2f} kHz"
                        period = 1.0 / frequency * 1000
                        ch_name = ch_info['name']
                        ch_info['freq_text'].setText(f"{ch_name}: {freq_str}\nT={period:.3f}ms")
                        ch_info['freq_text'].setVisible(True)
                else:
                    if 'freq_text' in ch_info:
                        ch_info['freq_text'].setVisible(False)
            else:
                if 'freq_text' in ch_info:
                    ch_info['freq_text'].setVisible(False)

        self._pending_data.clear()

        elapsed = (time.perf_counter() - t0) * 1000
        if not hasattr(self, '_flush_log_counter'):
            self._flush_log_counter = 0
        self._flush_log_counter += 1
        if self._flush_log_counter <= 5 or self._flush_log_counter % 200 == 0:
            import logging
            logging.getLogger(__name__).info(
                f"[flush] #{self._flush_log_counter} ch_count={ch_count} elapsed={elapsed:.1f}ms")

        if self._view_mode == "oscilloscope":
            self._auto_y_range_multi_channel()
            if self._current_strategy and self._current_strategy._grid_item:
                self._sync_y_grid_ticks()

    def _auto_y_range_multi_channel(self):
        if not self._y_range_auto:
            return
        all_min = None
        all_max = None
        for ch_info in self._channels.values():
            if not ch_info['enabled'] or not ch_info.get('has_data'):
                continue
            curve = ch_info['curve']
            y_data = curve.yData
            if y_data is not None and len(y_data) > 0:
                ch_min = float(min(y_data))
                ch_max = float(max(y_data))
                if all_min is None or ch_min < all_min:
                    all_min = ch_min
                if all_max is None or ch_max > all_max:
                    all_max = ch_max
        if all_min is not None and all_max is not None:
            margin = max(abs(all_max - all_min) * 0.1, 0.001)
            self._plot_widget.setYRange(all_min - margin, all_max + margin)

    def _sync_y_grid_ticks(self):
        y_axis = self._plot_widget.getAxis('left')
        try:
            vr = self._plot_widget.viewRange()
            ticks = y_axis.tickValues(vr[1][0], vr[1][1], self._plot_widget.getViewBox().height())
            if ticks:
                for spacing, values in ticks:
                    if len(values) >= 2 and spacing > 0:
                        self._current_strategy._grid_item.set_y_tick_spacing(spacing)
                        return
        except Exception:
            pass

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
        for i, v in enumerate(TimeBaseManager.STEPS_US):
            if v == us_per_div:
                idx = i
                break
        if idx is None:
            closest = min(range(len(TimeBaseManager.STEPS_US)),
                          key=lambda i: abs(TimeBaseManager.STEPS_US[i] - us_per_div))
            idx = closest
        self._tb_manager.index = idx
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
        self._tb_manager.index = index
        self._apply_time_base()

    def _on_trigger_changed(self, index):
        modes = ['auto', 'normal', 'single']
        if 0 <= index < len(modes):
            self._trigger_mode = modes[index]

    def set_channel_color(self, channel: int, color: str) -> None:
        if channel not in self._channels:
            return
        self._channels[channel]['color'] = color
        self._channel_colors[channel] = color
        self._redraw_channel(channel)

    def set_channel_style(self, channel: int, style: int) -> None:
        if channel not in self._channels:
            return
        self._channels[channel]['style'] = style
        self._channel_styles[channel] = style
        self._redraw_channel(channel)

    def set_channel_vdiv(self, channel: int, vdiv: float) -> None:
        if vdiv <= 0:
            return
        if channel not in self._channels:
            return
        self._channels[channel]['vdiv'] = vdiv
        self._channel_vdiv[channel] = vdiv
        self._redraw_channel(channel)

    def set_channel_yoffset(self, channel: int, yoffset: float) -> None:
        if channel not in self._channels:
            return
        self._channels[channel]['yoffset'] = yoffset
        self._channel_yoffset[channel] = yoffset
        self._redraw_channel(channel)

    def set_channel_enabled(self, channel: int, enabled: bool) -> None:
        if channel not in self._channels:
            return
        self._channels[channel]['enabled'] = enabled
        self._channel_enabled[channel] = enabled
        self._channels[channel]['curve'].setVisible(enabled)
