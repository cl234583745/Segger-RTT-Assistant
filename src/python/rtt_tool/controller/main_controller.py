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

from PyQt5.QtCore import Qt, QObject, QDateTime, QThread, QTimer, pyqtSignal
from ..ui.main_window import MainWindow
from ..service.connection_service import ConnectionService
from ..service.data_receive_service import DataReceiveService
from ..service.data_send_service import DataSendService
from ..service.log_service import LogService
from ..utils.config_service import ConfigService
from ..backend.manager import DebuggerManager
from ..processors.log_processor import LogProcessor
from ..processors.waveform_processor import WaveformProcessor
from ..processors.high_speed_waveform_processor import HighSpeedWaveformProcessor
from .acquisition_state_machine import AcquisitionStateMachine
import sys


class _ConnectWorker(QThread):
    """连接工作线程"""
    finished = pyqtSignal(bool)
    error = pyqtSignal(str)

    def __init__(self, connection_service, config, parent=None):
        super().__init__(parent)
        self._connection_service = connection_service
        self._config = config
        self._aborted = False

    def run(self):
        try:
            success = self._connection_service.connect(self._config)
            if not self._aborted:
                self.finished.emit(success)
        except Exception as e:
            if not self._aborted:
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


class _HSBridge(QObject):
    """桥接对象：主线程信号 → HS线程槽，用于跨线程安全调用。"""
    data_ready = pyqtSignal(int, bytes)
    reset_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    start_requested = pyqtSignal()
    sampling_rate_changed = pyqtSignal(float)


class MainController(QObject):
    """主控制器"""

    _INIT_PHASE1_LABELS = ["Config", "MainWindow", "LoadConfig"]
    _INIT_PHASE2_LABELS = ["LogService", "Services", "Processors", "HS", "Remainder"]

    def __init__(self):
        super().__init__()
        import time as _time
        _t0 = _time.perf_counter()

        self.config_service = ConfigService()
        self.window = MainWindow()
        self._load_config()
        _t1 = _time.perf_counter()

        # 尽快显示窗口，重初始化延迟到事件循环中
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            app.aboutToQuit.connect(self._cleanup)
        self.window.show()

        print(f"[perf] Phase1(window): {(_t1-_t0)*1000:.0f}ms")

        # 预初始化引用为 None
        self.log_service = None
        self.window.log_service = None
        self.device_info_service = None
        self.window.device_info_service = None
        self.debugger_manager = None
        self.window._debugger_manager = None
        self.connection_service = None
        self.receive_service = None
        self.send_service = None
        self.log_processor = None
        self.waveform_processor = None
        self._hs_thread = None
        self._hs_processor = None
        self._hs_bridge = None
        self._acquisition_sm = None
        self._rate_timer = None
        self._use_high_speed = False
        self._sample_rate_hz = 0
        self._rate_sample_count = 0
        self._rate_check_interval = 0
        self._last_mode_hint_shown = None
        self._render_paused = False
        self.show_timestamp = False
        self.hex_display = False
        self.rx_bytes = 0
        self.tx_bytes = 0
        self._connect_worker = None
        self._connect_timer = None
        self._connect_timeout = 3
        self._updated_rtt_address = None
        self._pending_connect_config = None

        # UI 信号（不依赖 services）
        self._connect_ui_signals()

        # 延迟加载重初始化
        QTimer.singleShot(0, self._init_phase2)
    
    def _connect_ui_signals(self):
        """Phase 1 信号连接：仅依赖窗口自身，无需业务服务。"""
        self.window.timestamp_toggled.connect(self._on_timestamp_toggled)
        self.window.hex_display_toggled.connect(self._on_hex_display_toggled)
        self.window.config_changed.connect(self._on_config_changed)
        self.window.reset_counters_requested.connect(self._on_reset_counters)
        self.window.font_changed.connect(self._on_font_changed)
        if hasattr(self.window, 'ansi_color_action'):
            self.window.ansi_color_action.toggled.connect(self._on_ansi_color_toggled)
        if hasattr(self.window, 'keyword_highlight_action'):
            self.window.keyword_highlight_action.toggled.connect(self._on_keyword_highlight_toggled)
        self.window._pin_btn.toggled.connect(self._on_pin_save)

    def _connect_service_signals(self):
        """Phase 2 信号连接：需要业务服务已就绪。"""
        self.window.connect_requested.connect(self._on_connect_requested)
        self.window.quick_connect_requested.connect(self._on_quick_connect_requested)
        self.window.disconnect_requested.connect(self._on_disconnect_requested)
        self.window.send_requested.connect(self._on_send_requested)

        self.connection_service.connected.connect(self._on_connected)
        self.connection_service.disconnected.connect(self._on_disconnected)
        self.connection_service.error_occurred.connect(self._on_error)

        self.receive_service.data_received.connect(self._on_data_received)
        self.receive_service.error_occurred.connect(self._on_error)

        self.send_service.data_sent.connect(self._on_data_sent)
        self.send_service.error_occurred.connect(self._on_error)

        self.log_processor.text_updated.connect(self._on_log_text_updated)
        self.waveform_processor.waveform_updated.connect(self._on_waveform_updated)
        self._hs_processor.waveform_updated.connect(self._on_hs_waveform_updated)

        self.receive_service.data_received.connect(self._on_data_received_dispatch)

        self.window.mode_changed.connect(self._on_mode_changed)
        self.window.waveform_widget.acquisition_start.connect(self._on_acquisition_start)
        self.window.waveform_widget.acquisition_stop.connect(self._on_acquisition_stop)
        self.window.waveform_widget.acquisition_pause.connect(self._on_acquisition_pause)
        self.window.waveform_widget.acquisition_resume.connect(self._on_acquisition_resume)
        self.window.waveform_widget.sampling_rate_changed.connect(self.waveform_processor.set_sampling_rate)
        self.window.waveform_widget.sampling_rate_changed.connect(self._hs_bridge.sampling_rate_changed)
        self.window.waveform_widget.theme_changed.connect(self._on_theme_save)

        self._acquisition_sm.state_changed.connect(self._on_acquisition_state_changed)
        self.connection_service.disconnected.connect(self._on_device_disconnected_for_acquisition)

        self._rate_timer = QTimer()
        self._rate_timer.setInterval(2000)
        self._rate_timer.timeout.connect(self._on_rate_check)
        self._rate_timer.start()

    def _init_phase2(self):
        """Phase 2：延迟加载的后端、服务、处理器。"""
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import QEventLoop
        QApplication.processEvents(QEventLoop.ExcludeUserInputEvents)

        try:
            self._init_phase2_impl()
        except Exception as e:
            import traceback
            err = f"后台初始化失败: {e}"
            print(f"[error] {err}")
            traceback.print_exc()
            if self.log_service:
                self.log_service.error(err)
            self.window.set_status(err)

    def _init_phase2_impl(self):
        """Phase 2 实际初始化逻辑（被 _init_phase2 的 try/except 包裹）。"""
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import QEventLoop
        import time as _time
        _t0 = _time.perf_counter()

        self.log_service = LogService()
        self.window.log_service = self.log_service
        _t1 = _time.perf_counter()

        from ..utils.device_info_service import DeviceInfoService
        self.device_info_service = DeviceInfoService(log_service=self.log_service)
        self.window.device_info_service = self.device_info_service

        self.window.set_status("正在加载调试器后端...")
        QApplication.processEvents(QEventLoop.ExcludeUserInputEvents)

        self.debugger_manager = DebuggerManager(log_service=self.log_service)
        self.window._debugger_manager = self.debugger_manager
        self.connection_service = ConnectionService(self.debugger_manager, self.log_service)
        self.receive_service = DataReceiveService()
        self.send_service = DataSendService()
        _t2 = _time.perf_counter()

        self.window.set_status("正在初始化处理器...")
        QApplication.processEvents(QEventLoop.ExcludeUserInputEvents)

        self.log_processor = LogProcessor(log_service=self.log_service)
        self.waveform_processor = WaveformProcessor(
            buffer_size=1024, channels=[1], data_log_handle=self.window.data_log_handle)
        _t3 = _time.perf_counter()

        self._hs_thread = QThread()
        self._hs_processor = HighSpeedWaveformProcessor(buffer_size=1000000)
        self._hs_processor.moveToThread(self._hs_thread)
        self._hs_thread.start()

        self._hs_bridge = _HSBridge()
        self._hs_bridge.data_ready.connect(self._hs_processor.process_data)
        self._hs_bridge.reset_requested.connect(self._hs_processor.reset)
        self._hs_bridge.stop_requested.connect(self._hs_processor.stop)
        self._hs_bridge.start_requested.connect(self._hs_processor.start)
        self._hs_bridge.sampling_rate_changed.connect(self._hs_processor.set_sampling_rate)

        self._acquisition_sm = AcquisitionStateMachine()
        _t4 = _time.perf_counter()

        self._connect_service_signals()
        self._connect_log_service()

        self.window.set_status("就绪")
        _t5 = _time.perf_counter()
        _labels = self._INIT_PHASE2_LABELS
        _durs = [(_t1-_t0), (_t2-_t1), (_t3-_t2), (_t4-_t3), (_t5-_t4)]
        _msg = "[perf] Phase2(backend): total={:.0f}ms  ".format((_t5-_t0)*1000) + \
               "  ".join(f"{l}={d*1000:.0f}ms" for l,d in zip(_labels, _durs))
        print(_msg)
        self.log_service.info(_msg)
    
    def _on_connect_requested(self, config):
        """连接请求"""
        if not self.connection_service:
            self.window.set_status("正在初始化...")
            return
        from datetime import datetime
        if self.log_service:
            self.log_service.debug(f"[性能] 开始连接请求: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
        
        self.window.set_status("连接中")
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
                # 启动数据接收 - 同时监听通道0(日志)和通道1(示波器)
                self.receive_service.start_receive(backend, channels=[0, 1])
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

        worker = self._connect_worker
        if worker and worker.isRunning():
            worker._aborted = True
            try:
                self.connection_service.disconnect()
            except Exception:
                pass
            if not worker.wait(3000):
                if self.log_service:
                    self.log_service.warning(
                        f"连接工作线程在超时后未能及时退出，将继续在后台完成")

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
        self._use_high_speed = False
        self._hs_bridge.stop_requested.emit()
        self._rate_timer.stop()

        self._disconnect_worker = _DisconnectWorker(
            self.receive_service, self.connection_service, self
        )

        def _on_disconnect_done():
            self.window._jlink_ref = None
            self.window.set_status("未连接")
            self._rate_timer.start()

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
        self._auto_detect_jscope_format()
    
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
        
        # 示波器数据处理
        acquisition_active = self._acquisition_sm.is_running() or self._acquisition_sm.is_paused()
        channel_supported = channel in self.waveform_processor.get_supported_channels()
        
        if acquisition_active and channel_supported:
            # 估算数据速率（无论哪种模式都计数）
            self._rate_sample_count += len(data)
            
            if self._use_high_speed:
                self._hs_bridge.data_ready.emit(channel, data)
            else:
                self.waveform_processor.process(channel, data)
        elif channel == 1 and not acquisition_active:
            if not hasattr(self, '_ch1_warning_shown'):
                self._ch1_warning_shown = True
                if self.log_service:
                    self.log_service.warning(f"[示波器] CH{channel} 接收到数据但采集未启动，请点击'开始'按钮")
    
    def _on_log_text_updated(self, channel, text):
        """日志文本更新"""
        self.window.append_receive_data(text)
    
    def _on_waveform_updated(self, channel, values):
        """波形数据更新（普通处理器）"""
        if self._render_paused or self._use_high_speed:
            return
        
        timestamps, all_values = self.waveform_processor.get_buffer_data(channel)
        self.window.waveform_widget.update_data(channel, timestamps, all_values)

    def _on_hs_waveform_updated(self, channel, timestamps, values):
        """波形数据更新（高速处理器 - 已降采样）"""
        if self._render_paused or not self._use_high_speed:
            return
        
        self.window.waveform_widget.update_data(channel, timestamps, values)
    
    def _on_mode_changed(self, mode):
        """显示模式切换"""
        if self.log_service:
            self.log_service.info(f'[模式切换] 切换到: {mode}')
            self.log_service.info(f'[模式切换] 当前示波器配置:')
            self.log_service.info(f'  - 数据格式: {self.waveform_processor.get_data_format().value}')
            self.log_service.info(f'  - 监听通道: {self.waveform_processor.get_supported_channels()}')
            self.log_service.info(f'  - 采集状态: {self._acquisition_sm.current_state().value}')
            self.log_service.info(f'  - 渲染暂停: {self._render_paused}')
    
    def _on_data_received(self, channel, data):
        """数据接收（已废弃，由 _on_data_received_dispatch + LogProcessor 处理）"""
        pass
    
    def _on_timestamp_toggled(self, enabled):
        """时间戳开关"""
        self.show_timestamp = enabled
        if self.log_processor:
            self.log_processor.set_timestamp_enabled(enabled)
    
    def _on_hex_display_toggled(self, enabled):
        """HEX显示开关"""
        self.hex_display = enabled
        if self.log_processor:
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
            'interface': self.config_service.get('interface', 'SWD'),
            'speed': self.config_service.get('speed', 4000),
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

        # 恢复主题（全局限定样式 + 波形组件 + 工具菜单勾选）
        theme = self.config_service.get('color_theme', 'dark')
        self.window.set_app_theme(theme)

        # 恢复字体
        font_family = self.config_service.get('font_family', 'Courier New')
        font_size = self.config_service.get('font_size', 10)
        from PyQt5.QtGui import QFont
        self.window.receive_text.setFont(QFont(font_family, font_size))

        # 恢复置顶状态（blockSignals 防止误触发保存）
        topmost = self.config_service.get('window_topmost', False)
        self.window._pin_btn.blockSignals(True)
        self.window._pin_btn.setChecked(topmost)
        self.window._pin_btn.blockSignals(False)
        if topmost:
            self.window.setWindowFlag(Qt.WindowStaysOnTopHint, True)
            self.window.show()
    
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

        # 保存接口
        if 'interface' in config:
            self.config_service.set('interface', config['interface'])

        # 保存速度
        if 'speed' in config:
            self.config_service.set('speed', config['speed'])

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

    def _on_theme_save(self, theme):
        self.config_service.set('color_theme', theme)
        self.config_service.save()
        self.window.set_app_theme(theme)

    def _on_pin_save(self, checked):
        self.config_service.set('window_topmost', checked)
        self.config_service.save()

    def _on_font_changed(self, font):
        from PyQt5.QtGui import QFont
        self.config_service.set('font_family', font.family())
        self.config_service.set('font_size', font.pointSize())
        self.config_service.save()

    def _auto_detect_jscope_format(self) -> None:
        """连接成功后，自动读取RTT通道名、缓冲区大小并设置格式"""
        channel_name = None
        mcu_buf_info = {}
        try:
            backend = self.connection_service.get_backend()
            if backend is None:
                return
            if hasattr(backend, '_wrapper') and hasattr(backend._wrapper, 'jlink') and backend._wrapper.jlink:
                jlink = backend._wrapper.jlink
                for ch_idx in range(4):
                    try:
                        desc = jlink.rtt_get_buf_descriptor(ch_idx, up=True)
                        name = desc.acName.decode() if isinstance(desc.acName, bytes) else desc.acName
                        if desc.SizeOfBuffer > 0:
                            mcu_buf_info[ch_idx] = (desc.SizeOfBuffer, name)
                        if name and name.startswith("JScope_"):
                            channel_name = name
                    except Exception:
                        continue
            elif hasattr(backend, '_rtt_cb') and backend._rtt_cb is not None:
                for ch_idx, ch in enumerate(backend._rtt_cb.up_channels):
                    name = getattr(ch, 'name', None)
                    if name and isinstance(name, (str, bytes)):
                        if isinstance(name, bytes):
                            name = name.decode()
                        if name.startswith("JScope_"):
                            channel_name = name
                    try:
                        buf_size = getattr(ch, 'size', 0) or 0
                        if buf_size > 0:
                            mcu_buf_info[ch_idx] = (buf_size, name or f"Up[{ch_idx}]")
                    except Exception:
                        pass
        except Exception:
            pass

        if channel_name:
            self.waveform_processor.set_jscope_format(channel_name)
        format_text = self.waveform_processor.get_format_text()
        self.window.waveform_widget.set_format_text(format_text)

        if mcu_buf_info:
            last_ch = max(mcu_buf_info.keys())
            size, name = mcu_buf_info[last_ch]
            self.window.waveform_widget.set_mcu_buffer_info(last_ch, size, name)
            if self.log_service:
                for ch, (sz, nm) in sorted(mcu_buf_info.items()):
                    self.log_service.info(f"  MCU缓冲 CH{ch}: \"{nm}\" 大小={sz}B")

    def _on_acquisition_start(self) -> None:
        if not self.connection_service.is_connected:
            self.window.set_status("请先连接设备")
            if self.log_service:
                self.log_service.warning("[示波器] 无法启动采集: 设备未连接")
            return
        
        # 记录当前配置
        current_format = self.waveform_processor.get_data_format()
        supported_channels = self.waveform_processor.get_supported_channels()
        if self.log_service:
            self.log_service.info(f"[示波器] 开始采集 - 格式: {current_format.value}, 监听通道: {supported_channels}")
        
        self._acquisition_sm.start()
        self._render_paused = False
        self._rate_sample_count = 0
        self._last_mode_hint_shown = None
        self._hs_bridge.start_requested.emit()

    def _on_acquisition_stop(self) -> None:
        if self.log_service:
            self.log_service.info("[示波器] 停止采集")
        self._acquisition_sm.stop()
        self._render_paused = False
        self._use_high_speed = False
        self._hs_bridge.stop_requested.emit()
        self._hs_bridge.reset_requested.emit()
        self._rate_sample_count = 0
        try:
            self.waveform_processor.reset()
        except Exception:
            pass
        # 清除曲线数据但保留通道配置
        for ch in self.waveform_processor.get_supported_channels():
            if ch in self.window.waveform_widget._channels:
                self.window.waveform_widget._channels[ch]['curve'].setData([], [])

    def _on_acquisition_pause(self) -> None:
        self._acquisition_sm.pause()
        self._render_paused = True
        if self._use_high_speed:
            self._hs_bridge.stop_requested.emit()

    def _on_acquisition_resume(self) -> None:
        self._acquisition_sm.resume()
        self._render_paused = False
        if not self._use_high_speed:
            for ch in self.waveform_processor.get_supported_channels():
                timestamps, values = self.waveform_processor.get_buffer_data(ch)
                self.window.waveform_widget.update_data(ch, timestamps, values)
        else:
            self._hs_bridge.start_requested.emit()

    def _on_acquisition_state_changed(self, state: str) -> None:
        self.window.waveform_widget.update_acquisition_buttons(state)

    def _on_device_disconnected_for_acquisition(self) -> None:
        self._acquisition_sm.on_device_disconnected()
        self._render_paused = False

    def _on_rate_check(self):
        """每2秒检查一次数据速率，自动切换高速/普通模式。"""
        if not (self._acquisition_sm.is_running() or self._acquisition_sm.is_paused()):
            self._rate_sample_count = 0
            return

        rate_bytes_per_sec = self._rate_sample_count / 2.0
        self._rate_sample_count = 0

        approx_samples_per_sec = rate_bytes_per_sec / 2

        if approx_samples_per_sec > 5000 and not self._use_high_speed:
            self._set_high_speed_mode(True)
            if self._last_mode_hint_shown != 'hs':
                self._last_mode_hint_shown = 'hs'
                if self.log_service:
                    self.log_service.info(
                        f"[示波器] 自动切换到高速模式 (数据速率: {approx_samples_per_sec:.0f} 样本/秒)")
        elif approx_samples_per_sec < 2000 and self._use_high_speed:
            self._set_high_speed_mode(False)
            if self._last_mode_hint_shown != 'normal':
                self._last_mode_hint_shown = 'normal'
                if self.log_service:
                    self.log_service.info(
                        f"[示波器] 自动切换到普通模式 (数据速率: {approx_samples_per_sec:.0f} 样本/秒)")

    def _set_high_speed_mode(self, enabled: bool):
        if enabled == self._use_high_speed:
            return

        self._use_high_speed = enabled
        if enabled:
            fmt_text = self.waveform_processor.get_format_text()
            fmt = self.waveform_processor.get_data_format()
            sampling_interval = self.window.waveform_widget._sampling_interval
            rate_hz = 1.0 / sampling_interval if sampling_interval > 0 else 0
            jscope_ok = False
            if hasattr(self, '_auto_detect_jscope_format'):
                try:
                    backend = self.connection_service.get_backend()
                    if backend:
                        if hasattr(backend, '_wrapper') and hasattr(backend._wrapper, 'jlink') and backend._wrapper.jlink:
                            jlink = backend._wrapper.jlink
                            for ch_idx in range(4):
                                try:
                                    desc = jlink.rtt_get_buf_descriptor(ch_idx, up=True)
                                    name = desc.acName.decode() if isinstance(desc.acName, bytes) else desc.acName
                                    if name and name.startswith("JScope_"):
                                        self._hs_processor.set_jscope_format(name)
                                        jscope_ok = True
                                        break
                                except Exception:
                                    continue
                except Exception:
                    pass
            if not jscope_ok:
                self._hs_processor.set_data_format(fmt)
            self._hs_processor.set_sampling_rate(rate_hz)
            self.waveform_processor.reset()
        else:
            self._hs_bridge.reset_requested.emit()

        hint = "高速" if enabled else "普通"
        if self.log_service:
            self.log_service.info(f"[示波器] 采集模式: {hint}")
        self.window.waveform_widget.set_format_text(
            f"{self.waveform_processor.get_format_text()} [模式:{hint}]")

    def show(self):
        """显示窗口（窗口已在 __init__ 中显示）"""
        pass

    def _cleanup(self):
        if self._hs_processor:
            self._hs_processor.stop()
        if self._rate_timer:
            self._rate_timer.stop()
        if self._hs_thread and self._hs_thread.isRunning():
            self._hs_thread.quit()
            self._hs_thread.wait(3000)
