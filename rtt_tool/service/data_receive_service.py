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
数据接收服务
从RTT接收数据，发射数据接收信号
"""

from PyQt5.QtCore import QThread, pyqtSignal, QObject
from ..infrastructure.ring_buffer import RingBuffer


class DataReceiveThread(QThread):
    """数据接收线程"""
    
    data_received = pyqtSignal(bytes)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, jlink, buffer_size=8192):
        """
        初始化数据接收线程
        
        Args:
            jlink: JLink RTT封装对象
            buffer_size: 环形缓冲区大小
        """
        super().__init__()
        self.jlink = jlink
        self.buffer = RingBuffer(buffer_size)
        self.running = False
    
    def run(self):
        """线程运行函数"""
        self.running = True
        
        while self.running:
            try:
                # 从RTT读取数据
                data = self.jlink.read_rtt(1024)
                
                if data:
                    # 写入环形缓冲区
                    self.buffer.write(data)
                    
                    # 发射数据接收信号
                    self.data_received.emit(data)
                
                # 短暂休眠，避免CPU占用过高
                self.msleep(1)
                
            except Exception as e:
                self.error_occurred.emit(str(e))
                self.running = False
                break
    
    def stop(self):
        """停止线程"""
        self.running = False
        self.wait()
    
    def get_buffer_data(self, size=None):
        """
        从缓冲区获取数据
        
        Args:
            size: 要获取的字节数，None表示获取所有
        
        Returns:
            bytes: 缓冲区数据
        """
        return self.buffer.read(size)


class DataReceiveService(QObject):
    """数据接收服务"""
    
    # 信号定义
    data_received = pyqtSignal(bytes)  # 数据接收信号
    error_occurred = pyqtSignal(str)  # 错误信号
    
    def __init__(self):
        super().__init__()
        self.receive_thread = None
    
    def start_receive(self, jlink):
        """
        启动数据接收
        
        Args:
            jlink: JLink RTT封装对象
        """
        if self.receive_thread is not None and self.receive_thread.isRunning():
            return
        
        self.receive_thread = DataReceiveThread(jlink)
        self.receive_thread.data_received.connect(self.data_received)
        self.receive_thread.error_occurred.connect(self.error_occurred)
        self.receive_thread.start()
    
    def stop_receive(self):
        """停止数据接收"""
        if self.receive_thread is not None:
            self.receive_thread.stop()
            self.receive_thread = None
    
    def is_receiving(self):
        """
        是否正在接收
        
        Returns:
            bool: 是否正在接收
        """
        return self.receive_thread is not None and self.receive_thread.isRunning()
