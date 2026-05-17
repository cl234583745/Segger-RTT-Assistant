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
日志服务
管理日志记录、分类和显示
所有日志自动保存到文件
"""

from PyQt5.QtCore import QObject, pyqtSignal
from datetime import datetime
from ..utils.resource_utils import get_exe_dir
import os
import logging.handlers


class LogService(QObject):
    """日志服务"""
    
    # 信号定义
    log_added = pyqtSignal(str, str, str)  # 日志添加信号 (时间, 类型, 消息)
    
    # 日志类型
    DEBUG = 'DEBUG'
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'
    SUCCESS = 'SUCCESS'
    
    def __init__(self):
        super().__init__()
        self.logs = []
        self.max_logs = 1000

        from ..runtime.path_config import RUNTIME_LOG_DIR, ensure_runtime_dirs
        ensure_runtime_dirs()
        self.log_file_path = os.path.join(RUNTIME_LOG_DIR, 'rtt_system.log')

        try:
            self._log_handler = logging.handlers.RotatingFileHandler(
                self.log_file_path, maxBytes=5*1024*1024, backupCount=3,
                encoding='utf-8')
            self._log_logger = logging.Logger('rtt_system')
            self._log_logger.addHandler(self._log_handler)
            self._log_logger.setLevel(logging.DEBUG)
            self._log_logger.info(f"\n{'='*60}")
            self._log_logger.info(f"RTT Assistant 启动 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self._log_logger.info(f"{'='*60}")
        except Exception as e:
            print(f"无法打开日志文件: {e}")
            self._log_logger = None
    
    def add_log(self, message, log_type='INFO'):
        """
        添加日志
        
        Args:
            message: 日志消息
            log_type: 日志类型 (INFO/WARNING/ERROR/SUCCESS)
        """
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        
        # 添加到日志列表
        log_entry = {
            'timestamp': timestamp,
            'type': log_type,
            'message': message
        }
        self.logs.append(log_entry)
        
        # 限制日志数量
        if len(self.logs) > self.max_logs:
            self.logs.pop(0)
        
        if self._log_logger:
            try:
                self._log_logger.info(f'[{timestamp}] [{log_type}] {message}')
            except:
                pass
        
        # 发射信号
        self.log_added.emit(timestamp, log_type, message)
    
    def debug(self, message):
        """添加DEBUG日志"""
        self.add_log(message, self.DEBUG)
    
    def info(self, message):
        """添加INFO日志"""
        self.add_log(message, self.INFO)
    
    def warning(self, message):
        """添加WARNING日志"""
        self.add_log(message, self.WARNING)
    
    def error(self, message):
        """添加ERROR日志"""
        self.add_log(message, self.ERROR)
    
    def success(self, message):
        """添加SUCCESS日志"""
        self.add_log(message, self.SUCCESS)
    
    def clear(self):
        """清空日志"""
        self.logs.clear()
    
    def get_logs(self):
        """
        获取所有日志
        
        Returns:
            list: 日志列表
        """
        return self.logs.copy()
    
    def get_logs_by_type(self, log_type):
        """
        按类型获取日志
        
        Args:
            log_type: 日志类型
        
        Returns:
            list: 指定类型的日志列表
        """
        return [log for log in self.logs if log['type'] == log_type]
    
    def read_log_file(self, max_lines=500):
        """
        读取日志文件内容（仅最后max_lines行，避免首次加载慢）

        Args:
            max_lines: 最大读取行数

        Returns:
            str: 日志文件内容
        """
        try:
            if os.path.exists(self.log_file_path):
                with open(self.log_file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if len(lines) > max_lines:
                        lines = lines[-max_lines:]
                    return ''.join(lines)
        except Exception as e:
            return f"读取日志文件失败: {e}"
        return ""
    
    def _close_log_file(self):
        if self._log_handler:
            try:
                self._log_handler.close()
            except:
                pass
