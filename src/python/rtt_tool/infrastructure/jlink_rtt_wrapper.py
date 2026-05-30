#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2026 chenkaka
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
JLink RTT SDK封装
使用pylink库实现RTT功能
"""

import os
import sys
import struct
import time
import atexit
from ..runtime.path_config import find_jlink_dll, RUNTIME_DLL_DIR


class JLinkRTTWrapper:
    """JLink RTT SDK封装类"""
    
    def __init__(self, jlink_path=None, log_service=None):
        """
        初始化JLink RTT封装
        
        Args:
            jlink_path: JLink安装路径，None则自动查找
            log_service: 日志服务，用于输出调试信息
        """
        self.jlink = None
        self.connected = False
        self.rtt_initialized = False
        self._rtt_cb_addr = 0
        self.log_service = log_service
        
        # 查找JLinkARM.dll
        if jlink_path is None:
            jlink_path = self._find_jlink_dll()
        
        if jlink_path is None:
            raise RuntimeError(
                "未找到JLinkARM.dll，请安装JLink软件或指定路径。\n"
                "注意: JLink DLL位数必须与Python位数匹配!\n"
                f"当前Python: {struct.calcsize('P') * 8}位"
            )
        
        self.jlink_path = jlink_path
        
        # 检查DLL位数
        try:
            import pefile
            pe = pefile.PE(jlink_path)
            dll_bits = 64 if pe.OPTIONAL_HEADER.Magic == 0x20b else 32
            python_bits = struct.calcsize('P') * 8
            
            if dll_bits != python_bits:
                raise RuntimeError(
                    f"JLink DLL位数不匹配!\n"
                    f"JLink DLL: {dll_bits}位\n"
                    f"Python: {python_bits}位\n"
                    f"请安装{'64位' if python_bits == 64 else '32位'}版本的JLink软件"
                )
        except ImportError:
            pass
        except Exception:
            pass
        
        # 设置环境变量，让pylink找到DLL
        jlink_dir = os.path.dirname(jlink_path)
        os.environ['JLINK_PATH'] = jlink_dir

        # 将JLink目录添加到PATH环境变量
        if jlink_dir not in os.environ.get('PATH', ''):
            os.environ['PATH'] = jlink_dir + os.pathsep + os.environ.get('PATH', '')

        atexit.register(self._safe_disconnect)
        self._pylink_imported = False
    
    def _find_jlink_dll(self):
        return find_jlink_dll()
    
    def _log(self, level, msg):
        """输出日志"""
        if self.log_service:
            getattr(self.log_service, level)(msg)
    
    def _get_cb_addr_via_dll(self) -> int:
        """绕过pylink直接调DLL获取RTT CB地址
        
        策略：构造JLinkRTTerminalStart(ConfigBlockAddress=0)，
        调DLL的JLINK_RTTERMINAL_Control(START)让DLL自动搜索CB，
        此调用同时初始化RTT(等效于rtt_start())，
        然后检查ConfigBlockAddress是否被DLL写回找到的CB地址。
        
        Returns:
            int: CB地址，0表示DLL未写回(但RTT可能已初始化)
        """
        try:
            import ctypes
            import pylink.enums as pl_enums
            import pylink.structs as pl_structs

            config = pl_structs.JLinkRTTerminalStart()
            config.ConfigBlockAddress = 0
            cmd_start = pl_enums.JLinkRTTCommand.START

            self.jlink.rtt_control(cmd_start, config)

            written_addr = config.ConfigBlockAddress
            if written_addr > 0:
                self._log('info', f'auto模式: DLL写回CB地址=0x{written_addr:08X}')
                return written_addr
            self._log('info', 'auto模式: DLL未写回CB地址(ConfigBlockAddress仍为0)')
        except Exception as e:
            self._log('warning', f'auto模式: DLL START+写回失败: {e}')
        return 0

    def _find_cb_addr_from_device_info(self) -> int:
        """从DLL设备信息获取RAM区域并搜索RTT CB地址
        
        策略1: 从jlink._device(JLinkDeviceInfo)获取RAM区域
               - aRAMArea数组(含Addr+Size, 最多32个)
               - 回退到RAMAddr+RAMSize
        策略2: 回退到memory_zones()获取RAM区域(无Size，默认搜1MB)
        
        Returns:
            int: CB地址，未找到返回0
        """
        SEARCH_SIZE_FALLBACK = 0x00100000
        ram_regions = []

        try:
            dev_info = getattr(self.jlink, '_device', None)
            if dev_info is not None:
                for i in range(32):
                    try:
                        area = dev_info.aRAMArea[i]
                        if area.Addr > 0 and area.Size > 0:
                            ram_regions.append((area.Addr, area.Size, f"aRAMArea[{i}]"))
                    except Exception:
                        break
                if not ram_regions:
                    ram_addr = getattr(dev_info, 'RAMAddr', 0)
                    ram_size = getattr(dev_info, 'RAMSize', 0)
                    if ram_addr > 0 and ram_size > 0:
                        ram_regions.append((ram_addr, ram_size, "RAMAddr/RAMSize"))
                if ram_regions:
                    self._log('info', f'auto模式: 从DeviceInfo获取到{len(ram_regions)}个RAM区域')
        except Exception as e:
            self._log('warning', f'auto模式: DeviceInfo读取失败: {e}')

        if not ram_regions:
            try:
                zones = self.jlink.memory_zones()
                if zones:
                    ram_keywords = ['ram', 'sram', 'data', 'dram']
                    for zone in zones:
                        desc = zone.sDesc.decode() if isinstance(zone.sDesc, bytes) else zone.sDesc
                        name = zone.sName.decode() if isinstance(zone.sName, bytes) else zone.sName
                        desc_lower = (desc or '').lower()
                        name_lower = (name or '').lower()
                        if any(kw in desc_lower or kw in name_lower for kw in ram_keywords):
                            ram_regions.append((zone.VirtAddr, SEARCH_SIZE_FALLBACK, f"zone:{name}"))
                    if ram_regions:
                        self._log('info', f'auto模式: 从memory zones获取到{len(ram_regions)}个RAM区域')
            except Exception as e:
                self._log('warning', f'auto模式: memory_zones查询失败: {e}')

        if not ram_regions:
            self._log('info', 'auto模式: 无可用RAM区域(DeviceInfo和memory_zones均未提供)')
            return 0

        for addr, size, source in ram_regions:
            end_addr = addr + size
            try:
                self._log('info', f'auto模式: 在{source}(0x{addr:08X}-0x{end_addr:08X})中搜索CB...')
                found = self._search_rtt_in_range(addr, end_addr)
                if found is not None:
                    return found
            except Exception:
                continue
        return 0

    def _log_memory_regions(self):
        """获取并记录芯片内存区域信息"""
        try:
            zones = self.jlink.memory_zones()
            if not zones:
                self._log('info', '芯片无memory zones信息(部分芯片不提供此数据)')
                return
            self._log('info', f'芯片内存区域(Memory Zones)数量: {len(zones)}')
            for i, zone in enumerate(zones):
                name = zone.sName.decode() if isinstance(zone.sName, bytes) else zone.sName
                desc = zone.sDesc.decode() if isinstance(zone.sDesc, bytes) else zone.sDesc
                self._log('info', f'  区域[{i}]: 名称={name}, 描述={desc}, 虚拟起始地址=0x{zone.VirtAddr:08X}')
        except Exception as e:
            self._log('warning', f'获取内存区域信息失败: {e}')
    
    def get_down_buffer_info(self, cb_addr: int = 0) -> dict:
        """直接从MCU内存读取RTT控制块中Down buffer的名称和大小
        
        Args:
            cb_addr: RTT控制块地址（若为0则尝试通过rtt_get_buf_descriptor获取）
        
        SEGGER_RTT_CB内存布局(32位ARM):
          acID[16]                (16 bytes)
          MaxNumUpBuffers        (4 bytes, int32)
          MaxNumDownBuffers      (4 bytes, int32)
          aUp[MaxNumUpBuffers]   (每个24 bytes)
          aDown[MaxNumDownBuffers](每个24 bytes)
        
        每个BUFFER_UP/DOWN entry:
          sName        (4 bytes, const char*指针)
          pBuffer      (4 bytes, char*指针)
          SizeOfBuffer (4 bytes, uint32)
          WrOff        (4 bytes, uint32)
          RdOff        (4 bytes, uint32)
          Flags        (4 bytes, uint32)
        """
        import struct
        result = {}
        if not self.jlink or not self.rtt_initialized:
            return result
        if cb_addr == 0:
            return result
        cb_addr = self._verify_and_correct_cb_addr(cb_addr)
        if cb_addr == 0:
            return result
        try:
            status = self.jlink.rtt_get_status()
            num_up = status.NumUpBuffers
            num_down = status.NumDownBuffers
            if num_down == 0:
                return result
            cb_header = 16 + 4 + 4
            down_offset = cb_header + num_up * 24
            ENTRY = 24
            for i in range(min(num_down, 10)):
                addr = cb_addr + down_offset + i * ENTRY
                try:
                    raw = bytes(self.jlink.memory_read8(addr, ENTRY))
                    s_name_ptr = struct.unpack_from('<I', raw, 0)[0]
                    p_buf_ptr = struct.unpack_from('<I', raw, 4)[0]
                    buf_size = struct.unpack_from('<I', raw, 8)[0]
                    name = ""
                    if s_name_ptr > 0 and buf_size > 0:
                        try:
                            nb = bytes(self.jlink.memory_read8(s_name_ptr, 32))
                            nul = nb.find(b'\x00')
                            if nul >= 0:
                                nb = nb[:nul]
                            name = nb.decode('utf-8', errors='replace')
                        except Exception:
                            pass
                    if buf_size > 0:
                        result[i] = (buf_size, name or f"Down[{i}]")
                except Exception:
                    continue
        except Exception:
            pass
        return result
    
    def _verify_and_correct_cb_addr(self, addr: int) -> int:
        """验证CB地址的SEGGER RTT签名，若不对在±256B范围搜索校正
        
        Args:
            addr: 候选CB地址
            
        Returns:
            int: 校正后的CB地址（acID位置），0表示未找到
        """
        if addr == 0:
            return 0
        try:
            sig_check = bytes(self.jlink.memory_read8(addr, 12))
            if sig_check[:10] == b'SEGGER RTT':
                return addr
        except Exception:
            pass
        for offset in range(-256, 257, 4):
            try:
                check = bytes(self.jlink.memory_read8(addr + offset, 12))
                if check[:10] == b'SEGGER RTT':
                    corrected = addr + offset
                    self._log('info', f'CB地址校正: 0x{addr:08X} -> 0x{corrected:08X} (偏移{offset:+d})')
                    return corrected
            except Exception:
                continue
        self._log('warning', f'CB地址0x{addr:08X}附近±256B未找到SEGGER RTT签名')
        return 0
    
    def _log_rtt_info(self):
        """RTT启动后，获取并打印RTT控制块信息"""
        time.sleep(0.1)
        try:
            status = self.jlink.rtt_get_status()
            self._log('info', f'RTT状态: 运行={bool(status.IsRunning)}, Up缓冲区={status.NumUpBuffers}, Down缓冲区={status.NumDownBuffers}')
        except Exception as e:
            self._log('warning', f'获取RTT状态失败: {e}')
        try:
            num_up = 0
            for i in range(3):
                try:
                    desc = self.jlink.rtt_get_buf_descriptor(i, up=True)
                    name = desc.acName.decode() if isinstance(desc.acName, bytes) else desc.acName
                    if desc.SizeOfBuffer > 0:
                        num_up += 1
                    self._log('info', f'  Up缓冲区[{i}]: 名称="{name}", 大小={desc.SizeOfBuffer}字节')
                except Exception:
                    break
            num_down = 0
            for i in range(3):
                try:
                    desc = self.jlink.rtt_get_buf_descriptor(i, up=False)
                    name = desc.acName.decode() if isinstance(desc.acName, bytes) else desc.acName
                    if desc.SizeOfBuffer > 0:
                        num_down += 1
                    self._log('info', f'  Down缓冲区[{i}]: 名称="{name}", 大小={desc.SizeOfBuffer}字节')
                except Exception:
                    break
            if num_up == 0 and num_down == 0:
                self._log('warning', 'RTT控制块已找到但缓冲区未初始化(大小=0)，可能目标MCU尚未调用SEGGER_RTT_Init()')
        except Exception as e:
            self._log('warning', f'获取RTT缓冲区描述失败: {e}')
    
    def _search_rtt_in_range(self, range_start, range_end):
        """
        在指定地址范围内搜索RTT控制块
        
        通过逐块读取目标内存，搜索"SEGGER RTT"签名来定位控制块
        
        Args:
            range_start: 搜索起始地址
            range_end: 搜索结束地址
            
        Returns:
            int: 找到的RTT控制块地址，未找到返回None
        """
        RTT_SIG = b"SEGGER RTT"
        SEARCH_STEP = 16
        READ_CHUNK = 1024
        
        self._log('info', f'开始在范围 0x{range_start:08X} - 0x{range_end:08X} 内搜索RTT控制块...')
        self._log('info', f'搜索签名: "{RTT_SIG.decode()}", 步进: {SEARCH_STEP}字节')
        
        total_range = range_end - range_start
        self._log('info', f'搜索范围大小: 0x{total_range:08X}({total_range}字节)')
        
        addr = range_start
        while addr < range_end:
            read_size = min(READ_CHUNK, range_end - addr)
            try:
                data = self.jlink.memory_read(addr, read_size)
                data_bytes = bytes(data)
                
                offset = 0
                while offset <= len(data_bytes) - len(RTT_SIG):
                    if data_bytes[offset:offset + len(RTT_SIG)] == RTT_SIG:
                        found_addr = addr + offset
                        self._log('info', f'找到RTT控制块! 地址: 0x{found_addr:08X}')
                        return found_addr
                    offset += SEARCH_STEP
                    
            except Exception as e:
                self._log('warning', f'读取地址 0x{addr:08X} 失败: {e}')
            
            addr += read_size
        
        self._log('warning', f'在范围 0x{range_start:08X} - 0x{range_end:08X} 内未找到RTT控制块')
        return None
    
    def connect(self, device="Cortex-M4", interface="SWD", speed=4000, 
                serial_number=None, ip_address=None):
        """
        连接到MCU
        
        Args:
            device: MCU型号，如"Cortex-M4"
            interface: 接口类型，"SWD"或"JTAG"
            speed: 接口速度（kHz）
            serial_number: JLink序列号（可选）
            ip_address: JLink IP地址（可选）
        
        Returns:
            bool: 连接是否成功
        """
        if self.connected:
            return True
        
        try:
            if not self._pylink_imported:
                import pylink
                from pylink import library
                self._pylink_imported = True
            jlink_lib = library.Library(dllpath=self.jlink_path)
            self.jlink = pylink.JLink(lib=jlink_lib)
            
            if serial_number:
                self.jlink.open(serial_no=serial_number)
            elif ip_address:
                self.jlink.open(ip_addr=ip_address)
            else:
                try:
                    num_connected = self.jlink.num_connected_emulators()
                except Exception:
                    num_connected = 0
                if num_connected == 0:
                    raise RuntimeError("未检测到J-Link探针，请先连接探针并在配置页面刷新探针列表")
                self.jlink.open()
            
            try:
                self.jlink.disable_dialog_boxes()
            except Exception:
                pass
            
            if interface.upper() == "SWD":
                self.jlink.set_tif(pylink.enums.JLinkInterfaces.SWD)
            else:
                self.jlink.set_tif(pylink.enums.JLinkInterfaces.JTAG)
            
            self.jlink.connect(chip_name=device, speed=speed)
            
            self.connected = True
            return True
            
        except Exception as e:
            self.connected = False
            if self.jlink:
                try:
                    self.jlink.close()
                except Exception:
                    pass
                self.jlink = None
            raise RuntimeError(f"连接失败: {e}")
    
    def disconnect(self):
        """断开连接"""
        try:
            if self.jlink:
                self.jlink.close()
        except Exception:
            pass
        
        self.connected = False
        self.rtt_initialized = False
        self.jlink = None
    
    def init_rtt(self, rtt_address=None, rtt_mode='auto', range_start=None, range_end=None):
        """
        初始化RTT
        
        Args:
            rtt_address: RTT控制块地址（address模式使用）
            rtt_mode: RTT模式 'auto'/'address'/'range'
            range_start: 搜索范围起始地址（range模式使用）
            range_end: 搜索范围结束地址（range模式使用）
        
        Returns:
            bool: 初始化是否成功
        """
        if not self.connected:
            raise RuntimeError("未连接到MCU")
        
        if self.rtt_initialized:
            return True
        
        try:
            self._log('info', f'RTT模式: {rtt_mode}')
            self._log_memory_regions()
            
            if rtt_mode == 'address':
                self._log('info', f'使用指定RTT地址: 0x{rtt_address:X}')
                self.jlink.rtt_start(rtt_address)
                corrected = self._verify_and_correct_cb_addr(rtt_address)
                self._rtt_cb_addr = corrected
                if corrected and corrected != rtt_address:
                    self._log('info', f'CB地址已校正: 0x{rtt_address:08X} -> 0x{corrected:08X}')
                self._log_rtt_info()
                
            elif rtt_mode == 'range':
                self._log('info', f'搜索范围: 0x{range_start:08X} - 0x{range_end:08X}')
                found_addr = self._search_rtt_in_range(range_start, range_end)
                if found_addr is not None:
                    self._log('info', f'使用搜索到的RTT地址: 0x{found_addr:08X}')
                    self._rtt_cb_addr = found_addr
                    self.jlink.rtt_start(found_addr)
                    self._log_rtt_info()
                else:
                    raise RuntimeError(
                        f"在范围 0x{range_start:08X} - 0x{range_end:08X} 内未找到RTT控制块\n"
                        "请确认:\n"
                        "1. 目标MCU已启动RTT(SEGGER_RTT_Init已调用)\n"
                        "2. 搜索范围覆盖了RTT控制块所在RAM区域\n"
                        "3. 地址范围设置正确(起始<结束)"
                    )
                    
            else:
                self._log('info', '自动检测RTT控制块(J-Link DLL内部扫描RAM区域)...')
                cb_addr = self._get_cb_addr_via_dll()
                if cb_addr > 0:
                    self._rtt_cb_addr = cb_addr
                    self._log('info', f'auto模式: DLL返回CB地址=0x{cb_addr:08X}')
                else:
                    self._log('info', 'auto模式: DLL未写回CB地址，尝试rtt_start+device_info...')
                    self.jlink.rtt_start()
                    cb_from_dev = self._find_cb_addr_from_device_info()
                    if cb_from_dev > 0:
                        self._rtt_cb_addr = cb_from_dev
                        self._log('info', f'auto模式: 通过DeviceInfo/memory_zones定位CB地址=0x{cb_from_dev:08X}')
                    else:
                        self._rtt_cb_addr = 0
                        self._log('warning', 'auto模式: 无法定位CB地址，Down buffer信息不可用(请使用range或address模式)')
                self._log_rtt_info()
            
            self.rtt_initialized = True
            return True
            
        except Exception as e:
            self.rtt_initialized = False
            raise RuntimeError(f"RTT初始化失败: {e}")
    
    def read_rtt(self, buffer_size=4096, channel=0):
        """
        从RTT读取数据
        
        Args:
            buffer_size: 读取缓冲区大小
            channel: RTT通道号
        
        Returns:
            bytes: 读取的数据
        """
        if not self.rtt_initialized:
            raise RuntimeError("RTT未初始化")
        
        try:
            data = self.jlink.rtt_read(channel, buffer_size)
            return bytes(data)
        except Exception as e:
            raise RuntimeError(f"RTT读取失败: {e}")
    
    def write_rtt(self, data, channel=0):
        """
        向RTT写入数据
        
        Args:
            data: 要写入的数据（bytes）
            channel: RTT通道号
        
        Returns:
            int: 实际写入的字节数
        """
        if not self.rtt_initialized:
            raise RuntimeError("RTT未初始化")
        
        if not data:
            return 0
        
        try:
            num_bytes = self.jlink.rtt_write(channel, list(data))
            return num_bytes
        except Exception as e:
            raise RuntimeError(f"RTT写入失败: {e}")
    
    def _safe_disconnect(self):
        """安全断开连接(atexit回调)"""
        try:
            self.disconnect()
        except Exception:
            pass
