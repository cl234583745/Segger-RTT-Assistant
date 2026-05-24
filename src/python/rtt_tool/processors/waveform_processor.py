import struct
import logging
from collections import deque
from enum import Enum, unique

from PyQt5.QtCore import pyqtSignal

from .base import DataProcessor
from .jscope_parser import parse_channel_name, parse_packet, calc_packet_size, format_display_text, AUTO_TYPE_MAP


logger = logging.getLogger(__name__)


@unique
class AcquisitionState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"


@unique
class DataFormat(Enum):
    AUTO = "auto"
    INT8 = "int8"
    UINT8 = "uint8"
    INT16 = "int16"
    UINT16 = "uint16"
    INT32 = "int32"
    UINT32 = "uint32"
    FLOAT = "float"


FORMAT_DISPLAY_MAP = {
    DataFormat.AUTO: "自动识别",
    DataFormat.INT8: "int8 (1字节)",
    DataFormat.UINT8: "uint8 (1字节)",
    DataFormat.INT16: "int16 (2字节)",
    DataFormat.UINT16: "uint16 (2字节)",
    DataFormat.INT32: "int32 (4字节)",
    DataFormat.UINT32: "uint32 (4字节)",
    DataFormat.FLOAT: "float (4字节)",
}

FORMAT_DETAIL_MAP = {
    DataFormat.INT8: ('b', 1),
    DataFormat.UINT8: ('B', 1),
    DataFormat.INT16: ('h', 2),
    DataFormat.UINT16: ('H', 2),
    DataFormat.INT32: ('i', 4),
    DataFormat.UINT32: ('I', 4),
    DataFormat.FLOAT: ('f', 4),
}


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

    def __init__(self, buffer_size=1024, channels=None, data_log_handle=None, parent=None):
        super().__init__(parent)
        self._buffer_size = buffer_size
        self._channels = channels if channels is not None else list(range(1, 11))
        self._channel_buffers = {}
        self._channel_timestamps = {}
        self._channel_sample_counters = {}
        self._time_origin = None
        self._hw_ts_origins = {}
        self._channel_jscope_fields = {}
        self._channel_jscope_packet_size = {}
        self._channel_data_format = {}
        self._residual_buffers = {}
        self._data_format = DataFormat.AUTO
        self._jscope_fields = None
        self._jscope_packet_size = 0
        self._jscope_format_text = "自动识别"
        self._sampling_interval = 0
        self._data_log_handle = data_log_handle
        self._channel_log_handles = {}
        self._log_state = {}
        for ch in self._channels:
            self._init_channel(ch)

    def _init_channel(self, channel):
        self._channel_buffers[channel] = deque(maxlen=self._buffer_size)
        self._channel_timestamps[channel] = deque(maxlen=self._buffer_size)
        self._channel_sample_counters[channel] = 0
        self._residual_buffers[channel] = b''

    def process(self, channel: int, data: bytes) -> None:
        if channel not in self._channels:
            self.add_channel(channel)

        if channel not in self._channel_buffers:
            self._init_channel(channel)

        log_handle = self._channel_log_handles.get(channel) or self._data_log_handle
        if log_handle is not None:
            try:
                from datetime import datetime
                now_time = datetime.now()
                
                # 检查是否需要写开始/结束标记
                if channel not in self._log_state:
                    # 首次接收，写开始标记
                    self._log_state[channel] = {
                        'start_time': now_time,
                        'last_time': now_time,
                        'count': 0
                    }
                    timestamp = now_time.strftime("[%Y-%m-%d %H:%M:%S.%f")[:-3] + "]"
                    log_handle.write(f"\n{timestamp} [CH{channel}] [开始接收]\n")
                
                # 检查是否超过100ms未接收，写结束/开始标记
                time_diff = (now_time - self._log_state[channel]['last_time']).total_seconds()
                if time_diff > 0.1 and self._log_state[channel]['count'] > 0:
                    last_ts = self._log_state[channel]['last_time'].strftime("[%Y-%m-%d %H:%M:%S.%f")[:-3] + "]"
                    log_handle.write(f"{last_ts} [CH{channel}] [结束] 共{self._log_state[channel]['count']}字节\n")
                    timestamp = now_time.strftime("[%Y-%m-%d %H:%M:%S.%f")[:-3] + "]"
                    log_handle.write(f"\n{timestamp} [CH{channel}] [继续接收]\n")
                    self._log_state[channel]['count'] = 0
                
                # 写数据（只写十六进制）
                hex_str = ' '.join(f'{b:02X}' for b in data)
                log_handle.write(f"{hex_str}\n")
                log_handle.flush()
                
                # 更新状态
                self._log_state[channel]['last_time'] = now_time
                self._log_state[channel]['count'] += len(data)
            except Exception:
                pass

        values, hw_timestamps = self._parse_channel(channel, data)
        
        if not values:
            import logging
            logging.getLogger(__name__).warning(
                f"CH{channel} parse EMPTY! jscope={self._channel_jscope_fields.get(channel)}, "
                f"fmt={self._data_format}, raw_hex={data[:8].hex() if len(data)>=8 else data.hex()}")
            return
        
        use_hw_ts = len(hw_timestamps) == len(values) and any(t is not None for t in hw_timestamps)

        if channel not in self._channel_sample_counters:
            self._channel_sample_counters[channel] = 0

        if use_hw_ts:
            if channel not in self._hw_ts_origins:
                self._hw_ts_origins[channel] = hw_timestamps[0] * 1e-6
            for i, v in enumerate(values):
                self._channel_buffers[channel].append(v)
                ts = hw_timestamps[i] * 1e-6 - self._hw_ts_origins[channel] if hw_timestamps[i] is not None else 0.0
                self._channel_timestamps[channel].append(ts)
        else:
            est_dt = 0.001 if self._sampling_interval <= 0 else self._sampling_interval
            idx_start = self._channel_sample_counters[channel]
            for i, v in enumerate(values):
                self._channel_buffers[channel].append(v)
                self._channel_timestamps[channel].append((idx_start + i) * est_dt)
            self._channel_sample_counters[channel] += len(values)

        self.waveform_updated.emit(channel, values)
        self.data_updated.emit((channel, values))

    def process_batch(self, poll_time: float, batch: list) -> None:
        """批量处理同一poll时刻的多通道数据，共享时间基准。
        
        Args:
            poll_time: perf_counter()时刻，本批所有通道共享
            batch: [(channel, data_bytes), ...]
        """
        import time
        if self._time_origin is None:
            self._time_origin = poll_time

        poll_offset = poll_time - self._time_origin
        est_dt = 0.001 if self._sampling_interval <= 0 else self._sampling_interval
        t0 = time.perf_counter()

        for channel, data in batch:
            if channel not in self._channels:
                self.add_channel(channel)
            if channel not in self._channel_buffers:
                self._init_channel(channel)

            log_handle = self._channel_log_handles.get(channel) or self._data_log_handle
            if log_handle is not None:
                try:
                    from datetime import datetime
                    now_time = datetime.now()
                    if channel not in self._log_state:
                        self._log_state[channel] = {
                            'start_time': now_time,
                            'last_time': now_time,
                            'count': 0
                        }
                        timestamp = now_time.strftime("[%Y-%m-%d %H:%M:%S.%f")[:-3] + "]"
                        log_handle.write(f"\n{timestamp} [CH{channel}] [开始接收]\n")
                    time_diff = (now_time - self._log_state[channel]['last_time']).total_seconds()
                    if time_diff > 0.1 and self._log_state[channel]['count'] > 0:
                        last_ts = self._log_state[channel]['last_time'].strftime("[%Y-%m-%d %H:%M:%S.%f")[:-3] + "]"
                        log_handle.write(f"{last_ts} [CH{channel}] [结束] 共{self._log_state[channel]['count']}字节\n")
                        timestamp = now_time.strftime("[%Y-%m-%d %H:%M:%S.%f")[:-3] + "]"
                        log_handle.write(f"\n{timestamp} [CH{channel}] [继续接收]\n")
                        self._log_state[channel]['count'] = 0
                    hex_str = ' '.join(f'{b:02X}' for b in data)
                    log_handle.write(f"{hex_str}\n")
                    log_handle.flush()
                    self._log_state[channel]['last_time'] = now_time
                    self._log_state[channel]['count'] += len(data)
                except Exception:
                    pass

            values, hw_timestamps = self._parse_channel(channel, data)
            if not values:
                continue

            if channel not in self._channel_sample_counters:
                self._channel_sample_counters[channel] = 0

            use_hw_ts = len(hw_timestamps) == len(values) and any(t is not None for t in hw_timestamps)

            if use_hw_ts:
                if channel not in self._hw_ts_origins:
                    self._hw_ts_origins[channel] = hw_timestamps[0] * 1e-6
                for i, v in enumerate(values):
                    self._channel_buffers[channel].append(v)
                    ts = hw_timestamps[i] * 1e-6 - self._hw_ts_origins[channel] if hw_timestamps[i] is not None else 0.0
                    self._channel_timestamps[channel].append(ts)
            else:
                idx_start = self._channel_sample_counters[channel]
                for i, v in enumerate(values):
                    self._channel_buffers[channel].append(v)
                    self._channel_timestamps[channel].append((idx_start + i) * est_dt)
                self._channel_sample_counters[channel] += len(values)

            self.waveform_updated.emit(channel, values)
            self.data_updated.emit((channel, values))

        elapsed = (time.perf_counter() - t0) * 1000
        if not hasattr(self, '_batch_log_counter'):
            self._batch_log_counter = 0
        self._batch_log_counter += 1
        if self._batch_log_counter <= 5 or self._batch_log_counter % 100 == 0:
            ch_summary = ', '.join(f'CH{ch}:len={len(self._channel_buffers.get(ch, []))}' for ch, _ in batch)
            import logging
            logging.getLogger(__name__).info(
                f"[batch] #{self._batch_log_counter} poll_offset={poll_offset:.4f}s "
                f"est_dt={est_dt*1000:.2f}ms elapsed={elapsed:.1f}ms {ch_summary}")

    def _parse(self, data: bytes) -> tuple:
        """返回 (values, timestamps)。timestamps 为空列表表示无硬件时间戳。"""
        if self._jscope_fields is not None:
            return self._parse_jscope(data)
        if self._data_format == DataFormat.AUTO:
            return self._parse_auto(data)
        return self._parse_fixed(data)

    def _parse_channel(self, channel: int, data: bytes) -> tuple:
        ch_fields = self._channel_jscope_fields.get(channel)
        if ch_fields:
            return self._parse_channel_jscope(channel, data, ch_fields)
        ch_fmt = self._channel_data_format.get(channel)
        if ch_fmt and ch_fmt != DataFormat.AUTO:
            return self._parse_channel_fixed(data, ch_fmt)
        if self._jscope_fields is not None:
            return self._parse_jscope(data)
        if self._data_format != DataFormat.AUTO:
            return self._parse_fixed(data)
        return self._parse_auto(data)

    def _parse_channel_jscope(self, channel: int, data: bytes, fields: list) -> tuple:
        values = []
        hw_timestamps = []
        packet_size = sum(f['size'] for f in fields)
        if packet_size <= 0:
            return ([], [])

        residual = self._residual_buffers.get(channel, b'')
        if residual:
            if len(residual) >= packet_size:
                logger.warning(
                    f"CH{channel} 残缺缓冲区异常: len={len(residual)} >= packet_size={packet_size}, 清空重置")
                residual = b''
                self._residual_buffers[channel] = b''
            aligned_data = residual + data
            logger.debug(
                f"CH{channel} 拼接残缺: residual={len(residual)}B + new={len(data)}B -> aligned={len(aligned_data)}B")
        else:
            aligned_data = data

        if len(aligned_data) < packet_size:
            self._residual_buffers[channel] = aligned_data
            logger.debug(f"CH{channel} 数据不足一个包: {len(aligned_data)}B < {packet_size}B, 存入残缺缓冲区")
            return ([], [])

        i = 0
        while i + packet_size <= len(aligned_data):
            result = parse_packet(aligned_data, fields, offset=i)
            if result is None:
                break
            if result['timestamp'] is not None:
                hw_timestamps.append(result['timestamp'])
            values.extend(result['values'])
            i += packet_size

        tail_len = len(aligned_data) - i
        if tail_len > 0:
            self._residual_buffers[channel] = aligned_data[i:]
            logger.debug(f"CH{channel} 保存残缺: {tail_len}B")
        else:
            self._residual_buffers[channel] = b''

        return (values, hw_timestamps)

    def _parse_channel_fixed(self, data: bytes, fmt: DataFormat) -> tuple:
        detail = FORMAT_DETAIL_MAP.get(fmt)
        if detail is None:
            return ([], [])
        struct_fmt, size = detail
        values = []
        i = 0
        while i + size <= len(data):
            try:
                value = struct.unpack_from(f'<{struct_fmt}', data, i)[0]
                values.append(value)
                i += size
            except struct.error:
                break
        return (values, [])

    def set_channel_jscope_format(self, channel: int, channel_name: str) -> None:
        fields = parse_channel_name(channel_name)
        if fields:
            self._channel_jscope_fields[channel] = fields
            self._channel_jscope_packet_size[channel] = calc_packet_size(fields)
            self._channel_data_format[channel] = DataFormat.AUTO
            self._residual_buffers.pop(channel, None)

    def set_channel_log_handle(self, channel: int, log_handle) -> None:
        self._channel_log_handles[channel] = log_handle

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
                logger.warning("示波器: 固定格式解析异常, 跳过1字节")
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

    def set_jscope_format(self, channel_name: str) -> bool:
        """根据RTT通道名设置JScope格式。返回是否成功解析为JScope格式。"""
        fields = parse_channel_name(channel_name)
        if not fields:
            self._jscope_fields = None
            self._jscope_packet_size = 0
            self._jscope_format_text = "自动识别"
            return False
        self._jscope_fields = fields
        self._jscope_packet_size = calc_packet_size(fields)
        self._jscope_format_text = format_display_text(fields)
        logger.info(f"示波器: JScope格式 '{channel_name}' -> {self._jscope_format_text}, 包大小={self._jscope_packet_size}字节")
        return True

    def get_format_text(self) -> str:
        """获取当前格式的显示文本"""
        if self._jscope_fields is not None:
            return self._jscope_format_text
        if self._data_format == DataFormat.AUTO:
            return "自动识别"
        return FORMAT_DISPLAY_MAP.get(self._data_format, self._data_format.value)

    def set_data_format(self, fmt: DataFormat) -> None:
        self._data_format = fmt
        logger.info(f"示波器: 数据格式切换为 {fmt.value}")

    def set_sampling_rate(self, rate_hz: float) -> None:
        """设置采样率(Hz)。0表示自动估算。"""
        if rate_hz > 0:
            self._sampling_interval = 1.0 / rate_hz
            logger.info(f"示波器: 采样率设为 {rate_hz:.1f} Hz (间隔={self._sampling_interval*1e6:.1f}µs)")
        else:
            self._sampling_interval = 0
            logger.info("示波器: 采样率设为自动估算")

    def get_data_format(self) -> DataFormat:
        return self._data_format

    def get_supported_channels(self) -> list:
        return list(self._channels)

    def get_buffer_data(self, channel: int):
        if channel not in self._channel_buffers:
            return ([], [])
        ts_list = list(self._channel_timestamps[channel])
        val_list = list(self._channel_buffers[channel])
        n = min(len(ts_list), len(val_list))
        if n < len(ts_list) or n < len(val_list):
            ts_list = ts_list[:n]
            val_list = val_list[:n]
        return (ts_list, val_list)

    def add_channel(self, channel: int):
        if channel not in self._channels:
            self._channels.append(channel)
            self._init_channel(channel)

    def remove_channel(self, channel: int):
        if channel in self._channels:
            self._channels.remove(channel)
        self._channel_buffers.pop(channel, None)
        self._channel_timestamps.pop(channel, None)
        self._residual_buffers.pop(channel, None)

    def reset(self) -> None:
        for ch in self._channels:
            self._channel_buffers[ch].clear()
            self._channel_timestamps[ch].clear()
            self._channel_sample_counters[ch] = 0
        self._time_origin = None
        self._hw_ts_origins = {}
        self._residual_buffers.clear()
        # 写结束标记并清除日志状态
        if self._data_log_handle is not None:
            try:
                from datetime import datetime
                for ch, state in self._log_state.items():
                    if state['count'] > 0:
                        last_ts = state['last_time'].strftime("[%Y-%m-%d %H:%M:%S.%f")[:-3] + "]"
                        self._data_log_handle.write(f"{last_ts} [CH{ch}] [结束] 共{state['count']}字节\n")
            except Exception:
                pass
        self._log_state.clear()

    def set_data_log_handle(self, handle):
        self._data_log_handle = handle
