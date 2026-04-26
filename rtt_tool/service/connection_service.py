#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
连接管理服务
管理MCU连接状态，发射连接状态变化信号
"""

from PyQt5.QtCore import QObject, pyqtSignal
from ..infrastructure.jlink_rtt_wrapper import JLinkRTTWrapper


class ConnectionService(QObject):
    """连接管理服务"""
    
    # 信号定义
    connected = pyqtSignal()  # 连接成功信号
    disconnected = pyqtSignal()  # 断开连接信号
    error_occurred = pyqtSignal(str)  # 错误信号
    
    def __init__(self, log_service=None):
        super().__init__()
        self.jlink = None
        self.is_connected = False
        self.log_service = log_service
    
    def connect(self, config):
        """
        连接到MCU
        
        Args:
            config: 连接配置字典，包含：
                - device: MCU型号
                - interface: 接口类型
                - speed: 接口速度（kHz）
                - jlink_path: JLink DLL路径（可选）
                - serial_number: JLink序列号（可选）
                - ip_address: JLink IP地址（可选）
                - rtt_mode: RTT模式（auto/address/range）
                - rtt_address: RTT控制块地址（可选）
        
        Returns:
            bool: 连接是否成功
        """
        try:
            # 记录日志
            if self.log_service:
                self.log_service.info(f'开始连接MCU: {config.get("device", "Cortex-M4")}')
            
            # 创建JLink RTT封装
            if self.jlink is None:
                if self.log_service:
                    self.log_service.info('初始化JLink RTT封装')
                self.jlink = JLinkRTTWrapper(config.get('jlink_path'))
                if self.log_service:
                    self.log_service.info(f'JLink DLL路径: {self.jlink.jlink_path}')
            
            # 连接
            if self.log_service:
                self.log_service.info(f'连接参数: 接口={config.get("interface", "SWD")}, 速度={config.get("speed", 4000)}kHz')
            
            self.jlink.connect(
                device=config.get('device', 'Cortex-M4'),
                interface=config.get('interface', 'SWD'),
                speed=config.get('speed', 4000),
                serial_number=config.get('serial_number'),
                ip_address=config.get('ip_address'),
            )
            
            # 初始化RTT
            rtt_address = None
            if config.get('rtt_mode') == 'address':
                rtt_address_str = config.get('rtt_address', '')
                if rtt_address_str:
                    rtt_address = int(rtt_address_str, 16)
                    if self.log_service:
                        self.log_service.info(f'使用指定RTT地址: 0x{rtt_address:X}')
            
            if self.log_service:
                self.log_service.info('初始化RTT...')
            
            self.jlink.init_rtt(rtt_address)
            
            self.is_connected = True
            self.connected.emit()
            
            if self.log_service:
                self.log_service.success('MCU连接成功!')
            
            return True
            
        except Exception as e:
            self.is_connected = False
            error_msg = str(e)
            self.error_occurred.emit(error_msg)
            
            if self.log_service:
                self.log_service.error(f'连接失败: {error_msg}')
            
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.log_service:
            self.log_service.info('断开MCU连接')
        
        if self.jlink is not None:
            self.jlink.disconnect()
            self.jlink = None
        
        self.is_connected = False
        self.disconnected.emit()
        
        if self.log_service:
            self.log_service.success('已断开连接')
    
    def get_jlink(self):
        """
        获取JLink RTT封装对象
        
        Returns:
            JLinkRTTWrapper: JLink RTT封装对象
        """
        return self.jlink
