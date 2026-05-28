import os
import struct
import sys
import time

from .base import DebuggerBackend
from ..runtime.path_config import (
    RUNTIME_DLL_DIR, RUNTIME_PACKS_DIR, find_libusb_dll, inject_dll_path,
)


class _SuppressPyocdStderr:
    """临时抑制pyocd打印到stderr的非关键噪音"""

    _SUPPRESS_PATTERNS = (
        'Invalid coresight component',
        'Error attempting to create component',
        'Not a genuine ST Device',
        'Error during DAP processing',
    )

    def __enter__(self):
        self._original = sys.stderr
        sys.stderr = self
        return self

    def __exit__(self, *args):
        sys.stderr = self._original

    def write(self, text):
        if self._original is None:
            return
        for p in self._SUPPRESS_PATTERNS:
            if p in text:
                return
        self._original.write(text)

    def flush(self):
        if self._original is None:
            return
        self._original.flush()


class PyOCDBackend(DebuggerBackend):
    """PyOCD 调试器后端，支持 DAP-Link / ST-Link 等探针，使用 PyOCD 内置 RTT。"""

    _TYPE_SIZE_MAP = {
        'uint8': 1, 'int8': 1,
        'uint16': 2, 'int16': 2,
        'uint32': 4, 'int32': 4,
        'float': 4,
    }

    _TYPE_FMT_MAP = {
        'uint8': 'B', 'int8': 'b',
        'uint16': 'H', 'int16': 'h',
        'uint32': 'I', 'int32': 'i',
        'float': 'f',
    }

    def __init__(self, log_service=None):
        self._log_service = log_service
        self._session = None
        self._board = None
        self._target = None
        self._rtt_cb = None
        self._rtt_initialized = False
        self._pyocd_available = self._check_pyocd()
        self._probe_cache = None
        self._probe_cache_time = 0
        self._diag_counter = 0

    def _check_pyocd(self) -> bool:
        try:
            self._ensure_libusb_path()
            import pyocd
            self._diag_log(f'_check_pyocd: OK, pyocd={pyocd.__version__}')
            return True
        except ImportError as e:
            self._diag_log(f'_check_pyocd: FAIL import error: {e}')
            return False
        except Exception as e:
            self._diag_log(f'_check_pyocd: FAIL {type(e).__name__}: {e}')
            return False

    def _ensure_libusb_path(self):
        try:
            inject_dll_path()
            dll_path = find_libusb_dll()
            if dll_path:
                dll_dir = os.path.dirname(dll_path)
                if dll_dir not in os.environ.get('PATH', '').split(os.pathsep):
                    os.environ['PATH'] = dll_dir + os.pathsep + os.environ.get('PATH', '')
                self._diag_log(f'libusb dll: {dll_path}')
            else:
                self._diag_log('libusb dll not found in runtime')
        except Exception as e:
            self._diag_log(f'_ensure_libusb_path error: {e}')

    _diag_handler = None

    def _diag_log(self, msg):
        try:
            from ..runtime.path_config import RUNTIME_LOG_DIR
            import os, logging.handlers
            os.makedirs(RUNTIME_LOG_DIR, exist_ok=True)
            log_file = os.path.join(RUNTIME_LOG_DIR, 'pyocd_diag.log')
            if PyOCDBackend._diag_handler is None:
                PyOCDBackend._diag_handler = logging.handlers.RotatingFileHandler(
                    log_file, maxBytes=5*1024*1024, backupCount=2, encoding='utf-8')
            from datetime import datetime
            PyOCDBackend._diag_handler.stream.write(f'{datetime.now().strftime("%H:%M:%S")} {msg}\n')
            PyOCDBackend._diag_handler.stream.flush()
        except Exception:
            pass

    @staticmethod
    def _subprocess_flags():
        import subprocess
        return getattr(subprocess, 'CREATE_NO_WINDOW', 0)

    def _log(self, level, msg):
        if self._log_service:
            getattr(self._log_service, level)(msg)

    def connect(self, device: str, interface: str = 'SWD', speed: int = 4000, **kwargs) -> bool:
        self._ensure_libusb_path()
        probe_serial = kwargs.get('serial_number')
        connect_mode = kwargs.get('connect_mode', 'under_reset')

        _CONNECT_MODE_MAP = {
            'under_reset': 'under-reset',
            'halt_on_connect': 'halt',
            'pre_reset': 'pre-reset',
            'default': 'halt',
            'under-reset': 'under-reset',
            'halt': 'halt',
            'attach': 'attach',
        }
        pyocd_connect_mode = _CONNECT_MODE_MAP.get(connect_mode, 'under-reset')
        pyocd_target = kwargs.get('pyocd_target')

        if pyocd_target:
            target = pyocd_target
        elif device and not device.startswith('Cortex-M'):
            self._log('warning', f'未指定 PyOCD 目标，使用 J-Link 设备名 "{device}" 作为回退，可能无法识别')
            target = device
        else:
            raise RuntimeError('PyOCD 连接需要指定目标芯片型号（如 STM32U575）')

        resolved, use_override = self._resolve_target(target)
        if resolved != target:
            if use_override:
                self._log('info', f'目标名 "{target}" 解析为 "{resolved}"')
                target = resolved
            else:
                self._log('info', f'目标 "{target}" 匹配到多个具体型号，由探针自动识别芯片')
                use_override = False
        elif not use_override:
            self._log('info', f'目标 "{target}" 为系列名，由探针自动识别芯片')

        if not self._pyocd_available:
            raise RuntimeError('PyOCD 不可用，无法连接')

        try:
            from ..utils.resource_utils import sync_pyocd_yaml
            sync_pyocd_yaml()
        except Exception:
            pass

        try:
            import os
            os.environ['PYUSB_BACKEND'] = 'libusb1'
            os.environ['PYOCD_DISABLE_SVD'] = '1'
            self._diag_log('connect: importing PyOCD modules...')

            try:
                import usb1
                self._diag_log(f'connect: usb1 loaded from {usb1.__file__}')
            except ImportError as e:
                self._diag_log(f'connect: usb1 import failed: {e}')

            try:
                import usb.core
                self._diag_log(f'connect: usb.core loaded')
            except ImportError as e:
                self._diag_log(f'connect: usb.core import failed: {e}')

            from pyocd.core.session import Session
            from pyocd.probe.aggregator import DebugProbeAggregator

            try:
                from pyocd.debug.svd.loader import SVDLoader
                if not hasattr(SVDLoader, '_patched_run'):
                    _orig_run = SVDLoader.run
                    def _safe_run(self_loader):
                        try:
                            _orig_run(self_loader)
                        except (AttributeError, TypeError, ValueError):
                            pass
                    SVDLoader.run = _safe_run
                    SVDLoader._patched_run = True
                    self._diag_log('connect: patched SVDLoader.run for safety')
            except Exception as svd_patch_err:
                self._diag_log(f'connect: SVD patch skipped: {svd_patch_err}')

            self._diag_log('connect: modules imported')

            self._log('info', f'PyOCD连接: target_override={target if use_override else "auto"}, connect_mode={pyocd_connect_mode}, frequency={speed}kHz')

            options = {
                'frequency': speed * 1000,
                'enable_svd': False,
                'svd': False,
                'connect_mode': pyocd_connect_mode,
                'auto_unlock': True,
                'halt_on_connect': pyocd_connect_mode == 'halt',
            }
            if use_override:
                options['target_override'] = target

            pack_files = self._find_pack_files()
            if pack_files:
                options['pack'] = pack_files
                self._log('info', f'加载 {len(pack_files)} 个CMSIS Pack')
            self._diag_log(f'connect: options={options}, serial={probe_serial}')

            self._diag_log('connect: getting probe object...')
            probe = None
            all_probes = DebugProbeAggregator.get_all_connected_probes()
            self._diag_log(f'connect: found {len(all_probes)} probes')
            for p in all_probes:
                self._diag_log(f'  probe: type={type(p).__name__}, uid={p.unique_id}')
            if probe_serial:
                for p in all_probes:
                    if p.unique_id == probe_serial:
                        probe = p
                        break
            if probe is None:
                pyocd_compatible = [p for p in all_probes
                                    if 'jlink' not in type(p).__name__.lower()]
                if pyocd_compatible:
                    probe = pyocd_compatible[0]
                    self._diag_log(f'connect: serial not matched, falling back to first pyocd-compatible probe {probe.unique_id} ({type(probe).__name__})')
            if probe is None and all_probes:
                probe = all_probes[0]
                self._diag_log(f'connect: no pyocd-compatible probe, trying first probe {probe.unique_id} ({type(probe).__name__})')
            if probe is None:
                raise RuntimeError(f'未找到调试探针 (serial={probe_serial})')

            self._diag_log(f'connect: using probe {probe.unique_id} ({type(probe).__name__}), opening session...')
            self._session = Session(probe, options=options)
            self._board = self._session.board
            self._target = self._session.target
            with _SuppressPyocdStderr():
                try:
                    self._session.open()
                except Exception as open_err:
                    import traceback
                    tb = traceback.format_exc()
                    self._diag_log(f'connect: session.open() exception: {type(open_err).__name__}: {open_err}')
                    self._diag_log(f'connect: traceback:\n{tb}')
                    err_str = str(open_err)
                    if 'TransferFault' in err_str or 'FAULT ACK' in err_str or 'communication failure' in err_str:
                        raise RuntimeError(
                            f"SWD通讯失败(FAULT ACK)，请检查:\n"
                            f"1. 探针与目标板连线是否正确(SWDIO/SWCLK/GND)\n"
                            f"2. 目标MCU是否已上电\n"
                            f"3. 连接模式是否正确(尝试'under_reset')\n"
                            f"4. 目标芯片型号是否匹配\n"
                            f"原始错误: {open_err}"
                        )
                    raise
            try:
                self._target.resume()
            except Exception as resume_err:
                self._diag_log(f'connect: target.resume() warning: {type(resume_err).__name__}: {resume_err}')
                self._log('warning', f'目标resume失败(非致命): {resume_err}')
            self._log('info', f'PyOCD 已连接: {self._board.unique_id}')
            self._diag_log(f'connect: OK, board={self._board.unique_id}')
            return True
        except Exception as e:
            if self._session is not None:
                try:
                    self._session.close()
                except Exception:
                    pass
            self._session = None
            self._board = None
            self._target = None
            self._diag_log(f'connect: FAILED: {type(e).__name__}: {e}')
            self._log('error', f'PyOCD连接失败: {type(e).__name__}: {e}')
            raise RuntimeError(f"PyOCD 连接失败: {e}")

    def _find_pack_files(self) -> list:
        import glob as _glob
        if not os.path.isdir(RUNTIME_PACKS_DIR):
            return []
        pack_files = sorted(_glob.glob(os.path.join(RUNTIME_PACKS_DIR, '*.pack')))
        return pack_files

    def _resolve_target(self, target: str):
        """解析 PyOCD 目标名，支持系列名模糊匹配。

        用户可能输入系列名（如 stm32u575），PyOCD 需要具体型号（如 stm32u575zitx）。
        - 精确匹配：返回 (target, True)
        - 前缀匹配到多个：返回 (target, False) 不设 target_override，让探针自动识别
        - 前缀匹配到1个：返回 (resolved, True)
        - 无匹配：返回 (target, True) 让 PyOCD 自行处理
        """
        target_lower = target.lower().strip()
        if not target_lower:
            return target, True

        try:
            from ..runtime.path_config import RUNTIME_PYOCD_TARGETS_TXT
            if not os.path.isfile(RUNTIME_PYOCD_TARGETS_TXT):
                return target, True
            candidates = []
            with open(RUNTIME_PYOCD_TARGETS_TXT, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    name = line.split('\t')[0].strip()
                    if not name or name.lower() == 'name':
                        continue
                    if name.lower() == target_lower:
                        return name, True
                    if name.lower().startswith(target_lower):
                        candidates.append(name)
            if len(candidates) == 1:
                return candidates[0], True
            if len(candidates) > 1:
                return target, False
        except Exception as e:
            self._diag_log(f'_resolve_target error: {e}')
        return target, True

    def disconnect(self) -> None:
        self._rtt_cb = None
        self._rtt_initialized = False
        if self._session is not None:
            target = self._target
            self._target = None
            self._board = None
            try:
                if target is not None:
                    try:
                        target.resume()
                    except Exception:
                        pass
            except Exception:
                pass
            try:
                session = self._session
                self._session = None
                try:
                    session.close()
                except Exception:
                    pass
            except Exception:
                pass

    def init_rtt(self, rtt_address: int = None, rtt_mode: str = 'auto',
                 range_start: int = None, range_end: int = None) -> bool:
        if not self.is_connected:
            raise RuntimeError("PyOCD 未连接")
        self._rtt_initialized = False
        self._rtt_cb = None

        try:
            from pyocd.debug.rtt import RTTControlBlock
        except ImportError:
            raise RuntimeError("PyOCD RTT 模块不可用")

        try:
            address = None
            size = None

            if rtt_mode == 'address' and rtt_address is not None:
                self._log('info', f'使用指定RTT地址: 0x{rtt_address:08X}')
                address = rtt_address
            elif rtt_mode == 'range' and range_start is not None and range_end is not None:
                self._log('info', f'RTT搜索范围: 0x{range_start:08X} - 0x{range_end:08X}')
                address = range_start
                size = range_end - range_start
            else:
                self._log('info', '自动搜索RTT控制块...')

            try:
                self._target.resume()
            except Exception as resume_err:
                self._diag_log(f'init_rtt: target.resume() warning: {resume_err}')
            time.sleep(0.1)

            with _SuppressPyocdStderr():
                try:
                    self._rtt_cb = RTTControlBlock.from_target(
                        self._target, address=address, size=size
                    )
                    self._rtt_cb.start()
                except Exception as rtt_err:
                    err_str = str(rtt_err)
                    self._diag_log(f'init_rtt: RTTControlBlock error: {type(rtt_err).__name__}: {rtt_err}')
                    if 'TransferFault' in err_str or 'FAULT ACK' in err_str or 'communication failure' in err_str:
                        raise RuntimeError(
                            f"RTT搜索时SWD通讯失败，请检查:\n"
                            f"1. 目标MCU固件是否已初始化RTT(SEGGER_RTT_Init)\n"
                            f"2. RTT控制块是否在有效的RAM区域\n"
                            f"3. 尝试使用'地址'模式指定RTT控制块地址\n"
                            f"原始错误: {rtt_err}"
                        )
                    raise

            num_up = len(self._rtt_cb.up_channels)
            num_down = len(self._rtt_cb.down_channels)
            self._log('info', f'RTT已就绪，{num_up}个上行通道，{num_down}个下行通道')

            cb_type = type(self._rtt_cb).__name__
            cb_module = type(self._rtt_cb).__module__
            has_thread = hasattr(self._rtt_cb, '_thread') and self._rtt_cb._thread is not None
            self._diag_log(f'init_rtt: OK, cb={cb_type}/{cb_module}, has_bg_thread={has_thread}')

            for i, ch in enumerate(self._rtt_cb.up_channels):
                name = ch.name or f'Up[{i}]'
                self._log('info', f'  上行通道{i}: {name}')
                ch_type = type(ch).__name__
                has_available = hasattr(ch, 'available')
                try:
                    avail = ch.available() if has_available else -1
                except Exception:
                    avail = -2
                self._diag_log(f'  UpCh[{i}]: type={ch_type}, name={name}, available={avail}')
            for i, ch in enumerate(self._rtt_cb.down_channels):
                name = ch.name or f'Down[{i}]'
                self._log('info', f'  下行通道{i}: {name}')

            self._rtt_initialized = True
            self._log('success', 'RTT初始化成功')
            return True
        except Exception as e:
            self._rtt_cb = None
            self._diag_log(f'init_rtt: FAILED: {type(e).__name__}: {e}')
            err_str = str(e)
            if 'pop from an empty deque' in err_str:
                hint = ' - RTT控制块读取异常，请确认MCU固件已调用SEGGER_RTT_Init()后重试连接'
            elif type(e).__name__ == 'AssertionError':
                hint = ' - PyOCD内部断言失败，请重试连接'
            else:
                hint = ''
            raise RuntimeError(f"RTT 初始化失败: {e}{hint}")

    def _poll_rtt_control_block(self):
        cb = self._rtt_cb
        if cb is None:
            return
        for poll_name in ('poll', '_poll', '_read_all_channels', '_poll_channels'):
            if hasattr(cb, poll_name):
                try:
                    getattr(cb, poll_name)()
                except Exception:
                    pass
                break

    def _read_upchannel(self, ch, channel: int, buffer_size: int) -> bytes:
        """读取上行通道数据，兼容不同 PyOCD 版本的 read() 签名。"""
        try:
            return ch.read(length=buffer_size)
        except TypeError:
            pass
        try:
            data = ch.read()
        except Exception as inner_e:
            self._diag_log(f'rtt_read: ch.read() (no-arg) FAILED: {type(inner_e).__name__}: {inner_e}')
            return b''
        if data:
            if len(data) > buffer_size:
                data = data[:buffer_size]
        else:
            if (self._diag_counter % 100) == 0:
                ch_type = type(ch).__name__
                try:
                    avail = ch.available() if hasattr(ch, 'available') else -1
                except Exception:
                    avail = -3
                self._diag_log(f'rtt_read: ch={channel} type={ch_type} read() -> empty, available={avail}')
            self._diag_counter += 1
        return data

    def rtt_read(self, channel: int = 0, buffer_size: int = 1024) -> bytes:
        if not self._rtt_initialized or self._rtt_cb is None:
            raise RuntimeError("RTT 未初始化")
        try:
            if channel >= len(self._rtt_cb.up_channels):
                return b''
            ch = self._rtt_cb.up_channels[channel]
            self._poll_rtt_control_block()
            self._force_refresh_channel(ch)
            return self._read_upchannel(ch, channel, buffer_size)
        except Exception as e:
            self._log('warning', f'PyOCD RTT读取通道{channel}失败: {e}')
            self._diag_log(f'rtt_read(ch={channel}, buf={buffer_size}) FAILED: {type(e).__name__}: {e}')
            return b''

    def rtt_read_all(self, channels: list, buffer_size: int = 1024) -> dict:
        """一次poll控制块，批量读取多个通道数据。返回 {channel: bytes}。"""
        if not self._rtt_initialized or self._rtt_cb is None:
            raise RuntimeError("RTT 未初始化")
        result = {}
        try:
            self._poll_rtt_control_block()
        except Exception:
            pass
        for channel in channels:
            try:
                if channel >= len(self._rtt_cb.up_channels):
                    continue
                ch = self._rtt_cb.up_channels[channel]
                self._force_refresh_channel(ch)
                data = self._read_upchannel(ch, channel, buffer_size)
                result[channel] = data
            except Exception as e:
                self._log('warning', f'PyOCD RTT批量读取通道{channel}失败: {e}')
                result[channel] = b''
        return result

    def _force_refresh_channel(self, ch):
        for attr in ('_WrOff', '_RdOff', '_wr_off', '_rd_off'):
            if hasattr(ch, attr):
                try:
                    setattr(ch, attr, None)
                except Exception:
                    pass
        if hasattr(ch, '_read_from_target'):
            try:
                ch._read_from_target()
            except Exception:
                pass
        elif hasattr(ch, 'update'):
            try:
                ch.update()
            except Exception:
                pass

    def rtt_write(self, channel: int, data: bytes) -> int:
        if not self._rtt_initialized or self._rtt_cb is None:
            raise RuntimeError("RTT 未初始化")
        try:
            if channel >= len(self._rtt_cb.down_channels):
                return 0
            return self._rtt_cb.down_channels[channel].write(data)
        except Exception as e:
            self._log('warning', f'PyOCD RTT写入通道{channel}失败: {e}')
            return 0

    def _ensure_usb_modules(self):
        """打包模式下：确保libusb1 backend patch指向正确的DLL。只执行一次。"""
        if not getattr(sys, 'frozen', False):
            return
        if getattr(self.__class__, '_usb_patched', False):
            return
        self.__class__._usb_patched = True
        try:
            from rtt_tool.runtime.path_config import find_libusb_dll, inject_dll_path
            inject_dll_path()
            dll_path = find_libusb_dll()
            if dll_path and os.path.isfile(dll_path):
                try:
                    import ctypes
                    ctypes.CDLL(dll_path)
                except Exception:
                    pass
                import usb.backend.libusb1 as _libusb1_backend
                _orig = _libusb1_backend.get_backend
                def _patched(find_library=None, **kwargs):
                    return _orig(find_library=lambda x: dll_path)
                _libusb1_backend.get_backend = _patched
                self._diag_log(f'_ensure_usb_modules: patched libusb1 backend to {dll_path}')
        except Exception as e:
            self._diag_log(f'_ensure_usb_modules error: {e}')

    def _enumerate_pyocd_aggregator(self):
        """使用 PyOCD DebugProbeAggregator 枚举探针。"""
        self._ensure_usb_modules()
        probes = []
        from pyocd.probe.aggregator import DebugProbeAggregator
        all_probes = DebugProbeAggregator.get_all_connected_probes()
        self._diag_log(f'get_probe_list: aggregator found {len(all_probes)} probes')
        for p in all_probes:
            probe_type_name = type(p).__name__.lower()
            sn = p.unique_id or ''
            if 'stlink' in probe_type_name:
                ptype = 'stlink'
                pname = 'ST-Link'
            elif 'cmsis' in probe_type_name or 'dap' in probe_type_name:
                ptype = 'cmsis-dap'
                pname = 'CMSIS-DAP'
            elif 'jlink' in probe_type_name:
                ptype = 'jlink'
                pname = 'J-Link'
            else:
                ptype = probe_type_name
                pname = probe_type_name
            try:
                desc = getattr(p, 'description', '') or ''
                if desc:
                    pname = desc
            except Exception:
                pass
            probes.append({
                'type': ptype,
                'name': pname,
                'serial': sn,
                'backend': 'pyocd'
            })
            self._diag_log(f'  probe: type={ptype}, name={pname}, sn={sn}')
        return probes

    def _enumerate_pyusb(self):
        """使用 pyusb 回退枚举 CMSIS-DAP / ST-Link 探针。"""
        probes = []
        import usb.core
        import usb.backend.libusb1
        import usb.util
        backend = usb.backend.libusb1.get_backend()
        self._diag_log(f'get_probe_list: fallback to pyusb, backend={backend}')
        if backend is not None:
            for dev in usb.core.find(find_all=True, backend=backend):
                try:
                    vid, pid = dev.idVendor, dev.idProduct
                    try:
                        product_str = (usb.util.get_string(dev, dev.iProduct) or '').lower()
                    except Exception:
                        product_str = ''
                    is_cmsis_dap = (
                        (vid == 0x0D28 and pid == 0x020) or
                        (vid == 0x045B) or
                        ('cmsis' in product_str or 'dap' in product_str)
                    ) and vid != 0x1366
                    is_stlink = vid == 0x0483 and pid in (0x3748, 0x374B, 0x374F, 0x374E, 0x3744, 0x3752)
                    if is_cmsis_dap:
                        try:
                            sn = dev.serial_number or ''
                            name = product_str or 'CMSIS-DAP'
                        except Exception:
                            sn = ''
                            name = 'CMSIS-DAP'
                        probes.append({
                            'type': 'cmsis-dap',
                            'name': name,
                            'serial': sn,
                            'backend': 'pyocd'
                        })
                    elif is_stlink:
                        try:
                            sn = dev.serial_number or ''
                            name = product_str or 'ST-Link'
                        except Exception:
                            sn = ''
                            name = 'ST-Link'
                        probes.append({
                            'type': 'stlink',
                            'name': name,
                            'serial': sn,
                            'backend': 'pyocd'
                        })
                except Exception as e2:
                    self._diag_log(f'get_probe_list: device enumerate error: {type(e2).__name__}: {e2}')
            self._diag_log(f'get_probe_list: pyusb fallback found {len(probes)} probes')
        return probes

    def get_probe_list(self, force=False) -> list:
        self._ensure_libusb_path()
        now = time.time()
        if not force and self._probe_cache is not None and (now - self._probe_cache_time) < 5.0:
            return self._probe_cache
        probes = []
        if self._pyocd_available:
            self._diag_log('get_probe_list: trying DebugProbeAggregator...')
            try:
                probes = self._enumerate_pyocd_aggregator()
            except Exception as e:
                self._diag_log(f'get_probe_list: aggregator failed (will retry): {type(e).__name__}: {e}')
                import time as _time
                _time.sleep(0.3)
                try:
                    probes = self._enumerate_pyocd_aggregator()
                    self._diag_log(f'get_probe_list: aggregator retry OK, found {len(probes)} probes')
                except Exception as e2:
                    self._diag_log(f'get_probe_list: aggregator retry also failed: {type(e2).__name__}: {e2}')
                    try:
                        probes = self._enumerate_pyusb()
                    except Exception as e3:
                        self._diag_log(f'get_probe_list: pyusb also failed: {type(e3).__name__}: {e3}')
        if not probes:
            try:
                probes = self._enumerate_pyocd_aggregator()
            except Exception:
                pass
        self._probe_cache = probes
        self._probe_cache_time = now
        return probes

    def read_memory(self, address: int, var_type: str = 'uint32') -> object:
        if not self.is_connected:
            raise RuntimeError("PyOCD 未连接")
        if var_type not in self._TYPE_SIZE_MAP:
            raise ValueError(f"不支持的变量类型: {var_type}")
        size = self._TYPE_SIZE_MAP[var_type]
        fmt = self._TYPE_FMT_MAP[var_type]
        try:
            if size == 1:
                val = self._target.read8(address)
            elif size == 2:
                val = self._target.read16(address)
            elif size == 4:
                val = self._target.read32(address)
            else:
                raise ValueError(f"不支持的大小: {size}")
            if var_type == 'float':
                return struct.unpack('<f', struct.pack('<I', val))[0]
            if var_type.startswith('int'):
                return struct.unpack(f'<{fmt}', struct.pack(f'<{"I" if size <= 4 else "Q"}', val))[0]
            return val
        except Exception as e:
            raise RuntimeError(f"读取内存失败 (地址=0x{address:08X}, 类型={var_type}): {e}")

    @property
    def is_connected(self) -> bool:
        return self._session is not None and self._target is not None

    @property
    def backend_type(self) -> str:
        return "pyocd"
