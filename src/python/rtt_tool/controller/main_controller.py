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
主控制器
协调UI和业务服务
"""

from PyQt5.QtCore import QObject, QDateTime, QThread, QTimer, pyqtSignal
from ..ui.main_window import MainWindow
from ..service.connection_service import ConnectionService
from ..service.data_receive_service import DataReceiveService
from ..service.data_send_service import DataSendService
from ..service.log_service import LogService
from ..utils.config_service import ConfigService
from ..backend.manager import DebuggerManager
from ..processors.log_processor import LogProcessor
from ..processors.waveform_processor import WaveformProcessor
import sys


class _ConnectWorker(QThread):
    """连接工作线程"""
    finished = pyqtSignal(bool)
    error = pyqtSignal(str)

    def __init__(self, connection_service, config, parent=None):
        super().__init__(parent)
        self._connection_service = connection_service
        self._config = config

    def run(self):
        try:
            success = self._connection_service.connect(self._config)
            self.finished.emit(success)
        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit(False)


class _DisconnectWorker(QThread):
    """断开工作线程，避免session.close()/jlink.close()阻塞UI"""
    finished = pyqtSignal()

    def __init__(self, receive_service, connection_service, parent=None):
        super().__init__(parent)
        self._receive_service = receive_service
        self._connection_service = connection_service

    def run(self):
        try:
            self._receive_service.stop_receive()
        except Exception:
            pass
        import time
        time.sleep(0.2)
        try:
            self._connection_service.disconnect()
        except Exception:
            pass
        self.finished.emit()


class MainController(QObject):
    """主控制器"""
    
    def __init__(self):
        super().__init__()
        
        # 创建配置服务
        self.config_service = ConfigService()
        
        # 创建UI
        self.window = MainWindow()
        
        # 加载配置
        self._load_config()
        
        # 创建日志服务
        self.log_service = LogService()
        self.window.log_service = self.log_service
        
        # 创建设备信息服务（全局复用，避免重复解析devices.txt）
        from ..utils.device_info_service import DeviceInfoService
        self.device_info_service = DeviceInfoService(log_service=self.log_service)
        self.window.device_info_service = self.device_info_service
        
        # 创建调试器管理器和服务
        self.debugger_manager = DebuggerManager(log_service=self.log_service)
        self.window._debugger_manager = self.debugger_manager
        self.connection_service = ConnectionService(self.debugger_manager, self.log_service)
        self.receive_service = DataReceiveService()
        self.send_service = DataSendService()
        
        # 创建数据处理器
        self.log_processor = LogProcessor(log_service=self.log_service)
        self.waveform_processor = WaveformProcessor(buffer_size=1024, channels=[1])
        
        # 状态标志
        self.show_timestamp = False
        self.hex_display = False
        self.rx_bytes = 0  # 接收字节数
        self.tx_bytes = 0  # 发送字节数
        
        # 连接超时控制
        self._connect_worker = None
        self._connect_timer = None
        self._connect_timeout = 3
        self._updated_rtt_address = None
        self._pending_connect_config = None
        
        # 连接信号
        self._connect_signals()
        
        # 连接日志服务到日志窗口
        self._connect_log_service()
    
    def _connect_signals(self):
        """连接信号"""
        # UI信号 -> 控制器
        self.window.connect_requested.connect(self._on_connect_requested)
        self.window.quick_connect_requested.connect(self._on_quick_connect_requested)
        self.window.disconnect_requested.connect(self._on_disconnect_requested)
        self.window.send_requested.connect(self._on_send_requested)
        self.window.timestamp_toggled.connect(self._on_timestamp_toggled)
        self.window.hex_display_toggled.connect(self._on_hex_display_toggled)
        self.window.config_changed.connect(self._on_config_changed)
        self.window.reset_counters_requested.connect(self._on_reset_counters)
        
        # ANSI染色开关
        if hasattr(self.window, 'ansi_color_action'):
            self.window.ansi_color_action.toggled.connect(self._on_ansi_color_toggled)
        
        # 关键字高亮开关
        if hasattr(self.window, 'keyword_highlight_action'):
            self.window.keyword_highlight_action.toggled.connect(self._on_keyword_highlight_toggled)
        
        # 连接服务信号 -> 控制器
        self.connection_service.connected.connect(self._on_connected)
        self.connection_service.disconnected.connect(self._on_disconnected)
        self.connection_service.error_occurred.connect(self._on_error)
        
        # 接收服务信号 -> 控制器
        self.receive_service.data_received.connect(self._on_data_received)
        self.receive_service.error_occurred.connect(self._on_error)
        
        # 发送服务信号 -> 控制器
        self.send_service.data_sent.connect(self._on_data_sent)
        self.send_service.error_occurred.connect(self._on_error)
        
        # 数据处理器信号 -> UI
        self.log_processor.text_updated.connect(self._on_log_text_updated)
        self.waveform_processor.waveform_updated.connect(self._on_waveform_updated)
        
        # 接收服务信号 -> 处理器分发
        self.receive_service.data_received.connect(self._on_data_received_dispatch)
        
        # 模式切换信号
        self.window.mode_changed.connect(self._on_mode_changed)
    
    def _on_connect_requested(self, config):
        """连接请求"""
        from datetime import datetime
        if self.log_service:
            self.log_service.debug(f"[性能] 开始连接请求: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
        
        self.window.set_status("正在连接...")
        self._updated_rtt_address = None
        
        # MAP文件前置校验
        is_valid, rtt_address, error_msg = self._validate_map_file(config)
        if not is_valid:
            self.window.set_status(f"连接失败: {error_msg}")
            if self.log_service:
                self.log_service.error(error_msg)
            return
        if rtt_address:
            config['rtt_address'] = rtt_address
            self._updated_rtt_address = rtt_address
            if self.log_service:
                self.log_service.success(f"已从map文件更新RTT地址: {rtt_address}")
        
        # 启动带超时的异步连接
        self._start_connect_with_timeout(config)

    def _validate_map_file(self, config):
        """MAP文件前置校验"""
        rtt_mode = config.get('rtt_mode', 'auto')
        map_file_path = config.get('map_file_path', '')
        
        if rtt_mode != 'address' or not map_file_path:
            return True, None, None
        
        from ..utils.map_file_parser import MapFileParser
        addr, error = MapFileParser.search_symbol(map_file_path, self.log_service)
        
        if error:
            if "文件不存在" in error:
                return False, None, f"MAP文件不存在: {map_file_path}"
            elif "不是有效文件" in error:
                return False, None, f"MAP文件无效: {map_file_path} 不是有效文件"
            elif "未找到符号" in error:
                return False, None, "MAP文件中未找到SEGGER_RTT符号"
            elif "无法识别文件编码" in error:
                return False, None, "MAP文件编码无法识别"
            else:
                return False, None, f"MAP文件解析失败: {error}"
        
        return True, addr, None

    def _start_connect_with_timeout(self, config, timeout=10):
        """启动带超时的异步连接"""
        self._connect_timeout = timeout
        self._pending_connect_config = config

        # 创建工作线程
        self._connect_worker = _ConnectWorker(self.connection_service, config, self)
        self._connect_worker.finished.connect(self._on_connect_worker_finished)
        self._connect_worker.error.connect(self._on_connect_worker_error)

        # 创建超时定时器
        self._connect_timer = QTimer()
        self._connect_timer.setSingleShot(True)
        self._connect_timer.timeout.connect(self._on_connect_timeout)
        self._connect_timer.start(timeout * 1000)

        if self.log_service:
            from datetime import datetime
            self.log_service.debug(
                f"[性能] 启动异步连接(超时{timeout}s): {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")

        self._connect_worker.start()

    def _on_connect_worker_finished(self, success):
        """连接Worker完成回调"""
        if self._connect_timer:
            self._connect_timer.stop()
            self._connect_timer = None

        if success:
            backend = self.connection_service.get_backend()
            if backend:
                # 启动数据接收
                self.receive_service.start_receive(backend)
                self.send_service.set_backend(backend)

                # 更新UI状态
                self.window.set_connected(True)
                self.window.set_status("已连接")

                # 保存更新的RTT地址
                if self._updated_rtt_address:
                    self.window.last_config['rtt_address'] = self._updated_rtt_address
                    self.config_service.set('rtt_address', self._updated_rtt_address)
                    self.config_service.save()
                    if self.log_service:
                        self.log_service.info(f"已保存更新后的RTT地址到配置: {self._updated_rtt_address}")
            else:
                self.window.set_connected(False)
                self.window.set_status("连接失败")
        else:
            self.window.set_connected(False)
            self.window.set_status("连接失败")

        self._connect_worker = None
        self._pending_connect_config = None

    def _on_connect_worker_error(self, error_msg):
        """连接Worker错误回调"""
        if self.log_service:
            self.log_service.error(f"连接错误: {error_msg}")
        self.window.set_status(f"连接失败: {error_msg}")

    def _on_connect_timeout(self):
        """连接超时回调"""
        timeout = self._connect_timeout

        if self._connect_worker and self._connect_worker.isRunning():
            self._connect_worker.terminate()
            self._connect_worker.wait(2000)

        try:
            self.connection_service.disconnect()
        except Exception:
            pass

        self.window.set_connected(False)
        self.window.set_status(f"连接超时({timeout}s)")
        if self.log_service:
            self.log_service.error(f"连接超时: {timeout}秒内未完成连接")

        self._connect_worker = None
        self._connect_timer = None
        self._pending_connect_config = None
    
    def _on_quick_connect_requested(self):
        """快速连接请求 - 使用上次配置"""
        # 获取上次配置
        last_config = self.window.last_config
        
        if not last_config:
            # 如果没有上次配置,提示用户先配置
            self.window.set_status("请先配置连接参数")
            return
        
        # 构建完整的配置
        config = {
            'debugger_type': last_config.get('debugger_type', 'jlink'),
            'serial_number': last_config.get('serial_number'),
            'device': last_config.get('device', 'Cortex-M4'),
            'interface': last_config.get('interface', 'SWD'),
            'speed': last_config.get('speed', 4000),
            'connect_mode': last_config.get('connect_mode', 'default'),
            'pyocd_target': last_config.get('pyocd_target', ''),
            'rtt_mode': last_config.get('rtt_mode', 'auto'),
            'rtt_address': last_config.get('rtt_address', ''),
            'rtt_range_start': last_config.get('rtt_range_start', ''),
            'rtt_range_size': last_config.get('rtt_range_size', ''),
            'map_file_path': last_config.get('map_file_path', ''),
        }
        
        # 使用配置连接
        self._on_connect_requested(config)
    
    def _on_disconnect_requested(self):
        """断开连接请求 - 异步执行避免UI阻塞"""
        self.window.set_status("正在断开...")
        self.window.set_connected(False)

        self._disconnect_worker = _DisconnectWorker(
            self.receive_service, self.connection_service, self
        )

        def _on_disconnect_done():
            self.window._jlink_ref = None
            self.window.set_status("未连接")

        self._disconnect_worker.finished.connect(_on_disconnect_done)
        self._disconnect_worker.start()
    
    def _on_reset_counters(self):
        """重置计数器"""
        self.rx_bytes = 0
        self.tx_bytes = 0
        self.window.update_rx_bytes(0)
        self.window.update_tx_bytes(0)
    
    def _on_connected(self):
        """连接成功"""
        jlink_wrapper = self.connection_service.get_jlink()
        if jlink_wrapper and jlink_wrapper.jlink:
            self.window._jlink_ref = jlink_wrapper.jlink
        else:
            backend = self.connection_service.get_backend()
            if backend is not None:
                self.window._jlink_ref = None
        self.window.set_connected(True)
        self.window.set_status("已连接")
    
    def _on_disconnected(self):
        """断开连接"""
        self.window._jlink_ref = None
        self.window.set_connected(False)
        self.window.set_status("未连接")
    
    def _on_send_requested(self, text, is_hex, add_newline):
        """发送请求"""
        try:
            if is_hex:
                num_bytes = self.send_service.send_hex(text)
            else:
                num_bytes = self.send_service.send_string(text, add_newline)
            
            # 记录发送日志
            self.log_service.add_log(f"发送数据: {text[:50]}{'...' if len(text) > 50 else ''} (模式: {'HEX' if is_hex else '字符串'})", 'INFO')
        except Exception as e:
            self.log_service.add_log(f"发送失败: {str(e)}", 'ERROR')
            self.window.set_status(f"发送失败: {str(e)}")
    
    def _on_data_sent(self, num_bytes):
        """数据发送完成"""
        # 更新发送字节数
        self.tx_bytes += num_bytes
        self.window.update_tx_bytes(self.tx_bytes)
        # 记录日志
        self.log_service.add_log(f"发送完成: {num_bytes} 字节", 'SUCCESS')
    
    def _on_data_received_dispatch(self, channel, data):
        """数据接收分发到处理器"""
        self.rx_bytes += len(data)
        self.window.update_rx_bytes(self.rx_bytes)
        
        if channel in self.log_processor.get_supported_channels():
            self.log_processor.process(channel, data)
        if channel in self.waveform_processor.get_supported_channels():
            self.waveform_processor.process(channel, data)
    
    def _on_log_text_updated(self, channel, text):
        """日志文本更新"""
        self.window.append_receive_data(text)
    
    def _on_waveform_updated(self, channel, values):
        """波形数据更新"""
        timestamps, all_values = self.waveform_processor.get_buffer_data(channel)
        self.window.waveform_widget.update_data(channel, timestamps, all_values)
    
    def _on_mode_changed(self, mode):
        """显示模式切换"""
        if self.log_service:
            self.log_service.info(f'显示模式切换: {mode}')
    
    def _on_data_received(self, channel, data):
        """数据接收（已废弃，由 _on_data_received_dispatch + LogProcessor 处理）"""
        pass
    
    def _on_timestamp_toggled(self, enabled):
        """时间戳开关"""
        self.show_timestamp = enabled
        self.log_processor.set_timestamp_enabled(enabled)
    
    def _on_hex_display_toggled(self, enabled):
        """HEX显示开关"""
        self.hex_display = enabled
        self.log_processor.set_hex_mode(enabled)
    
    def _on_error(self, error_msg):
        """错误处理"""
        self.window.set_status(f"错误: {error_msg}")
        # 添加到系统日志
        self.log_service.add_log(f"错误: {error_msg}", 'ERROR')
    
    def _connect_log_service(self):
        """连接日志服务到日志窗口"""
        # 创建日志窗口(如果还没有)
        log_window = self.window.get_log_window()
        if log_window is None:
            from rtt_tool.ui.log_window import LogWindow
            log_window = LogWindow()
            self.window.log_window = log_window
        
        # 设置日志服务到日志窗口
        log_window.set_log_service(self.log_service)
    
    def _load_config(self):
        """加载配置"""
        # 加载连接配置
        last_config = {
            'debugger_type': self.config_service.get('debugger_type', 'jlink'),
            'serial_number': self.config_service.get('last_serial_number', None),
            'device': self.config_service.get('last_device', 'Cortex-M4'),
            'connect_mode': self.config_service.get('connect_mode', 'default'),
            'pyocd_target': self.config_service.get('pyocd_target', ''),
            'rtt_mode': self.config_service.get('rtt_mode', 'auto'),
            'rtt_address': self.config_service.get('rtt_address', ''),
            'rtt_range_start': self.config_service.get('rtt_range_start', ''),
            'rtt_range_size': self.config_service.get('rtt_range_size', ''),
            'map_file_path': self.config_service.get('map_file_path', ''),
            'probe_name': self.config_service.get('probe_name', ''),
            'probe_backend': self.config_service.get('probe_backend', ''),
            'probe_serial': self.config_service.get('probe_serial', ''),
        }
        self.window.set_last_config(last_config)
        
        # 恢复ANSI染色开关
        ansi_enabled = self.config_service.get('ansi_color_enabled', False)
        if hasattr(self.window, 'ansi_color_action'):
            self.window.ansi_color_action.setChecked(ansi_enabled)
        
        # 恢复关键字高亮开关
        keyword_enabled = self.config_service.get('keyword_highlight_enabled', True)
        if hasattr(self.window, 'keyword_highlight_action'):
            self.window.keyword_highlight_action.setChecked(keyword_enabled)
        
        # 恢复关键字高亮规则
        keyword_rules = self.config_service.get('keyword_rules', {})
        if keyword_rules:
            self.window._keyword_rules = dict(keyword_rules)
    
    def _on_config_changed(self, config):
        """配置改变"""
        # 保存调试器类型
        if 'debugger_type' in config:
            self.config_service.set('debugger_type', config['debugger_type'])
        
        # 保存序列号
        if 'serial_number' in config:
            self.config_service.set('last_serial_number', config['serial_number'])
        
        # 保存设备型号
        if 'device' in config:
            self.config_service.set('last_device', config['device'])

        # 保存连接模式
        if 'connect_mode' in config:
            self.config_service.set('connect_mode', config['connect_mode'])

        # 保存PyOCD目标
        if 'pyocd_target' in config:
            self.config_service.set('pyocd_target', config['pyocd_target'])

        # 保存RTT模式
        if 'rtt_mode' in config:
            self.config_service.set('rtt_mode', config['rtt_mode'])
        
        # 保存RTT地址
        if 'rtt_address' in config:
            self.config_service.set('rtt_address', config['rtt_address'])
        
        # 保存RTT范围
        if 'rtt_range_start' in config:
            self.config_service.set('rtt_range_start', config['rtt_range_start'])
        
        if 'rtt_range_size' in config:
            self.config_service.set('rtt_range_size', config['rtt_range_size'])
        
        # 保存map文件路径
        if 'map_file_path' in config:
            self.config_service.set('map_file_path', config['map_file_path'])

        # 保存探针信息
        if 'probe_name' in config:
            self.config_service.set('probe_name', config['probe_name'])
        if 'probe_backend' in config:
            self.config_service.set('probe_backend', config['probe_backend'])
        if 'probe_serial' in config:
            self.config_service.set('probe_serial', config['probe_serial'])
        
        # 保存到文件
        self.config_service.save()
    
    def _on_ansi_color_toggled(self, checked):
        """ANSI染色开关切换"""
        self.config_service.set('ansi_color_enabled', checked)
        self.config_service.save()
    
    def _on_keyword_highlight_toggled(self, checked):
        """关键字高亮开关切换"""
        self.config_service.set('keyword_highlight_enabled', checked)
        self.config_service.save()
        
        keyword_rules = getattr(self.window, '_keyword_rules', {})
        if keyword_rules:
            self.config_service.set('keyword_rules', keyword_rules)
            self.config_service.save()
    
    def show(self):
        """显示窗口"""
        self.window.show()
