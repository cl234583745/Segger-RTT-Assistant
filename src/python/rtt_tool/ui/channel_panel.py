from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QScrollArea, QLabel, QSizePolicy, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize
from PyQt5.QtGui import QPixmap, QColor

from .channel_card import ChannelCard
from ..models.channel_config import DEFAULT_CHANNEL_COLORS


class ChannelPanel(QWidget):

    channel_enabled_changed = pyqtSignal(int, bool)
    channel_color_changed = pyqtSignal(int, str)
    channel_style_changed = pyqtSignal(int, int)
    channel_vdiv_changed = pyqtSignal(int, float)
    channel_yoffset_changed = pyqtSignal(int, float)
    channel_name_changed = pyqtSignal(int, str)

    panel_collapsed = pyqtSignal(bool)

    COLLAPSED_WIDTH = 40
    EXPANDED_WIDTH = 240

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards: dict = {}
        self._collapsed: bool = True
        self._color_tags: list = []
        self._init_ui()

    def _init_ui(self):
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        self._header = QWidget()
        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(2, 2, 2, 2)
        header_layout.setSpacing(2)

        self._toggle_btn = QPushButton(">")
        self._toggle_btn.setFixedSize(22, 22)
        self._toggle_btn.setToolTip("展开通道面板")
        self._toggle_btn.clicked.connect(self._on_toggle_clicked)
        header_layout.addWidget(self._toggle_btn)

        self._header_label = QLabel("通道")
        self._header_label.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(self._header_label)
        header_layout.addStretch()

        self._main_layout.addWidget(self._header)

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll_area.setFrameShape(QFrame.NoFrame)

        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(2, 2, 2, 2)
        self._content_layout.setSpacing(4)
        self._content_layout.addStretch()

        self._scroll_area.setWidget(self._content_widget)
        self._main_layout.addWidget(self._scroll_area, 1)

        self._tags_widget = QWidget()
        self._tags_layout = QVBoxLayout(self._tags_widget)
        self._tags_layout.setContentsMargins(2, 2, 2, 2)
        self._tags_layout.setSpacing(2)
        self._tags_layout.addStretch()
        self._main_layout.addWidget(self._tags_widget, 1)

        self._apply_collapsed_state()

    def _on_toggle_clicked(self):
        self.set_collapsed(not self._collapsed)

    def _apply_collapsed_state(self):
        if self._collapsed:
            self.setFixedWidth(self.COLLAPSED_WIDTH)
            self._toggle_btn.setText(">")
            self._toggle_btn.setToolTip("展开通道面板")
            self._scroll_area.hide()
            self._header_label.hide()
            self._tags_widget.show()
        else:
            self.setFixedWidth(self.EXPANDED_WIDTH)
            self._toggle_btn.setText("<")
            self._toggle_btn.setToolTip("折叠通道面板")
            self._scroll_area.show()
            self._header_label.show()
            self._tags_widget.hide()

    def _update_color_tags(self):
        while self._tags_layout.count() > 1:
            item = self._tags_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._color_tags.clear()

        for ch in sorted(self._cards.keys()):
            card = self._cards[ch]
            info = card.get_channel_info()
            color = info.get('color', '#00FF00')
            name = info.get('name', f'CH{ch}')

            tag = QLabel(name[:2])
            tag.setAlignment(Qt.AlignCenter)
            tag.setStyleSheet(
                f"background-color: {color}; color: #000; "
                f"font-size: 9px; font-weight: bold; "
                f"border-radius: 2px; padding: 1px;")
            tag.setFixedHeight(18)

            insert_pos = self._tags_layout.count() - 1
            self._tags_layout.insertWidget(insert_pos, tag)
            self._color_tags.append(tag)

    def add_channel_card(self, channel: int, info: dict = None) -> None:
        if channel in self._cards:
            return
        card = ChannelCard(channel)
        if info:
            card.set_channel_info(info)

        card.channel_enabled_changed.connect(self.channel_enabled_changed)
        card.channel_color_changed.connect(self.channel_color_changed)
        card.channel_style_changed.connect(self.channel_style_changed)
        card.channel_vdiv_changed.connect(self.channel_vdiv_changed)
        card.channel_yoffset_changed.connect(self.channel_yoffset_changed)
        card.channel_name_changed.connect(self.channel_name_changed)

        self._cards[channel] = card

        insert_pos = self._content_layout.count() - 1
        self._content_layout.insertWidget(insert_pos, card)
        self._update_color_tags()

    def remove_channel_card(self, channel: int) -> None:
        card = self._cards.pop(channel, None)
        if card is not None:
            self._content_layout.removeWidget(card)
            card.deleteLater()
            self._update_color_tags()

    def set_channel_enabled(self, channel: int, enabled: bool) -> None:
        card = self._cards.get(channel)
        if card:
            card.set_channel_info({'enabled': enabled})

    def set_channel_active(self, channel: int, active: bool) -> None:
        card = self._cards.get(channel)
        if card:
            card.set_active(active)

    def is_collapsed(self) -> bool:
        return self._collapsed

    def set_collapsed(self, collapsed: bool) -> None:
        if collapsed == self._collapsed:
            return
        self._collapsed = collapsed
        self._apply_collapsed_state()
        self.panel_collapsed.emit(collapsed)

    def get_all_channels_info(self) -> dict:
        result = {}
        for ch, card in self._cards.items():
            result[ch] = card.get_channel_info()
        return result

    def sizeHint(self) -> QSize:
        w = self.COLLAPSED_WIDTH if self._collapsed else self.EXPANDED_WIDTH
        return QSize(w, super().sizeHint().height())
