import struct
import time

from .base import DebuggerBackend
from ..infrastructure.jlink_rtt_wrapper import JLinkRTTWrapper


class JLinkBackend(DebuggerBackend):
    """J-Link 调试器后端，适配器模式封装 JLinkRTTWrapper。"""

    _TYPE_MAP = {
        'uint8':  {'fmt': 'B', 'size': 1},
        'int8':   {'fmt': 'b', 'size': 1},
        'uint16': {'fmt': 'H', 'size': 2},
        'int16':  {'fmt': 'h', 'size': 2},
        'uint32': {'fmt': 'I', 'size': 4},
        'int32':  {'fmt': 'i', 'size': 4},
        'float':  {'fmt': 'f', 'size': 4},
    }

    _probe_cache = None
    _probe_cache_time = 0

    def __init__(self, jlink_path=None, log_service=None):
        self._jlink_path = jlink_path
        self._log_service = log_service
        self._wrapper = None

    def _ensure_wrapper(self):
        if self._wrapper is None:
            self._wrapper = JLinkRTTWrapper(
                jlink_path=self._jlink_path,
                log_service=self._log_service
            )

    def connect(self, device: str, interface: str = 'SWD', speed: int = 4000, **kwargs) -> bool:
        self._ensure_wrapper()
        serial_number = kwargs.get('serial_number')
        ip_address = kwargs.get('ip_address')
        return self._wrapper.connect(
            device=device,
            interface=interface,
            speed=speed,
            serial_number=serial_number,
            ip_address=ip_address
        )

    def disconnect(self) -> None:
        if self._wrapper is not None:
            self._wrapper.disconnect()
            self._wrapper = None

    def init_rtt(self, rtt_address: int = None, rtt_mode: str = 'auto',
                 range_start: int = None, range_end: int = None) -> bool:
        if self._wrapper is None:
            raise RuntimeError("J-Link 未连接")
        return self._wrapper.init_rtt(
            rtt_address=rtt_address,
            rtt_mode=rtt_mode,
            range_start=range_start,
            range_end=range_end
        )

    def rtt_read(self, channel: int = 0, buffer_size: int = 4096) -> bytes:
        if self._wrapper is None:
            raise RuntimeError("J-Link 未连接")
        return self._wrapper.read_rtt(buffer_size=buffer_size, channel=channel)

    def rtt_read_all(self, channels: list, buffer_size: int = 4096) -> dict:
        if self._wrapper is None:
            raise RuntimeError("J-Link 未连接")
        result = {}
        for channel in channels:
            try:
                result[channel] = self._wrapper.read_rtt(buffer_size=buffer_size, channel=channel)
            except Exception:
                result[channel] = b''
        return result

    def rtt_write(self, channel: int, data: bytes) -> int:
        if self._wrapper is None:
            raise RuntimeError("J-Link 未连接")
        return self._wrapper.write_rtt(data, channel=channel)

    def get_probe_list(self, force=False) -> list:
        now = time.time()
        if not force and JLinkBackend._probe_cache is not None and (now - JLinkBackend._probe_cache_time) < 5.0:
            return JLinkBackend._probe_cache
        probes = []
        try:
            import pylink
            jlink = pylink.JLink()
            num = jlink.num_connected_emulators()
            if num > 0:
                for i in range(num):
                    info = jlink.connected_emulators()[i]
                    serial = info.SerialNumber
                    name = f"J-Link (SN:{serial})"
                    probes.append({
                        'type': 'jlink',
                        'name': name,
                        'serial': str(serial),
                        'backend': 'jlink'
                    })
        except Exception:
            pass
        JLinkBackend._probe_cache = probes
        JLinkBackend._probe_cache_time = now
        return probes

    def read_memory(self, address: int, var_type: str = 'uint32') -> object:
        if self._wrapper is None or not self._wrapper.connected:
            raise RuntimeError("J-Link 未连接")
        type_info = self._TYPE_MAP.get(var_type)
        if type_info is None:
            raise ValueError(f"不支持的变量类型: {var_type}")
        try:
            raw = self._wrapper.jlink.memory_read(address, type_info['size'])
            raw_bytes = struct.pack(f'<{type_info["size"]}I', *raw) if type_info['size'] <= 4 else bytes(raw)
            return struct.unpack(f'<{type_info["fmt"]}', raw_bytes[:type_info['size']])[0]
        except Exception as e:
            raise RuntimeError(f"读取内存失败 (地址=0x{address:08X}, 类型={var_type}): {e}")

    @property
    def is_connected(self) -> bool:
        return self._wrapper is not None and self._wrapper.connected

    @property
    def backend_type(self) -> str:
        return "jlink"

    def get_wrapper(self) -> JLinkRTTWrapper:
        """返回底层 JLinkRTTWrapper 引用（向后兼容）。"""
        return self._wrapper
