from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QCheckBox,
                              QLabel, QPushButton, QComboBox, QDoubleSpinBox,
                              QColorDialog)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QIcon, QColor

from ..models.channel_config import V_DIV_STEPS, DRAW_STYLES, DEFAULT_CHANNEL_COLORS


class ChannelCard(QWidget):

    channel_enabled_changed = pyqtSignal(int, bool)
    channel_color_changed = pyqtSignal(int, str)
    channel_style_changed = pyqtSignal(int, int)
    channel_vdiv_changed = pyqtSignal(int, float)
    channel_yoffset_changed = pyqtSignal(int, float)
    channel_name_changed = pyqtSignal(int, str)

    def __init__(self, channel: int, parent=None):
        super().__init__(parent)
        self._channel = channel
        self._block_signals = False
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(3)

        header = QHBoxLayout()
        header.setSpacing(4)

        self._enabled_cb = QCheckBox()
        self._enabled_cb.setChecked(True)
        self._enabled_cb.stateChanged.connect(self._on_enabled_changed)
        header.addWidget(self._enabled_cb)

        self._name_label = QLabel(f"CH{self._channel}")
        self._name_label.setStyleSheet("font-weight: bold; font-size: 11px;")
        header.addWidget(self._name_label)

        self._active_indicator = QLabel("●")
        self._active_indicator.setStyleSheet("color: #555; font-size: 10px;")
        self._active_indicator.setFixedWidth(12)
        self._active_indicator.setToolTip("空闲")
        header.addWidget(self._active_indicator)

        self._color_btn = QPushButton()
        self._color_btn.setFixedSize(20, 20)
        default_color = DEFAULT_CHANNEL_COLORS[
            (self._channel - 1) % len(DEFAULT_CHANNEL_COLORS)]
        self._set_color_btn_style(default_color)
        self._color_btn.clicked.connect(self._on_color_clicked)
        header.addWidget(self._color_btn)

        header.addStretch()
        layout.addLayout(header)

        style_row = QHBoxLayout()
        style_row.setSpacing(4)
        style_label = QLabel("样式:")
        style_label.setFixedWidth(32)
        style_row.addWidget(style_label)
        self._style_combo = QComboBox()
        self._style_combo.addItems(DRAW_STYLES)
        self._style_combo.currentIndexChanged.connect(self._on_style_changed)
        style_row.addWidget(self._style_combo)
        style_row.addStretch()
        layout.addLayout(style_row)

        vdiv_row = QHBoxLayout()
        vdiv_row.setSpacing(4)
        vdiv_label = QLabel("V/div:")
        vdiv_label.setFixedWidth(32)
        vdiv_row.addWidget(vdiv_label)
        self._vdiv_combo = QComboBox()
        for v in V_DIV_STEPS:
            self._vdiv_combo.addItem(f"{v:.3g}", v)
        self._vdiv_combo.setCurrentIndex(V_DIV_STEPS.index(1.0))
        self._vdiv_combo.currentIndexChanged.connect(self._on_vdiv_changed)
        vdiv_row.addWidget(self._vdiv_combo)
        layout.addLayout(vdiv_row)

        yoffset_row = QHBoxLayout()
        yoffset_row.setSpacing(4)
        yoffset_label = QLabel("Y偏移:")
        yoffset_label.setFixedWidth(32)
        yoffset_row.addWidget(yoffset_label)
        self._yoffset_spin = QDoubleSpinBox()
        self._yoffset_spin.setRange(-100.0, 100.0)
        self._yoffset_spin.setDecimals(2)
        self._yoffset_spin.setSingleStep(0.1)
        self._yoffset_spin.setValue(0.0)
        self._yoffset_spin.valueChanged.connect(self._on_yoffset_changed)
        yoffset_row.addWidget(self._yoffset_spin)
        layout.addLayout(yoffset_row)

        fmt_row = QHBoxLayout()
        fmt_row.setSpacing(4)
        fmt_label = QLabel("格式:")
        fmt_label.setFixedWidth(32)
        fmt_row.addWidget(fmt_label)
        self._format_label = QLabel("自动识别")
        self._format_label.setStyleSheet("color: #00AAFF; font-weight: bold; font-size: 10px;")
        fmt_row.addWidget(self._format_label)
        layout.addLayout(fmt_row)

        buf_row = QHBoxLayout()
        buf_row.setSpacing(4)
        buf_label = QLabel("缓冲:")
        buf_label.setFixedWidth(32)
        buf_row.addWidget(buf_label)
        self._mcu_buf_label = QLabel("?")
        self._mcu_buf_label.setStyleSheet("color: #888888; font-size: 10px;")
        self._mcu_buf_label.setToolTip("MCU侧RTT上行缓冲区大小")
        buf_row.addWidget(self._mcu_buf_label)
        layout.addLayout(buf_row)

        self.setStyleSheet(
            "ChannelCard { border: 1px solid #555; border-radius: 3px; }"
        )

    def _set_color_btn_style(self, color: str):
        self._color_btn.setStyleSheet(
            f"background-color: {color}; border: 1px solid #888; border-radius: 2px;")

    def _on_enabled_changed(self, state):
        if self._block_signals:
            return
        enabled = state == Qt.Checked
        self.channel_enabled_changed.emit(self._channel, enabled)

    def _on_color_clicked(self):
        current = self._color_btn.property('channel_color') or '#00FF00'
        color = QColorDialog.getColor(QColor(current), self, "选择通道颜色")
        if color.isValid():
            name = color.name()
            self._set_color_btn_style(name)
            self._color_btn.setProperty('channel_color', name)
            if not self._block_signals:
                self.channel_color_changed.emit(self._channel, name)

    def _on_style_changed(self, index):
        if self._block_signals:
            return
        self.channel_style_changed.emit(self._channel, index)

    def _on_vdiv_changed(self, index):
        if self._block_signals:
            return
        value = self._vdiv_combo.currentData()
        if value is not None:
            self.channel_vdiv_changed.emit(self._channel, float(value))

    def _on_yoffset_changed(self, value):
        if self._block_signals:
            return
        self.channel_yoffset_changed.emit(self._channel, value)

    def set_channel_info(self, info: dict) -> None:
        self._block_signals = True
        try:
            if 'enabled' in info:
                self._enabled_cb.setChecked(info['enabled'])
            if 'color' in info:
                self._set_color_btn_style(info['color'])
                self._color_btn.setProperty('channel_color', info['color'])
            if 'name' in info:
                self._name_label.setText(info['name'])
            if 'style' in info:
                self._style_combo.setCurrentIndex(info['style'])
            if 'vdiv' in info:
                vdiv = info['vdiv']
                closest = min(range(len(V_DIV_STEPS)),
                              key=lambda i: abs(V_DIV_STEPS[i] - vdiv))
                self._vdiv_combo.setCurrentIndex(closest)
            if 'yoffset' in info:
                self._yoffset_spin.setValue(info['yoffset'])
        finally:
            self._block_signals = False

    def get_channel_info(self) -> dict:
        return {
            'channel': self._channel,
            'enabled': self._enabled_cb.isChecked(),
            'color': self._color_btn.property('channel_color') or '#00FF00',
            'name': self._name_label.text(),
            'style': self._style_combo.currentIndex(),
            'vdiv': self._vdiv_combo.currentData() or 1.0,
            'yoffset': self._yoffset_spin.value(),
        }

    def set_color(self, color: str) -> None:
        self._block_signals = True
        try:
            self._set_color_btn_style(color)
            self._color_btn.setProperty('channel_color', color)
        finally:
            self._block_signals = False

    def set_format_text(self, text: str) -> None:
        self._format_label.setText(text)

    def set_mcu_buffer_text(self, text: str, tooltip: str = "") -> None:
        self._mcu_buf_label.setText(text)
        if tooltip:
            self._mcu_buf_label.setToolTip(tooltip)

    def set_active(self, active: bool) -> None:
        if active:
            self._active_indicator.setStyleSheet("color: #00FF00; font-size: 10px;")
            self._active_indicator.setToolTip("活跃")
        else:
            self._active_indicator.setStyleSheet("color: #555; font-size: 10px;")
            self._active_indicator.setToolTip("空闲")

    @property
    def channel_number(self) -> int:
        return self._channel
