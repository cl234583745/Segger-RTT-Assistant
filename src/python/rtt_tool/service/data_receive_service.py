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

import logging
from PyQt5.QtCore import QThread, pyqtSignal, QObject, QMutex
from ..infrastructure.ring_buffer import RingBuffer

_logger = logging.getLogger(__name__)


class DataReceiveThread(QThread):
    """数据接收线程"""
    
    data_received = pyqtSignal(int, bytes)
    batch_received = pyqtSignal(float, list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, backend, channels=None, buffer_size=65536, poll_interval_ms=10,
                 pylink_read_size=4096, max_drain_rounds=16,
                 fast_interval_ms=2, slow_interval_ms=10, idle_threshold=3,
                 swd_latency_ms=1.0, diagnostic_log_enabled=True):
        super().__init__()
        self._backend = backend
        self._channels = channels if channels is not None else [0]
        self._channels_mutex = QMutex()
        self.buffer = RingBuffer(buffer_size)
        self._poll_interval_ms = poll_interval_ms
        self.running = False
        self._channel_error_counts: dict = {}
        self._buffer_full_warned = False
        self._pylink_read_size = pylink_read_size
        self._max_drain_rounds = max_drain_rounds
        self._fast_interval_ms = fast_interval_ms
        self._slow_interval_ms = slow_interval_ms
        self._idle_threshold = idle_threshold
        self._swd_latency_ms = swd_latency_ms
        self._consecutive_idle_count = 0
        self._current_interval_ms = slow_interval_ms
        self._diagnostic_log_enabled = diagnostic_log_enabled
    
    def _effective_fast_interval(self) -> int:
        self._channels_mutex.lock()
        active_count = len(self._channels)
        self._channels_mutex.unlock()
        return max(self._fast_interval_ms, int(active_count * self._swd_latency_ms))

    def _update_poll_state(self, has_data: bool) -> None:
        if has_data:
            self._consecutive_idle_count = 0
            self._current_interval_ms = self._effective_fast_interval()
        else:
            self._consecutive_idle_count += 1
            if self._consecutive_idle_count >= self._idle_threshold:
                self._current_interval_ms = self._slow_interval_ms

    def _drain_read_channel(self, channel: int) -> bytes:
        collected = b''
        for round_idx in range(self._max_drain_rounds):
            try:
                data = self._backend.rtt_read(channel, self._pylink_read_size)
            except Exception as e:
                if round_idx == 0:
                    raise
                _logger.warning(f"积压读取CH{channel}第{round_idx+1}轮异常: {e}")
                break
            if not data:
                break
            collected += data
        else:
            if self._diagnostic_log_enabled:
                _logger.warning(f"积压读取CH{channel}达{self._max_drain_rounds}轮上限，仍有数据")
        return collected

    def run(self):
        """线程运行函数 - 一次poll控制块，批量读取所有通道"""
        self.running = True
        self._channel_error_counts.clear()
        self._channel_read_counts = {}
        
        while self.running:
            try:
                self._channels_mutex.lock()
                channels_snapshot = list(self._channels)
                self._channels_mutex.unlock()
                
                if not channels_snapshot:
                    if self.running:
                        self.msleep(self._current_interval_ms)
                    continue

                has_data_this_round = False
                use_batch = hasattr(self._backend, 'rtt_read_all')
                
                if use_batch:
                    try:
                        import time
                        poll_time = time.perf_counter()
                        all_data = self._backend.rtt_read_all(channels_snapshot, self._pylink_read_size)
                    except Exception as e:
                        self.error_occurred.emit(f"RTT批量读取失败: {e}")
                        self._update_poll_state(False)
                        if self.running:
                            self.msleep(self._current_interval_ms)
                        continue
                    
                    batch = []
                    ch0_merged_data = b''
                    for channel, data in all_data.items():
                        if not self.running:
                            break
                        cnt = self._channel_read_counts.get(channel, 0) + 1
                        self._channel_read_counts[channel] = cnt
                        data_len = len(data) if data else 0
                        if data:
                            has_data_this_round = True
                            if channel == 0:
                                ch0_merged_data += data
                            else:
                                batch.append((channel, data))
                        self._channel_error_counts.pop(channel, None)
                    
                    if ch0_merged_data:
                        written = self.buffer.write(ch0_merged_data)
                        if written < len(ch0_merged_data) and not self._buffer_full_warned:
                            self._buffer_full_warned = True
                            _logger.debug(
                                f"环形缓冲区已满，丢弃 {len(ch0_merged_data) - written} 字节 "
                                f"(缓冲大小={self.buffer.size}, 通道=0)")
                        elif written >= len(ch0_merged_data):
                            self._buffer_full_warned = False
                        self.data_received.emit(0, ch0_merged_data)
                    
                    if batch:
                        self.batch_received.emit(poll_time, batch)
                        if not hasattr(self, '_batch_log_cnt'):
                            self._batch_log_cnt = 0
                        self._batch_log_cnt += 1
                        if self._batch_log_cnt <= 5 or self._batch_log_cnt % 100 == 0:
                            summary = ', '.join(f'CH{ch}:{len(d)}B' for ch, d in batch)
                            _logger.info(f"[DRT batch] #{self._batch_log_cnt} poll={poll_time:.4f} {summary}")
                else:
                    ch0_merged_data = b''
                    for channel in channels_snapshot:
                        if not self.running:
                            break
                        try:
                            is_jlink = hasattr(self._backend, 'backend_type') and self._backend.backend_type == 'jlink'
                            if is_jlink and channel == 0:
                                data = self._drain_read_channel(channel)
                            else:
                                data = self._backend.rtt_read(channel, self._pylink_read_size)
                            cnt = self._channel_read_counts.get(channel, 0) + 1
                            self._channel_read_counts[channel] = cnt
                            data_len = len(data) if data else 0
                            if data:
                                has_data_this_round = True
                                if channel == 0:
                                    ch0_merged_data += data
                                else:
                                    self.data_received.emit(channel, data)
                            self._channel_error_counts.pop(channel, None)
                        except Exception as e:
                            _logger.warning(f"RTT通道{channel}读取错误(第{self._channel_error_counts.get(channel,0)+1}次): {e}")
                            err_cnt = self._channel_error_counts.get(channel, 0) + 1
                            self._channel_error_counts[channel] = err_cnt
                            if err_cnt >= 3:
                                self._channels_mutex.lock()
                                if channel in self._channels:
                                    self._channels = [c for c in self._channels if c != channel]
                                self._channels_mutex.unlock()
                                self.error_occurred.emit(
                                    f"通道{channel}连续3次读取失败，已停止该通道: {e}")
                            else:
                                self.error_occurred.emit(f"通道{channel}读取错误: {e}")
                    
                    if ch0_merged_data:
                        written = self.buffer.write(ch0_merged_data)
                        if written < len(ch0_merged_data) and not self._buffer_full_warned:
                            self._buffer_full_warned = True
                            _logger.debug(
                                f"环形缓冲区已满，丢弃 {len(ch0_merged_data) - written} 字节 "
                                f"(缓冲大小={self.buffer.size}, 通道=0)")
                        elif written >= len(ch0_merged_data):
                            self._buffer_full_warned = False
                        self.data_received.emit(0, ch0_merged_data)
                
                self._update_poll_state(has_data_this_round)
                
                if self._diagnostic_log_enabled and hasattr(self, '_diag_tick'):
                    self._diag_tick += 1
                    if self._diag_tick <= 5 or self._diag_tick % 100 == 0:
                        backend_t = getattr(self._backend, 'backend_type', '?')
                        interval_mode = 'fast' if self._current_interval_ms <= self._effective_fast_interval() else 'slow'
                        _logger.info(f"poll: backend={backend_t}, interval={interval_mode}({self._current_interval_ms}ms), "
                                     f"idle={self._consecutive_idle_count}, channels={len(channels_snapshot)}")
                elif not hasattr(self, '_diag_tick'):
                    self._diag_tick = 0
                
                if self.running:
                    self.msleep(self._current_interval_ms)
                
            except Exception as e:
                _logger.error(f"DataReceiveThread unexpected error: {e}", exc_info=True)
                self.error_occurred.emit(str(e))
                if self.running:
                    self.msleep(self._current_interval_ms)
    
    def stop(self):
        """停止线程 - 优雅退出，不使用terminate"""
        self.running = False
        self.wait(3000)
    
    def set_poll_interval(self, ms):
        self._poll_interval_ms = max(1, min(ms, 100))
    
    def set_fast_interval(self, ms):
        self._fast_interval_ms = max(1, min(ms, 50))
    
    def set_slow_interval(self, ms):
        self._slow_interval_ms = max(5, min(ms, 100))
    
    def set_channels(self, channels):
        self._channels_mutex.lock()
        self._channels = channels if channels is not None else [0]
        self._channels_mutex.unlock()
    
    def get_buffer_data(self, size=None):
        return self.buffer.read(size)


class DataReceiveService(QObject):
    """数据接收服务"""
    
    data_received = pyqtSignal(int, bytes)
    batch_received = pyqtSignal(float, list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.receive_thread = None
    
    def start_receive(self, backend, channels=None):
        if self.receive_thread is not None and self.receive_thread.isRunning():
            return
        
        self.receive_thread = DataReceiveThread(backend, channels=channels)
        self.receive_thread.data_received.connect(self.data_received)
        self.receive_thread.batch_received.connect(self.batch_received)
        self.receive_thread.error_occurred.connect(self.error_occurred)
        self.receive_thread.start()
    
    def stop_receive(self):
        """停止数据接收"""
        if self.receive_thread is not None:
            self.receive_thread.stop()
            self.receive_thread = None
    
    def is_receiving(self):
        return self.receive_thread is not None and self.receive_thread.isRunning()
