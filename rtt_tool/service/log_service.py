#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
日志服务
管理日志记录、分类和显示
所有日志自动保存到文件
"""

from PyQt5.QtCore import QObject, pyqtSignal
from datetime import datetime
import os


class LogService(QObject):
    """日志服务"""
    
    # 信号定义
    log_added = pyqtSignal(str, str, str)  # 日志添加信号 (时间, 类型, 消息)
    
    # 日志类型
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'
    SUCCESS = 'SUCCESS'
    
    def __init__(self):
        super().__init__()
        self.logs = []  # 日志列表
        self.max_logs = 1000  # 最大日志数量
        
        # 日志文件路径
        self.log_file_path = os.path.join(os.getcwd(), 'rtt_system.log')
        
        # 打开日志文件(追加模式)
        try:
            self.log_file = open(self.log_file_path, 'a', encoding='utf-8')
            # 写入分隔线
            self.log_file.write(f"\n{'='*60}\n")
            self.log_file.write(f"RTT Assistant 启动 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            self.log_file.write(f"{'='*60}\n")
            self.log_file.flush()
        except Exception as e:
            print(f"无法打开日志文件: {e}")
            self.log_file = None
    
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
        
        # 自动保存到文件
        if self.log_file:
            try:
                line = f'[{timestamp}] [{log_type}] {message}\n'
                self.log_file.write(line)
                self.log_file.flush()
            except:
                pass
        
        # 发射信号
        self.log_added.emit(timestamp, log_type, message)
    
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
    
    def read_log_file(self):
        """
        读取日志文件内容
        
        Returns:
            str: 日志文件内容
        """
        try:
            if os.path.exists(self.log_file_path):
                with open(self.log_file_path, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception as e:
            return f"读取日志文件失败: {e}"
        return ""
    
    def __del__(self):
        """析构函数,关闭日志文件"""
        if self.log_file:
            try:
                self.log_file.close()
            except:
                pass
