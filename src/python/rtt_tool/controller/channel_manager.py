import logging
from PyQt5.QtCore import QObject, pyqtSignal

from ..models.channel_config import ChannelConfig, ChannelRoute, AutoDetectState


class ChannelManager(QObject):

    MAX_CHANNELS = 10

    channel_added = pyqtSignal(int)
    channel_removed = pyqtSignal(int)
    channel_enabled_changed = pyqtSignal(int, bool)
    channel_color_changed = pyqtSignal(int, str)
    channel_style_changed = pyqtSignal(int, int)
    channel_vdiv_changed = pyqtSignal(int, float)
    channel_yoffset_changed = pyqtSignal(int, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_channels: set = set()
        self._enabled_channels: set = set()
        self._channel_configs: dict = {}
        self._auto_detect_state = AutoDetectState()
        self._logger = logging.getLogger(__name__)

    def add_channel(self, channel: int) -> None:
        if channel in self._active_channels:
            return
        if len(self._active_channels) >= self.MAX_CHANNELS:
            self._logger.warning(f"通道数已达上限({self.MAX_CHANNELS})，忽略添加 CH{channel}")
            return
        if channel < 1 or channel > self.MAX_CHANNELS:
            self._logger.warning(f"通道编号 {channel} 超出范围 [1, {self.MAX_CHANNELS}]")
            return
        self._active_channels.add(channel)
        self._enabled_channels.add(channel)
        self._channel_configs[channel] = ChannelConfig.default(channel)
        self.channel_added.emit(channel)

    def remove_channel(self, channel: int) -> None:
        if channel not in self._active_channels:
            return
        self._active_channels.discard(channel)
        self._enabled_channels.discard(channel)
        self._channel_configs.pop(channel, None)
        self._auto_detect_state.detection_counts.pop(
            ChannelRoute.display_to_rtt(channel), None)
        self.channel_removed.emit(channel)

    def set_channel_enabled(self, channel: int, enabled: bool) -> None:
        if channel not in self._active_channels:
            return
        if enabled:
            self._enabled_channels.add(channel)
        else:
            self._enabled_channels.discard(channel)
        config = self._channel_configs.get(channel)
        if config:
            config.enabled = enabled
        self.channel_enabled_changed.emit(channel, enabled)

    def set_channel_color(self, channel: int, color: str) -> None:
        config = self._channel_configs.get(channel)
        if config:
            config.color = color
            self.channel_color_changed.emit(channel, color)

    def set_channel_style(self, channel: int, style: int) -> None:
        config = self._channel_configs.get(channel)
        if config:
            config.style = style
            self.channel_style_changed.emit(channel, style)

    def set_channel_vdiv(self, channel: int, vdiv: float) -> None:
        if vdiv <= 0:
            return
        config = self._channel_configs.get(channel)
        if config:
            config.vdiv = vdiv
            self.channel_vdiv_changed.emit(channel, vdiv)

    def set_channel_yoffset(self, channel: int, yoffset: float) -> None:
        config = self._channel_configs.get(channel)
        if config:
            config.yoffset = yoffset
            self.channel_yoffset_changed.emit(channel, yoffset)

    def get_enabled_rtt_channels(self) -> list:
        result = []
        for ch in sorted(self._enabled_channels):
            rtt_ch = ChannelRoute.display_to_rtt(ch)
            if 1 <= rtt_ch <= self.MAX_CHANNELS:
                result.append(rtt_ch)
        return result

    def get_active_channels(self) -> set:
        return set(self._active_channels)

    def get_channel_config(self, channel: int) -> ChannelConfig:
        return self._channel_configs.get(channel)

    def get_all_configs(self) -> dict:
        return dict(self._channel_configs)

    def on_data_activity(self, rtt_channel: int) -> None:
        if not self._auto_detect_state.enabled:
            return
        if rtt_channel == 0:
            return
        display_ch = ChannelRoute.rtt_to_display(rtt_channel)
        if display_ch in self._active_channels:
            return
        if display_ch > self.MAX_CHANNELS:
            self._logger.warning(
                f"RTT通道{rtt_channel}超出上限，忽略自动检测")
            return
        counts = self._auto_detect_state.detection_counts
        counts[rtt_channel] = counts.get(rtt_channel, 0) + 1
        if counts[rtt_channel] >= self._auto_detect_state.threshold:
            counts.pop(rtt_channel, None)
            self.add_channel(display_ch)

    def set_auto_detect(self, enabled: bool) -> None:
        self._auto_detect_state.enabled = enabled

    def is_auto_detect_enabled(self) -> bool:
        return self._auto_detect_state.enabled

    def ensure_channel1(self) -> None:
        if 1 not in self._active_channels:
            self.add_channel(1)

    def ensure_all_channels(self) -> None:
        for ch in range(1, self.MAX_CHANNELS + 1):
            if ch not in self._active_channels:
                self.add_channel(ch)
