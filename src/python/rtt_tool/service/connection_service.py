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
连接管理服务
管理MCU连接状态，发射连接状态变化信号
"""

from PyQt5.QtCore import QObject, pyqtSignal
from ..backend.base import DebuggerBackend
from ..utils.device_info_service import DeviceInfoService


class ConnectionService(QObject):
    """连接管理服务，支持多后端调试器。"""
    
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, debugger_manager, log_service=None):
        super().__init__()
        self._debugger_manager = debugger_manager
        self._backend = None
        self.is_connected = False
        self.log_service = log_service
        self._device_info_service = DeviceInfoService(log_service=log_service)
    
    def connect(self, config):
        """
        连接到MCU

        Args:
            config: 连接配置字典

        Returns:
            bool: 连接是否成功
        """
        try:
            debugger_type = config.get('debugger_type', 'jlink')
            jlink_device = config.get('device', 'Cortex-M4')
            pyocd_target = config.get('pyocd_target', '')

            if debugger_type == 'pyocd':
                device_display = pyocd_target or jlink_device
            else:
                device_display = jlink_device

            if self.log_service:
                self.log_service.info(f'开始连接MCU: {device_display} (后端: {debugger_type})')

            self._backend = self._debugger_manager.select_backend(debugger_type)

            if self.log_service:
                self.log_service.info(f'连接参数: 接口={config.get("interface", "SWD")}, 速度={config.get("speed", 4000)}kHz')

            if debugger_type == 'jlink':
                try:
                    device_info = self._device_info_service.get_device_info(jlink_device)
                    log_msg = self._device_info_service.format_device_log(device_info, jlink_device)
                    if self.log_service:
                        self.log_service.info(log_msg)
                except Exception:
                    pass
            elif pyocd_target and self.log_service:
                self.log_service.info(f'[PyOCD 目标] {pyocd_target}')

            self._backend.connect(
                device=jlink_device,
                interface=config.get('interface', 'SWD'),
                speed=config.get('speed', 4000),
                serial_number=config.get('serial_number'),
                ip_address=config.get('ip_address'),
                connect_mode=config.get('connect_mode', 'default'),
                pyocd_target=pyocd_target,
            )

            rtt_mode = config.get('rtt_mode', 'auto')
            rtt_address = None
            range_start = None
            range_end = None

            rtt_cli_flags = ''

            if rtt_mode == 'address':
                rtt_address_str = config.get('rtt_address', '')
                if rtt_address_str:
                    rtt_address = int(rtt_address_str, 16)
                    rtt_cli_flags = f'-a {rtt_address_str}'
                    if self.log_service:
                        self.log_service.info(f'使用指定RTT地址: 0x{rtt_address:X}')

            elif rtt_mode == 'range':
                range_start_str = config.get('rtt_range_start', '')
                range_size_str = config.get('rtt_range_size', '')
                if range_start_str and range_size_str:
                    range_start = int(range_start_str, 16)
                    range_size = int(range_size_str, 16)
                    if range_size <= 0:
                        raise ValueError(f"搜索大小无效: 大小(0x{range_size:X}) 必须>0")
                    range_end = range_start + range_size
                    rtt_cli_flags = f'-a {range_start_str} -s {range_size_str}'
                    if self.log_service:
                        self.log_service.info(f'RTT搜索范围: 起始=0x{range_start:X}, 大小=0x{range_size:X}, 结束=0x{range_end:X}')
                else:
                    raise ValueError("搜索范围模式需要指定起始地址和大小")

            elif rtt_mode == 'auto':
                rtt_cli_flags = ''  # 自动搜索，无需额外参数

            # 在日志中打印等效的命令行字符串，方便排查问题
            if self.log_service and self._backend is not None:
                bt = self._backend.backend_type
                target_str = config.get('device', '') if bt == 'jlink' else config.get('pyocd_target', '')
                speed_val = config.get('speed', 4000)
                mode = config.get('connect_mode', 'under_reset')
                if bt == 'pyocd':
                    cli = f'pyocd rtt --target {target_str} -f {speed_val}k --connect={mode}'
                    if rtt_cli_flags:
                        cli += f' {rtt_cli_flags}'
                elif bt == 'jlink':
                    cli = f'JLinkRTTLogger -Device {target_str} -Interface SWD -Speed {speed_val}'
                    if rtt_cli_flags:
                        cli += f' {rtt_cli_flags}'
                else:
                    cli = f'pyocd rtt --target {target_str}'
                self.log_service.info(f'等效命令行: {cli}')

            if self.log_service:
                self.log_service.info('初始化RTT...')

            self._backend.init_rtt(
                rtt_address=rtt_address,
                rtt_mode=rtt_mode,
                range_start=range_start,
                range_end=range_end,
            )

            self.is_connected = True
            self.connected.emit()

            if self.log_service:
                self.log_service.success('MCU连接成功!')

            return True

        except Exception as e:
            self.is_connected = False
            if self._backend is not None:
                try:
                    self._backend.disconnect()
                except Exception:
                    pass
            error_msg = str(e)
            err_type = type(e).__name__
            hint = ''
            if err_type == 'AssertionError':
                hint = ' (PyOCD内部断言失败，请重试连接)'
            elif 'pop from an empty deque' in error_msg:
                hint = ' (RTT控制块读取异常，请确认MCU已初始化RTT后重试)'
            self.error_occurred.emit(f'{error_msg}{hint}')

            if self.log_service:
                self.log_service.error(f'连接失败: {error_msg}{hint}')

            return False
    
    def disconnect(self):
        """断开连接"""
        if self.log_service:
            self.log_service.info('断开MCU连接')

        if self._backend is not None:
            self._backend.disconnect()

        self.is_connected = False
        self.disconnected.emit()

        if self.log_service:
            self.log_service.success('已断开连接')

    def get_backend(self) -> DebuggerBackend:
        """获取当前调试器后端。"""
        return self._backend

    def get_jlink(self):
        """向后兼容：获取 JLinkRTTWrapper 引用。仅 J-Link 后端可用。"""
        if self._backend is not None and self._backend.backend_type == 'jlink':
            return self._backend.get_wrapper()
        return None
