import struct
import logging

from PyQt5.QtCore import QObject, QTimer, pyqtSignal

from .jscope_parser import parse_packet
from .waveform_processor import DataFormat, FORMAT_DETAIL_MAP


logger = logging.getLogger(__name__)


class HighSpeedWaveformProcessor(QObject):
    """高速示波器处理器，运行在 Worker Thread。

    职责：
    - 接收原始 RTT 字节，解析为数值+时间戳
    - 在大型环形缓冲区中存储（默认 1M 样本）
    - 30FPS 定时降采样 → 发射到 GUI 线程
    """

    TYPE_MAP = {
        0x01: ('b', 1),
        0x02: ('B', 1),
        0x03: ('h', 2),
        0x04: ('H', 2),
        0x05: ('i', 4),
        0x06: ('I', 4),
        0x07: ('f', 4),
    }

    waveform_updated = pyqtSignal(int, list, list)

    def __init__(self, parent=None, buffer_size=1000000):
        super().__init__(parent)
        self._buffer_size = buffer_size
        self._max_display_points = 2000

        self._ts_buffers = {}
        self._val_buffers = {}
        self._write_pos = {}
        self._wrap_count = {}
        self._total_count = {}

        self._jscope_fields = None
        self._jscope_packet_size = 0
        self._data_format = DataFormat.AUTO
        self._sampling_interval = 0

        self._supports_hw_timestamps = False

        self._decimate_timer = QTimer(self)
        self._decimate_timer.setInterval(33)
        self._decimate_timer.timeout.connect(self._on_decimate_tick)

    def _init_channel(self, channel):
        self._ts_buffers[channel] = [0.0] * self._buffer_size
        self._val_buffers[channel] = [0.0] * self._buffer_size
        self._write_pos[channel] = 0
        self._wrap_count[channel] = 0
        self._total_count[channel] = 0

    def process_data(self, channel: int, data: bytes) -> None:
        if channel not in self._ts_buffers:
            self._init_channel(channel)

        values, hw_timestamps = self._parse(data)
        if not values:
            return

        use_hw = len(hw_timestamps) == len(values) and any(t is not None for t in hw_timestamps)

        ts_buf = self._ts_buffers[channel]
        val_buf = self._val_buffers[channel]
        wp = self._write_pos[channel]
        idx_start = self._total_count[channel]
        est_dt = 0.001 if self._sampling_interval <= 0 else self._sampling_interval

        for i, v in enumerate(values):
            if use_hw and hw_timestamps[i] is not None:
                ts = hw_timestamps[i] * 1e-6
            else:
                ts = (idx_start + i) * est_dt

            val_buf[wp] = float(v)
            ts_buf[wp] = ts
            wp = (wp + 1) % self._buffer_size
            if wp == 0:
                self._wrap_count[channel] += 1

        self._write_pos[channel] = wp
        self._total_count[channel] += len(values)

    def _parse(self, data: bytes) -> tuple:
        if self._jscope_fields is not None:
            return self._parse_jscope(data)
        if self._data_format == DataFormat.AUTO:
            return self._parse_auto(data)
        return self._parse_fixed(data)

    def _parse_auto(self, data: bytes) -> tuple:
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
        return (values, [])

    def _parse_fixed(self, data: bytes) -> tuple:
        values = []
        detail = FORMAT_DETAIL_MAP.get(self._data_format)
        if detail is None:
            return (values, [])
        fmt, size = detail
        i = 0
        while i + size <= len(data):
            try:
                value = struct.unpack_from(f'<{fmt}', data, i)[0]
                values.append(value)
                i += size
            except struct.error:
                i += 1
        return (values, [])

    def _parse_jscope(self, data: bytes) -> tuple:
        values = []
        timestamps = []
        pkt_size = self._jscope_packet_size
        if pkt_size <= 0:
            return (values, timestamps)
        i = 0
        while i + pkt_size <= len(data):
            result = parse_packet(data, self._jscope_fields, i)
            if result is None:
                i += 1
                continue
            ts = result['timestamp']
            for v in result['values']:
                values.append(v)
                timestamps.append(ts)
            i += pkt_size
        return (values, timestamps)

    def _on_decimate_tick(self):
        for ch in list(self._ts_buffers.keys()):
            timestamps, values = self._read_ring_buffer(ch)
            if len(timestamps) < 2:
                continue
            if len(timestamps) > self._max_display_points:
                timestamps, values = self._decimate_peak(timestamps, values)
            self.waveform_updated.emit(ch, timestamps, values)

    def _read_ring_buffer(self, channel):
        wp = self._write_pos[channel]
        wrapped = self._wrap_count[channel]
        total = self._total_count[channel]
        buf_size = self._buffer_size

        if total == 0:
            return ([], [])

        if wrapped == 0:
            timestamps = self._ts_buffers[channel][:wp]
            values = self._val_buffers[channel][:wp]
        else:
            timestamps = self._ts_buffers[channel][wp:] + self._ts_buffers[channel][:wp]
            values = self._val_buffers[channel][wp:] + self._val_buffers[channel][:wp]

        return (timestamps, values)

    def _decimate_peak(self, timestamps, values):
        n = len(timestamps)
        target = self._max_display_points
        bin_size = max(2, n // (target // 2))

        result_ts = []
        result_val = []

        i = 0
        while i < n:
            end = min(i + bin_size, n)
            chunk = values[i:end]
            if not chunk:
                break
            min_idx = i + chunk.index(min(chunk))
            max_idx = i + chunk.index(max(chunk))
            result_ts.append(timestamps[min_idx])
            result_val.append(values[min_idx])
            if max_idx != min_idx:
                result_ts.append(timestamps[max_idx])
                result_val.append(values[max_idx])
            i = end

        return (result_ts, result_val)

    def set_jscope_format(self, channel_name: str) -> bool:
        from .jscope_parser import parse_channel_name, calc_packet_size
        fields = parse_channel_name(channel_name)
        if not fields:
            self._jscope_fields = None
            self._jscope_packet_size = 0
            return False
        self._jscope_fields = fields
        self._jscope_packet_size = calc_packet_size(fields)
        self._supports_hw_timestamps = any(f.get('is_timestamp') for f in fields)
        return True

    def set_data_format(self, fmt: DataFormat) -> None:
        self._data_format = fmt

    def set_sampling_rate(self, rate_hz: float) -> None:
        if rate_hz > 0:
            self._sampling_interval = 1.0 / rate_hz
        else:
            self._sampling_interval = 0

    def start(self):
        self._decimate_timer.start()

    def stop(self):
        self._decimate_timer.stop()

    def reset(self):
        for ch in list(self._ts_buffers.keys()):
            self._init_channel(ch)
