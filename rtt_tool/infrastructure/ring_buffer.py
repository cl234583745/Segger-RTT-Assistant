#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
环形缓冲区实现
用于高效的数据缓存，支持多线程安全访问
"""

import threading


class RingBuffer:
    """线程安全的环形缓冲区"""
    
    def __init__(self, size=4096):
        """
        初始化环形缓冲区
        
        Args:
            size: 缓冲区大小（字节）
        """
        self.size = size
        self.buffer = bytearray(size)
        self.head = 0  # 写入位置
        self.tail = 0  # 读取位置
        self.lock = threading.Lock()
    
    def write(self, data):
        """
        写入数据到缓冲区
        
        Args:
            data: 要写入的数据（bytes或bytearray）
        
        Returns:
            int: 实际写入的字节数
        """
        if not data:
            return 0
        
        data_len = len(data)
        write_len = 0
        
        with self.lock:
            # 计算可写入空间
            available = self._get_available_write_space()
            
            # 限制写入长度
            write_len = min(data_len, available)
            
            if write_len == 0:
                return 0
            
            # 分两段写入（可能需要回绕）
            first_part = min(write_len, self.size - self.head)
            self.buffer[self.head:self.head + first_part] = data[:first_part]
            
            if write_len > first_part:
                # 需要回绕到缓冲区开头
                second_part = write_len - first_part
                self.buffer[:second_part] = data[first_part:write_len]
            
            # 更新写入位置
            self.head = (self.head + write_len) % self.size
        
        return write_len
    
    def read(self, size=None):
        """
        从缓冲区读取数据
        
        Args:
            size: 要读取的字节数，None表示读取所有可用数据
        
        Returns:
            bytes: 读取的数据
        """
        with self.lock:
            # 计算可读取数据量
            available = self._get_available_read_space()
            
            if available == 0:
                return b''
            
            # 确定读取长度
            read_len = available if size is None else min(size, available)
            
            # 分两段读取（可能需要回绕）
            first_part = min(read_len, self.size - self.tail)
            data = bytes(self.buffer[self.tail:self.tail + first_part])
            
            if read_len > first_part:
                # 需要从缓冲区开头继续读取
                second_part = read_len - first_part
                data += bytes(self.buffer[:second_part])
            
            # 更新读取位置
            self.tail = (self.tail + read_len) % self.size
        
        return data
    
    def peek(self, size=None):
        """
        查看缓冲区数据但不移除
        
        Args:
            size: 要查看的字节数，None表示查看所有可用数据
        
        Returns:
            bytes: 查看的数据
        """
        with self.lock:
            # 计算可读取数据量
            available = self._get_available_read_space()
            
            if available == 0:
                return b''
            
            # 确定查看长度
            peek_len = available if size is None else min(size, available)
            
            # 分两段查看（可能需要回绕）
            first_part = min(peek_len, self.size - self.tail)
            data = bytes(self.buffer[self.tail:self.tail + first_part])
            
            if peek_len > first_part:
                # 需要从缓冲区开头继续查看
                second_part = peek_len - first_part
                data += bytes(self.buffer[:second_part])
        
        return data
    
    def clear(self):
        """清空缓冲区"""
        with self.lock:
            self.head = 0
            self.tail = 0
    
    def get_available_space(self):
        """
        获取可写入空间大小
        
        Returns:
            int: 可写入字节数
        """
        with self.lock:
            return self._get_available_write_space()
    
    def get_data_size(self):
        """
        获取已存储数据大小
        
        Returns:
            int: 已存储字节数
        """
        with self.lock:
            return self._get_available_read_space()
    
    def _get_available_write_space(self):
        """计算可写入空间（内部方法，需在锁内调用）"""
        if self.head >= self.tail:
            return self.size - (self.head - self.tail) - 1
        else:
            return self.tail - self.head - 1
    
    def _get_available_read_space(self):
        """计算可读取数据量（内部方法，需在锁内调用）"""
        if self.head >= self.tail:
            return self.head - self.tail
        else:
            return self.size - (self.tail - self.head)
    
    def __len__(self):
        """返回已存储数据大小"""
        return self.get_data_size()
    
    def __bool__(self):
        """返回缓冲区是否有数据"""
        return self.get_data_size() > 0
