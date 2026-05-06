#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
连接管理服务
管理MCU连接状态，发射连接状态变化信号
"""

from PyQt5.QtCore import QObject, pyqtSignal
from ..infrastructure.jlink_rtt_wrapper import JLinkRTTWrapper
from ..utils.device_info_service import DeviceInfoService


class ConnectionService(QObject):
    """连接管理服务"""
    
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, log_service=None):
        super().__init__()
        self.jlink = None
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
            if self.log_service:
                self.log_service.info(f'开始连接MCU: {config.get("device", "Cortex-M4")}')
            
            if self.jlink is None:
                if self.log_service:
                    self.log_service.info('初始化JLink RTT封装')
                self.jlink = JLinkRTTWrapper(config.get('jlink_path'), log_service=self.log_service)
                if self.log_service:
                    self.log_service.info(f'JLink DLL路径: {self.jlink.jlink_path}')
            
            if self.log_service:
                self.log_service.info(f'连接参数: 接口={config.get("interface", "SWD")}, 速度={config.get("speed", 4000)}kHz')
            
            device_name = config.get('device', 'Cortex-M4')
            try:
                device_info = self._device_info_service.get_device_info(device_name)
                log_msg = self._device_info_service.format_device_log(device_info, device_name)
                if self.log_service:
                    self.log_service.info(log_msg)
            except Exception:
                pass
            
            self.jlink.connect(
                device=device_name,
                interface=config.get('interface', 'SWD'),
                speed=config.get('speed', 4000),
                serial_number=config.get('serial_number'),
                ip_address=config.get('ip_address'),
            )
            
            rtt_mode = config.get('rtt_mode', 'auto')
            rtt_address = None
            range_start = None
            range_end = None
            
            if rtt_mode == 'address':
                rtt_address_str = config.get('rtt_address', '')
                if rtt_address_str:
                    rtt_address = int(rtt_address_str, 16)
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
                    if self.log_service:
                        self.log_service.info(f'RTT搜索范围: 起始=0x{range_start:X}, 大小=0x{range_size:X}, 结束=0x{range_end:X}')
                else:
                    raise ValueError("搜索范围模式需要指定起始地址和大小")
            
            if self.log_service:
                self.log_service.info('初始化RTT...')
            
            self.jlink.init_rtt(
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
        return self.jlink
