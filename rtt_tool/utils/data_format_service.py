#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据格式化服务
HEX/字符串格式转换
"""


class DataFormatService:
    """数据格式化服务"""
    
    @staticmethod
    def format_to_hex(data):
        """
        格式化为HEX字符串
        
        Args:
            data: bytes数据
        
        Returns:
            str: HEX字符串（大写、空格分隔）
        """
        return ' '.join(f'{b:02X}' for b in data)
    
    @staticmethod
    def parse_hex(hex_str):
        """
        解析HEX字符串
        
        Args:
            hex_str: HEX字符串（支持空格分隔）
        
        Returns:
            bytes: 解析后的数据
        """
        # 移除空格
        hex_str = hex_str.replace(" ", "")
        
        # 转换为bytes
        return bytes.fromhex(hex_str)
    
    @staticmethod
    def format_to_string(data):
        """
        格式化为字符串
        
        Args:
            data: bytes数据
        
        Returns:
            str: 字符串（非可打印字符显示为'.'）
        """
        result = []
        for b in data:
            if 32 <= b <= 126:  # 可打印ASCII字符
                result.append(chr(b))
            else:
                result.append('.')
        return ''.join(result)
    
    @staticmethod
    def parse_string(text):
        """
        解析字符串
        
        Args:
            text: 字符串
        
        Returns:
            bytes: 解析后的数据（UTF-8编码）
        """
        return text.encode('utf-8')
    
    @staticmethod
    def is_printable(data):
        """
        判断数据是否为可打印字符
        
        Args:
            data: bytes数据
        
        Returns:
            bool: 是否为可打印字符
        """
        for b in data:
            if not (32 <= b <= 126 or b in (9, 10, 13)):  # 可打印字符或制表符、换行符、回车符
                return False
        return True
