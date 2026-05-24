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
    frequency_updated = pyqtSignal(int, float)

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
        self._channel_jscope_fields = {}
        self._channel_data_format = {}
        self._residual_buffers = {}
        self._sampling_interval = 0
        self._hw_ts_origins = {}

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
        self._residual_buffers[channel] = b''

    def process_data(self, channel: int, data: bytes) -> None:
        if channel not in self._ts_buffers:
            self._init_channel(channel)

        values, hw_timestamps = self._parse_channel(channel, data)
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
                if channel not in self._hw_ts_origins:
                    self._hw_ts_origins[channel] = hw_timestamps[i] * 1e-6
                ts = hw_timestamps[i] * 1e-6 - self._hw_ts_origins[channel]
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

    def _parse_channel(self, channel: int, data: bytes) -> tuple:
        ch_fields = self._channel_jscope_fields.get(channel)
        if ch_fields:
            return self._parse_channel_jscope(channel, data, ch_fields)
        return self._parse(data)

    def _parse_channel_jscope(self, channel: int, data: bytes, fields: list) -> tuple:
        values = []
        timestamps = []
        pkt_size = sum(f['size'] for f in fields)
        if pkt_size <= 0:
            return (values, timestamps)

        residual = self._residual_buffers.get(channel, b'')
        if residual:
            if len(residual) >= pkt_size:
                logger.warning(
                    f"CH{channel} 残缺缓冲区异常: len={len(residual)} >= pkt_size={pkt_size}, 清空重置")
                residual = b''
                self._residual_buffers[channel] = b''
            aligned_data = residual + data
            logger.debug(
                f"CH{channel} 拼接残缺: residual={len(residual)}B + new={len(data)}B -> aligned={len(aligned_data)}B")
        else:
            aligned_data = data

        if len(aligned_data) < pkt_size:
            self._residual_buffers[channel] = aligned_data
            logger.debug(f"CH{channel} 数据不足一个包: {len(aligned_data)}B < {pkt_size}B, 存入残缺缓冲区")
            return (values, timestamps)

        i = 0
        while i + pkt_size <= len(aligned_data):
            result = parse_packet(aligned_data, fields, i)
            if result is None:
                i += 1
                continue
            ts = result['timestamp']
            for v in result['values']:
                values.append(v)
                timestamps.append(ts)
            i += pkt_size

        tail_len = len(aligned_data) - i
        if tail_len > 0:
            self._residual_buffers[channel] = aligned_data[i:]
            logger.debug(f"CH{channel} 保存残缺: {tail_len}B")
        else:
            self._residual_buffers[channel] = b''

        return (values, timestamps)

    def set_channel_jscope_format(self, channel: int, channel_name: str) -> None:
        from .jscope_parser import parse_channel_name
        fields = parse_channel_name(channel_name)
        if fields:
            self._channel_jscope_fields[channel] = fields
            self._residual_buffers.pop(channel, None)

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

            freq = self._calculate_frequency(timestamps, values)

            if len(timestamps) > self._max_display_points:
                timestamps, values = self._decimate_peak(timestamps, values)
            self.waveform_updated.emit(ch, timestamps, values)

            if freq is not None and freq > 0:
                self.frequency_updated.emit(ch, freq)

    def _calculate_frequency(self, timestamps, values):
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
        if avg_period <= 0:
            return None
        return 1.0 / avg_period

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
        self._hw_ts_origins = {}
        self._residual_buffers.clear()
