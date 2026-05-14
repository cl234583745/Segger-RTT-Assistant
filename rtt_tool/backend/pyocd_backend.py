import os
import struct
import time

from .base import DebuggerBackend


class PyOCDBackend(DebuggerBackend):
    """PyOCD 调试器后端，支持 DAP-Link / ST-Link 等 CMSIS-DAP 探针。"""

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

    RTT_SIG = b"SEGGER RTT"
    RTT_CB_HEADER_SIZE = 24
    RTT_CHANNEL_STRUCT_SIZE = 24

    def __init__(self, log_service=None):
        self._log_service = log_service
        self._session = None
        self._board = None
        self._target = None
        self._rtt_cb_addr = None
        self._rtt_initialized = False
        self._pyocd_available = self._check_pyocd()
        self._probe_cache = None
        self._probe_cache_time = 0

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
        """确保libusb DLL在搜索路径中（打包后onefile模式需要）"""
        try:
            import sys
            import os
            dirs_to_add = []
            try:
                import usb1
                dirs_to_add.append(os.path.dirname(usb1.__file__))
            except ImportError:
                pass
            if getattr(sys, 'frozen', False):
                base = sys._MEIPASS
                dirs_to_add.extend([base, os.path.join(base, 'usb1')])
            exe_dir = os.path.dirname(sys.executable)
            dirs_to_add.append(exe_dir)
            for d in dirs_to_add:
                try:
                    os.add_dll_directory(d)
                except (OSError, FileNotFoundError):
                    pass
                if d not in os.environ.get('PATH', '').split(os.pathsep):
                    os.environ['PATH'] = d + os.pathsep + os.environ.get('PATH', '')
            self._diag_log(f'libusb PATH dirs: {dirs_to_add}')
            self._diag_log(f'libusb-1.0.dll search: ' + str([os.path.exists(os.path.join(d, 'libusb-1.0.dll')) for d in dirs_to_add]))
        except Exception as e:
            self._diag_log(f'_ensure_libusb_path error: {e}')

    def _diag_log(self, msg):
        """写入诊断日志到exe同级的pyocd_diag.log"""
        try:
            import sys, os
            exe_dir = os.path.dirname(sys.executable)
            log_file = os.path.join(exe_dir, 'pyocd_diag.log')
            with open(log_file, 'a', encoding='utf-8') as f:
                from datetime import datetime
                f.write(f'{datetime.now().strftime("%H:%M:%S")} {msg}\n')
        except Exception:
            pass

    def _find_pyocd_exe(self) -> str:
        """查找可用的 pyocd 可执行文件。"""
        candidates = ['pyocd']
        custom_path = os.environ.get('PYOCD_EXE_PATH', '')
        if custom_path and os.path.isfile(custom_path):
            candidates.insert(0, custom_path)
        import shutil
        for cmd in candidates:
            if os.path.isfile(cmd) or shutil.which(cmd):
                return cmd
        return None

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
        pyocd_target = kwargs.get('pyocd_target')

        target = pyocd_target if pyocd_target else device

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
            self._diag_log('connect: importing PyOCD modules...')
            from pyocd.probe.cmsis_dap_probe import CMSISDAPProbe
            from pyocd.core.session import Session
            self._diag_log('connect: modules imported')

            self._log('info', f'PyOCD连接: target_override={target}, connect_mode={connect_mode}, frequency={speed}kHz')

            options = {
                'frequency': speed * 1000,
                'target_override': target,
                'enable_svd': False,
                'svd': False,
            }

            pack_files = self._find_pack_files()
            if pack_files:
                options['pack'] = pack_files
                self._log('info', f'加载 {len(pack_files)} 个CMSIS Pack')
            self._diag_log(f'connect: options={options}, serial={probe_serial}')

            self._diag_log('connect: getting probe object...')
            probe = None
            all_probes = CMSISDAPProbe.get_all_connected_probes()
            self._diag_log(f'connect: found {len(all_probes)} probes')
            if probe_serial:
                for p in all_probes:
                    if p.unique_id == probe_serial:
                        probe = p
                        break
            if probe is None and all_probes:
                probe = all_probes[0]
            if probe is None:
                raise RuntimeError(f'未找到CMSIS-DAP探针 (serial={probe_serial})')

            self._diag_log(f'connect: using probe {probe.unique_id}, opening session...')
            self._session = Session(probe, options=options)
            self._board = self._session.board
            self._target = self._session.target
            self._session.open()
            self._target.resume()
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
        """查找本地 packs 目录中的 .pack 文件。"""
        import glob as _glob
        from ..utils.resource_utils import get_exe_dir
        packs_dir = os.path.join(get_exe_dir(), 'packs')
        if not os.path.isdir(packs_dir):
            return []
        pack_files = sorted(_glob.glob(os.path.join(packs_dir, '*.pack')))
        return pack_files

    def disconnect(self) -> None:
        if self._session is not None:
            try:
                self._session.close()
            except Exception as e:
                self._log('warning', f'PyOCD session 关闭异常: {e}')
        self._session = None
        self._board = None
        self._target = None
        self._rtt_cb_addr = None
        self._rtt_initialized = False

    def init_rtt(self, rtt_address: int = None, rtt_mode: str = 'auto',
                 range_start: int = None, range_end: int = None) -> bool:
        if not self.is_connected:
            raise RuntimeError("PyOCD 未连接")
        self._rtt_initialized = False
        self._rtt_cb_addr = None

        # 如果指定了精确地址，直接使用
        if rtt_mode == 'address' and rtt_address is not None:
            self._log('info', f'使用指定RTT地址: 0x{rtt_address:08X}')
            self._rtt_cb_addr = rtt_address
            # 验证地址是否有效
            try:
                data = bytes(self._target.read_memory_block8(rtt_address, 56))
                if data[:16] == b'SEGGER RTT\x00\x00\x00\x00\x00\x00':
                    num_up = struct.unpack_from('<I', data, 16)[0]
                    num_down = struct.unpack_from('<I', data, 20)[0]
                    self._log('info', f'RTT已就绪，{num_up}个上行通道，{num_down}个下行通道')
                else:
                    self._log('warning', f'RTT签名不匹配，实际: {data[:16].hex()}')
            except Exception as e:
                self._log('warning', f'读取RTT地址失败: {e}')

        elif rtt_mode == 'range' and range_start is not None and range_end is not None:
            self._log('info', f'RTT搜索范围: 0x{range_start:08X} - 0x{range_end:08X}')
            self._rtt_cb_addr = self._search_rtt_in_range(range_start, range_end)
            if self._rtt_cb_addr is None:
                raise RuntimeError(
                    f"在范围 0x{range_start:08X} - 0x{range_end:08X} 内未找到RTT控制块"
                )
        else:
            self._log('info', '自动搜索RTT控制块...')
            self._rtt_cb_addr = self._auto_search_rtt()
            if self._rtt_cb_addr is None:
                raise RuntimeError("自动搜索未找到RTT控制块")

        self._rtt_initialized = True
        self._log('success', f'RTT控制块地址: 0x{self._rtt_cb_addr:08X}')
        return True

    def _auto_search_rtt(self):
        if self._target is None:
            return None
        try:
            regions = self._target.get_memory_map()
            for region in regions:
                if region.is_ram:
                    start = region.start
                    end = region.start + region.length
                    addr = self._search_rtt_in_range(start, end)
                    if addr is not None:
                        return addr
        except Exception as e:
            self._log('warning', f'自动搜索RTT失败: {e}')
        return None

    def _search_rtt_in_range(self, range_start, range_end):
        SEARCH_STEP = 16
        READ_CHUNK = 1024
        self._log('info', f'PyOCD 搜索RTT: 0x{range_start:08X} - 0x{range_end:08X}')
        addr = range_start
        while addr < range_end:
            read_size = min(READ_CHUNK, range_end - addr)
            try:
                data = self._target.read_memory_block8(addr, read_size)
                data_bytes = bytes(data)
                offset = 0
                while offset <= len(data_bytes) - len(self.RTT_SIG):
                    if data_bytes[offset:offset + len(self.RTT_SIG)] == self.RTT_SIG:
                        found = addr + offset
                        self._log('info', f'PyOCD 找到RTT控制块: 0x{found:08X}')
                        return found
                    offset += SEARCH_STEP
            except Exception as e:
                self._log('warning', f'PyOCD 读取 0x{addr:08X} 失败: {e}')
            addr += read_size
        return None

    def _read_rtt_channel(self, channel, buffer_size):
        if self._rtt_cb_addr is None:
            return b''
        try:
            cb_data = bytes(self._target.read_memory_block8(self._rtt_cb_addr, self.RTT_CB_HEADER_SIZE))
            num_up = struct.unpack_from('<I', cb_data, 16)[0]  # 偏移16: MaxNumUpBuffers
            if channel >= num_up:
                return b''
            up_channels_base = self._rtt_cb_addr + self.RTT_CB_HEADER_SIZE
            ch_offset = up_channels_base + channel * self.RTT_CHANNEL_STRUCT_SIZE
            ch_data = bytes(self._target.read_memory_block8(ch_offset, self.RTT_CHANNEL_STRUCT_SIZE))
            buf_addr = struct.unpack_from('<I', ch_data, 4)[0]
            buf_size = struct.unpack_from('<I', ch_data, 8)[0]
            wr_off = struct.unpack_from('<I', ch_data, 12)[0]
            rd_off = struct.unpack_from('<I', ch_data, 16)[0]
            if wr_off == rd_off:
                return b''
            read_size = min(buffer_size, (wr_off - rd_off) % buf_size)
            result = bytearray()
            to_read = read_size
            src_off = rd_off
            while to_read > 0:
                chunk = min(to_read, buf_size - src_off)
                data = self._target.read_memory_block8(buf_addr + src_off, chunk)
                result.extend(data)
                src_off = (src_off + chunk) % buf_size
                to_read -= chunk
            new_rd_off = (rd_off + read_size) % buf_size
            self._target.write32(ch_offset + 16, new_rd_off)
            return bytes(result)
        except Exception as e:
            self._log('warning', f'PyOCD RTT读取通道{channel}失败: {e}')
            return b''

    def _write_rtt_channel(self, channel, data):
        if self._rtt_cb_addr is None:
            return 0
        try:
            cb_data = bytes(self._target.read_memory_block8(self._rtt_cb_addr, self.RTT_CB_HEADER_SIZE))
            num_up = struct.unpack_from('<I', cb_data, 16)[0]
            num_down = struct.unpack_from('<I', cb_data, 20)[0]
            if channel >= num_down:
                return 0
            up_channels_base = self._rtt_cb_addr + self.RTT_CB_HEADER_SIZE
            down_channels_base = up_channels_base + num_up * self.RTT_CHANNEL_STRUCT_SIZE
            ch_offset = down_channels_base + channel * self.RTT_CHANNEL_STRUCT_SIZE
            ch_data = bytes(self._target.read_memory_block8(ch_offset, self.RTT_CHANNEL_STRUCT_SIZE))
            buf_addr = struct.unpack_from('<I', ch_data, 4)[0]
            buf_size = struct.unpack_from('<I', ch_data, 8)[0]
            wr_off = struct.unpack_from('<I', ch_data, 12)[0]
            rd_off = struct.unpack_from('<I', ch_data, 16)[0]
            free_space = (rd_off - wr_off - 1) % buf_size
            write_size = min(len(data), free_space)
            to_write = write_size
            src_off = 0
            dst_off = wr_off
            while to_write > 0:
                chunk = min(to_write, buf_size - dst_off)
                self._target.write_memory_block8(buf_addr + dst_off, data[src_off:src_off + chunk])
                dst_off = (dst_off + chunk) % buf_size
                src_off += chunk
                to_write -= chunk
            new_wr_off = (wr_off + write_size) % buf_size
            self._target.write32(ch_offset + 12, new_wr_off)
            return write_size
        except Exception as e:
            self._log('warning', f'PyOCD RTT写入通道{channel}失败: {e}')
            return 0

    def rtt_read(self, channel: int = 0, buffer_size: int = 1024) -> bytes:
        if not self._rtt_initialized:
            raise RuntimeError("RTT 未初始化")
        return self._read_rtt_channel(channel, buffer_size)

    def rtt_write(self, channel: int, data: bytes) -> int:
        if not self._rtt_initialized:
            raise RuntimeError("RTT 未初始化")
        return self._write_rtt_channel(channel, data)

    def get_probe_list(self) -> list:
        self._ensure_libusb_path()
        now = time.time()
        if self._probe_cache is not None and (now - self._probe_cache_time) < 5.0:
            return self._probe_cache
        probes = []
        if self._pyocd_available:
            self._diag_log('get_probe_list: trying pyusb enumeration...')
            try:
                import usb.core
                import usb.backend.libusb1
                import usb.util
                backend = usb.backend.libusb1.get_backend()
                self._diag_log(f'get_probe_list: pyusb backend={backend}')
                if backend is not None:
                    for dev in usb.core.find(find_all=True, backend=backend):
                        vid, pid = dev.idVendor, dev.idProduct
                        is_cmsis_dap = (
                            (vid == 0x0D28 and pid == 0x020) or
                            (vid == 0x045B) or
                            ('cmsis' in (usb.util.get_string(dev, dev.iProduct) or '').lower() or
                             'dap' in (usb.util.get_string(dev, dev.iProduct) or '').lower())
                        ) and vid != 0x1366
                        if is_cmsis_dap:
                            try:
                                sn = dev.serial_number or ''
                                name = usb.util.get_string(dev, dev.iProduct) or 'CMSIS-DAP'
                            except Exception:
                                sn = ''
                                name = 'CMSIS-DAP'
                            probes.append({
                                'type': 'cmsis-dap',
                                'name': name,
                                'serial': sn,
                                'backend': 'pyocd'
                            })
                self._diag_log(f'get_probe_list: pyusb found {len(probes)} probes')
            except Exception as e:
                self._diag_log(f'get_probe_list: pyusb failed: {type(e).__name__}: {e}')
                try:
                    import hid
                    for dev in hid.enumerate(0, 0):
                        usage_page = dev.get('usage_page', 0)
                        if usage_page in (0xF00, 0xF001):
                            probes.append({
                                'type': 'cmsis-dap',
                                'name': dev.get('product_string', 'CMSIS-DAP'),
                                'serial': dev.get('serial_number', ''),
                                'backend': 'pyocd'
                            })
                    self._diag_log(f'get_probe_list: hidapi fallback found {len(probes)} probes')
                except Exception as e2:
                    self._diag_log(f'get_probe_list: hidapi also failed: {type(e2).__name__}: {e2}')
        # 回退: subprocess 调用 pyocd list (打包环境下跳过)
        if not probes and not getattr(sys, 'frozen', False):
            try:
                import subprocess
                pyocd_exe = self._find_pyocd_exe()
                if pyocd_exe:
                    result = subprocess.run(
                        [pyocd_exe, 'list'],
                        capture_output=True, text=True, timeout=8,
                        creationflags=self._subprocess_flags()
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        probes = self._parse_pyocd_list_output(result.stdout)
            except Exception as e:
                self._log('warning', f'pyocd subprocess探测失败: {e}')
        self._probe_cache = probes
        self._probe_cache_time = now
        return probes

    def _parse_pyocd_list_output(self, output: str) -> list:
        """解析 `pyocd list` 命令输出。"""
        import re
        probes = []
        for line in output.strip().split('\n'):
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('-'):
                continue
            match = re.match(r'\s*(\d+)\s+(.+?)\s{2,}(\S+)\s+', line)
            if match:
                name = match.group(2).strip()
                serial = match.group(3).strip()
                probes.append({
                    'type': 'cmsis-dap',
                    'name': name,
                    'serial': serial,
                    'backend': 'pyocd'
                })
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
