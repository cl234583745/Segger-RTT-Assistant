import struct
from collections import deque
import time

from PyQt5.QtCore import pyqtSignal

from .base import DataProcessor


class WaveformProcessor(DataProcessor):
    """二进制波形数据处理器，解析 <type_byte><value_bytes> 格式。"""

    waveform_updated = pyqtSignal(int, list)

    TYPE_MAP = {
        0x01: ('b', 1),
        0x02: ('B', 1),
        0x03: ('h', 2),
        0x04: ('H', 2),
        0x05: ('i', 4),
        0x06: ('I', 4),
        0x07: ('f', 4),
    }

    def __init__(self, buffer_size=1024, channels=None, parent=None):
        super().__init__(parent)
        self._buffer_size = buffer_size
        self._channels = channels if channels is not None else [1]
        self._channel_buffers = {}
        self._channel_timestamps = {}
        for ch in self._channels:
            self._init_channel(ch)

    def _init_channel(self, channel):
        self._channel_buffers[channel] = deque(maxlen=self._buffer_size)
        self._channel_timestamps[channel] = deque(maxlen=self._buffer_size)

    def process(self, channel: int, data: bytes) -> None:
        if channel not in self._channels:
            return

        if channel not in self._channel_buffers:
            self._init_channel(channel)

        values = self._parse(data)
        now = time.time()
        for v in values:
            self._channel_buffers[channel].append(v)
            self._channel_timestamps[channel].append(now)

        if values:
            self.waveform_updated.emit(channel, values)
            self.data_updated.emit((channel, values))

    def _parse(self, data: bytes) -> list:
        values = []
        i = 0
        while i < len(data):
            type_byte = data[i]
            i += 1
            type_info = self.TYPE_MAP.get(type_byte)
            if type_info is None:
                continue
            fmt, size = type_info
            if i + size > len(data):
                break
            try:
                value = struct.unpack_from(f'<{fmt}', data, i)[0]
                values.append(value)
                i += size
            except struct.error:
                break
        return values

    def get_supported_channels(self) -> list:
        return list(self._channels)

    def get_buffer_data(self, channel: int):
        """返回 (timestamps, values) 元组。"""
        if channel not in self._channel_buffers:
            return ([], [])
        return (list(self._channel_timestamps[channel]), list(self._channel_buffers[channel]))

    def add_channel(self, channel: int):
        if channel not in self._channels:
            self._channels.append(channel)
            self._init_channel(channel)

    def remove_channel(self, channel: int):
        if channel in self._channels:
            self._channels.remove(channel)
        self._channel_buffers.pop(channel, None)
        self._channel_timestamps.pop(channel, None)

    def reset(self) -> None:
        for ch in self._channels:
            self._channel_buffers[ch].clear()
            self._channel_timestamps[ch].clear()
