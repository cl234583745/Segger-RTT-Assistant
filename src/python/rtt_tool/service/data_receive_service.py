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
    
    data_received = pyqtSignal(int, bytes)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, backend, channels=None, buffer_size=8192, poll_interval_ms=10):
        super().__init__()
        self._backend = backend
        self._channels = channels if channels is not None else [0]
        self.buffer = RingBuffer(buffer_size)
        self._poll_interval_ms = poll_interval_ms
        self.running = False
        self._error_count = 0
        self._buffer_full_warned = False
    
    def run(self):
        """线程运行函数"""
        self.running = True
        self._error_count = 0
        
        while self.running:
            try:
                for channel in self._channels:
                    if not self.running:
                        break
                    try:
                        data = self._backend.rtt_read(channel, 1024)
                        if data:
                            written = self.buffer.write(data)
                            if written < len(data) and not self._buffer_full_warned:
                                self._buffer_full_warned = True
                                self.error_occurred.emit(
                                    f"环形缓冲区已满，丢弃 {len(data) - written} 字节 "
                                    f"(缓冲大小={self.buffer.size}, 通道={channel})")
                            elif written >= len(data):
                                self._buffer_full_warned = False
                            self.data_received.emit(channel, data)
                        self._error_count = 0
                    except Exception as e:
                        self._error_count += 1
                        if self._error_count >= 3:
                            self.running = False
                            break
                        self.error_occurred.emit(f"通道{channel}读取错误: {e}")
                
                if self.running:
                    self.msleep(self._poll_interval_ms)
                
            except Exception as e:
                self.error_occurred.emit(str(e))
                self.running = False
                break
    
    def stop(self):
        """停止线程 - 优雅退出，不使用terminate"""
        self.running = False
        self.wait(3000)
    
    def set_poll_interval(self, ms):
        self._poll_interval_ms = max(1, min(ms, 100))
    
    def set_channels(self, channels):
        self._channels = channels if channels is not None else [0]
    
    def get_buffer_data(self, size=None):
        return self.buffer.read(size)


class DataReceiveService(QObject):
    """数据接收服务"""
    
    data_received = pyqtSignal(int, bytes)
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.receive_thread = None
    
    def start_receive(self, backend, channels=None):
        if self.receive_thread is not None and self.receive_thread.isRunning():
            return
        
        self.receive_thread = DataReceiveThread(backend, channels=channels)
        self.receive_thread.data_received.connect(self.data_received)
        self.receive_thread.error_occurred.connect(self.error_occurred)
        self.receive_thread.start()
    
    def stop_receive(self):
        """停止数据接收"""
        if self.receive_thread is not None:
            self.receive_thread.stop()
            self.receive_thread = None
    
    def is_receiving(self):
        return self.receive_thread is not None and self.receive_thread.isRunning()
