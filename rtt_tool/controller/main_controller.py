#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
主控制器
协调UI和业务服务
"""

from PyQt5.QtCore import QObject, QDateTime
from ..ui.main_window import MainWindow
from ..service.connection_service import ConnectionService
from ..service.data_receive_service import DataReceiveService
from ..service.data_send_service import DataSendService
from ..service.log_service import LogService
from ..utils.config_service import ConfigService


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
        
        # 创建服务
        self.connection_service = ConnectionService(self.log_service)
        self.receive_service = DataReceiveService()
        self.send_service = DataSendService()
        
        # 状态标志
        self.show_timestamp = False
        self.hex_display = False
        self.rx_bytes = 0  # 接收字节数
        self.tx_bytes = 0  # 发送字节数
        
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
    
    def _on_connect_requested(self, config):
        """连接请求"""
        self.window.set_status("正在连接...")
        
        # 连接
        success = self.connection_service.connect(config)
        
        if success:
            # 启动数据接收
            jlink = self.connection_service.get_jlink()
            self.receive_service.start_receive(jlink)
            self.send_service.set_jlink(jlink)
    
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
            'device': last_config.get('device', 'Cortex-M4'),
            'interface': last_config.get('interface', 'SWD'),
            'speed': last_config.get('speed', 4000),
            'rtt_mode': last_config.get('rtt_mode', 'auto'),
            'rtt_address': last_config.get('rtt_address', ''),
            'rtt_range_start': last_config.get('rtt_range_start', ''),
            'rtt_range_end': last_config.get('rtt_range_end', ''),
        }
        
        # 使用配置连接
        self._on_connect_requested(config)
    
    def _on_disconnect_requested(self):
        """断开连接请求"""
        # 停止数据接收
        self.receive_service.stop_receive()
        
        # 断开连接
        self.connection_service.disconnect()
    
    def _on_reset_counters(self):
        """重置计数器"""
        self.rx_bytes = 0
        self.tx_bytes = 0
        self.window.update_rx_bytes(0)
        self.window.update_tx_bytes(0)
    
    def _on_connected(self):
        """连接成功"""
        self.window.set_connected(True)
        self.window.set_status("已连接")
    
    def _on_disconnected(self):
        """断开连接"""
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
    
    def _on_data_received(self, data):
        """数据接收"""
        # 更新接收字节数
        self.rx_bytes += len(data)
        self.window.update_rx_bytes(self.rx_bytes)
        
        # 格式化数据
        if self.hex_display:
            # HEX格式显示
            text = ' '.join(f'{b:02X}' for b in data)
        else:
            # 字符串格式显示
            text = data.decode('utf-8', errors='replace')
        
        # 添加时间戳 - 在每行前添加
        if self.show_timestamp:
            timestamp = QDateTime.currentDateTime().toString("[yyyy-MM-dd hh:mm:ss.zzz] ")
            # 如果数据包含换行符,在每行前添加时间戳
            if '\n' in text:
                lines = text.split('\n')
                text = '\n'.join(timestamp + line if line else line for line in lines)
            else:
                text = timestamp + text
        
        # 追加到接收区(会自动保存到数据日志文件)
        self.window.append_receive_data(text)
    
    def _on_timestamp_toggled(self, enabled):
        """时间戳开关"""
        self.show_timestamp = enabled
    
    def _on_hex_display_toggled(self, enabled):
        """HEX显示开关"""
        self.hex_display = enabled
    
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
            'device': self.config_service.get('last_device', 'Cortex-M4'),
            'rtt_mode': self.config_service.get('rtt_mode', 'auto'),
            'rtt_address': self.config_service.get('rtt_address', ''),
            'rtt_range_start': self.config_service.get('rtt_range_start', ''),
            'rtt_range_end': self.config_service.get('rtt_range_end', ''),
        }
        self.window.set_last_config(last_config)
    
    def _on_config_changed(self, config):
        """配置改变"""
        # 保存设备型号
        if 'device' in config:
            self.config_service.set('last_device', config['device'])
        
        # 保存RTT模式
        if 'rtt_mode' in config:
            self.config_service.set('rtt_mode', config['rtt_mode'])
        
        # 保存RTT地址
        if 'rtt_address' in config:
            self.config_service.set('rtt_address', config['rtt_address'])
        
        # 保存RTT范围
        if 'rtt_range_start' in config:
            self.config_service.set('rtt_range_start', config['rtt_range_start'])
        
        if 'rtt_range_end' in config:
            self.config_service.set('rtt_range_end', config['rtt_range_end'])
        
        # 保存到文件
        self.config_service.save()
    
    def show(self):
        """显示窗口"""
        self.window.show()
