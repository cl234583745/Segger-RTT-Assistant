from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QScrollArea, QLabel, QSizePolicy, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize
from PyQt5.QtGui import QPixmap, QColor

from .channel_card import ChannelCard
from ..models.channel_config import DEFAULT_CHANNEL_COLORS
from ..i18n import _ as i18n, language_changed as i18n_language_changed


class ChannelPanel(QWidget):

    channel_enabled_changed = pyqtSignal(object, bool)
    channel_color_changed = pyqtSignal(object, str)
    channel_style_changed = pyqtSignal(object, int)
    channel_vdiv_changed = pyqtSignal(object, float)
    channel_yoffset_changed = pyqtSignal(object, float)
    channel_name_changed = pyqtSignal(object, str)

    panel_collapsed = pyqtSignal(bool)

    COLLAPSED_WIDTH = 40
    EXPANDED_WIDTH = 240

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards: dict = {}
        self._collapsed: bool = True
        self._color_tags: list = []
        self._init_ui()
        _sig = i18n_language_changed()
        if _sig:
            _sig.connect(self._refresh_on_language_changed)

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
        self._toggle_btn.setToolTip(i18n("tooltip.expand_panel"))
        self._toggle_btn.clicked.connect(self._on_toggle_clicked)
        header_layout.addWidget(self._toggle_btn)

        self._header_label = QLabel(i18n("label.channel"))
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
            self._toggle_btn.setToolTip(i18n("tooltip.expand_panel"))
            self._scroll_area.hide()
            self._header_label.hide()
            self._tags_widget.show()
        else:
            self.setFixedWidth(self.EXPANDED_WIDTH)
            self._toggle_btn.setText("<")
            self._toggle_btn.setToolTip(i18n("tooltip.collapse_panel"))
            self._scroll_area.show()
            self._header_label.show()
            self._tags_widget.hide()

    def _card_sort_key(self, ch):
        if isinstance(ch, int):
            return (ch, -1)
        return (ch[0], ch[1])

    def _get_ordered_keys(self):
        int_keys = sorted([k for k in self._cards.keys() if isinstance(k, int)])
        result = []
        for k in int_keys:
            result.append(k)
            sub_keys = sorted(
                [sk for sk in self._cards.keys() if isinstance(sk, tuple) and sk[0] == k],
                key=lambda x: x[1]
            )
            result.extend(sub_keys)
        return result

    def _find_insert_index_for_sub(self, parent_channel):
        for i in range(self._content_layout.count()):
            item = self._content_layout.itemAt(i)
            if item and item.widget():
                w = item.widget()
                if isinstance(w, ChannelCard):
                    ch = w._channel
                    if isinstance(ch, int) and ch == parent_channel:
                        j = i + 1
                        while j < self._content_layout.count():
                            sub_item = self._content_layout.itemAt(j)
                            if sub_item and sub_item.widget():
                                sub_w = sub_item.widget()
                                if isinstance(sub_w, ChannelCard):
                                    sub_ch = sub_w._channel
                                    if isinstance(sub_ch, tuple) and sub_ch[0] == parent_channel:
                                        j += 1
                                        continue
                                break
                            j += 1
                        return j
                    if isinstance(ch, int) and ch > parent_channel:
                        return i
                    if isinstance(ch, tuple) and ch[0] > parent_channel:
                        return i
        return self._content_layout.count() - 1

    def _update_color_tags(self):
        while self._tags_layout.count() > 1:
            item = self._tags_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._color_tags.clear()

        for ch in self._get_ordered_keys():
            card = self._cards[ch]
            info = card.get_channel_info()
            color = info.get('color', '#00FF00')
            is_active = info.get('enabled', False)
            if isinstance(ch, tuple):
                name = info.get('name', f'CH{ch[0]}-{ch[1]}')
            else:
                name = info.get('name', f'CH{ch}')

            tag = QLabel(name[:6] if isinstance(ch, tuple) else name[:3])
            tag.setAlignment(Qt.AlignCenter)
            opacity_style = "" if is_active else "opacity: 0.4;"
            if isinstance(ch, tuple):
                tag.setStyleSheet(
                    f"background-color: {color}; color: #000; "
                    f"font-size: 8px; font-weight: bold; "
                    f"border-radius: 2px; padding: 1px; "
                    f"margin-left: 8px; {opacity_style}")
            else:
                tag.setStyleSheet(
                    f"background-color: {color}; color: #000; "
                    f"font-size: 9px; font-weight: bold; "
                    f"border-radius: 2px; padding: 1px; {opacity_style}")
            tag.setFixedHeight(18)

            insert_pos = self._tags_layout.count() - 1
            self._tags_layout.insertWidget(insert_pos, tag)
            self._color_tags.append(tag)

    def add_channel_card(self, channel, info: dict = None) -> None:
        if channel in self._cards:
            return
        is_sub = isinstance(channel, tuple)
        card = ChannelCard(channel, is_sub_channel=is_sub)
        if info:
            card.set_channel_info(info)

        card.channel_enabled_changed.connect(self.channel_enabled_changed)
        card.channel_color_changed.connect(self.channel_color_changed)
        card.channel_style_changed.connect(self.channel_style_changed)
        card.channel_vdiv_changed.connect(self.channel_vdiv_changed)
        card.channel_yoffset_changed.connect(self.channel_yoffset_changed)
        card.channel_name_changed.connect(self.channel_name_changed)

        self._cards[channel] = card

        if is_sub:
            insert_pos = self._find_insert_index_for_sub(channel[0])
        else:
            insert_pos = self._content_layout.count() - 1
        self._content_layout.insertWidget(insert_pos, card)
        self._update_color_tags()

    def remove_channel_card(self, channel) -> None:
        card = self._cards.pop(channel, None)
        if card is not None:
            self._content_layout.removeWidget(card)
            card.deleteLater()
            self._update_color_tags()

    def set_channel_enabled(self, channel, enabled: bool) -> None:
        card = self._cards.get(channel)
        if card:
            card.set_channel_info({'enabled': enabled})
            self._update_color_tags()

    def set_channel_active(self, channel, active: bool) -> None:
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

    def _refresh_on_language_changed(self, lang):
        if hasattr(self, '_header_label'):
            self._header_label.setText(i18n("label.channel"))
        self._apply_collapsed_state()

    def sizeHint(self) -> QSize:
        w = self.COLLAPSED_WIDTH if self._collapsed else self.EXPANDED_WIDTH
        return QSize(w, super().sizeHint().height())
