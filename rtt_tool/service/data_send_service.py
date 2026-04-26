#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据发送服务
向RTT发送数据，支持字符串和HEX模式
"""

from PyQt5.QtCore import QObject, pyqtSignal, QThread


class SendWorker(QThread):
    """发送工作线程"""
    finished = pyqtSignal(int)  # 完成信号(发送字节数)
    error = pyqtSignal(str)  # 错误信号
    
    def __init__(self, jlink, data):
        super().__init__()
        self.jlink = jlink
        self.data = data
    
    def run(self):
        """执行发送"""
        try:
            if self.jlink is None:
                self.error.emit("未连接到MCU")
                return
            
            # 发送数据
            num_bytes = self.jlink.write_rtt(self.data)
            self.finished.emit(num_bytes)
            
        except Exception as e:
            self.error.emit(str(e))


class DataSendService(QObject):
    """数据发送服务"""
    
    # 信号定义
    data_sent = pyqtSignal(int)  # 数据发送信号（发送字节数）
    error_occurred = pyqtSignal(str)  # 错误信号
    
    def __init__(self):
        super().__init__()
        self.jlink = None
        self.worker = None
    
    def set_jlink(self, jlink):
        """
        设置JLink RTT封装对象
        
        Args:
            jlink: JLink RTT封装对象
        """
        self.jlink = jlink
    
    def send_data(self, data):
        """
        发送数据
        
        Args:
            data: 要发送的数据（bytes）
        
        Returns:
            int: 实际发送的字节数
        """
        if self.jlink is None:
            self.error_occurred.emit("未连接到MCU")
            return 0
        
        try:
            # 在工作线程中发送数据
            self.worker = SendWorker(self.jlink, data)
            self.worker.finished.connect(self._on_send_finished)
            self.worker.error.connect(self._on_send_error)
            self.worker.start()
            return len(data)
            
        except Exception as e:
            self.error_occurred.emit(str(e))
            return 0
    
    def _on_send_finished(self, num_bytes):
        """发送完成"""
        self.data_sent.emit(num_bytes)
    
    def _on_send_error(self, error_msg):
        """发送错误"""
        self.error_occurred.emit(error_msg)
    
    def send_string(self, text, add_newline=False):
        """
        发送字符串
        
        Args:
            text: 要发送的字符串
            add_newline: 是否添加换行符
        
        Returns:
            int: 实际发送的字节数
        """
        if add_newline:
            text += "\n"
        
        data = text.encode('utf-8')
        return self.send_data(data)
    
    def send_hex(self, hex_str):
        """
        发送HEX数据
        
        Args:
            hex_str: HEX字符串（如"01 02 03"）
        
        Returns:
            int: 实际发送的字节数
        """
        try:
            # 移除空格
            hex_str = hex_str.replace(" ", "")
            
            # 验证是否为空
            if not hex_str:
                self.error_occurred.emit("HEX数据为空")
                return 0
            
            # 验证是否为偶数长度
            if len(hex_str) % 2 != 0:
                self.error_occurred.emit(f"HEX格式错误: 数据长度必须为偶数(当前{len(hex_str)}个字符)")
                return 0
            
            # 验证是否都是有效的十六进制字符
            valid_chars = set('0123456789ABCDEFabcdef')
            invalid_chars = set(hex_str) - valid_chars
            if invalid_chars:
                self.error_occurred.emit(f"HEX格式错误: 包含非法字符 {invalid_chars}")
                return 0
            
            # 转换为bytes
            data = bytes.fromhex(hex_str)
            
            return self.send_data(data)
            
        except Exception as e:
            self.error_occurred.emit(f"HEX格式错误: {e}")
            return 0
