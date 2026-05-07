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
Map文件解析服务
支持GCC、IAR、Keil等编译器生成的map文件
"""

import os
from typing import Optional, Tuple, List


class MapFileParser:
    """Map文件解析器，搜索_SEGGER_RTT符号地址"""
    
    SYMBOL_NAMES = ["_SEGGER_RTT", "SEGGER_RTT"]
    
    @staticmethod
    def parse_gcc_line(line: str) -> Optional[str]:
        """
        解析GCC格式map文件行
        格式: 地址 大小 符号名
        示例: 0x20000000 0x00000100 _SEGGER_RTT
        """
        parts = line.split()
        if len(parts) >= 3:
            for symbol in MapFileParser.SYMBOL_NAMES:
                if parts[-1] == symbol:
                    try:
                        addr = int(parts[0], 16)
                        return f"0x{addr:08X}"
                    except ValueError:
                        return None
        return None
    
    @staticmethod
    def parse_iar_line(line: str) -> Optional[str]:
        """
        解析IAR格式map文件行
        格式: 符号名 地址
        示例: _SEGGER_RTT 0x20000000
        """
        for symbol in MapFileParser.SYMBOL_NAMES:
            if symbol in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == symbol and i + 1 < len(parts):
                        try:
                            addr = int(parts[i + 1], 16)
                            return f"0x{addr:08X}"
                        except ValueError:
                            continue
        return None
    
    @staticmethod
    def parse_keil_line(line: str) -> Optional[str]:
        """
        解析Keil格式map文件行
        格式: 符号名 地址
        示例: _SEGGER_RTT 0x20000000
        """
        return MapFileParser.parse_iar_line(line)
    
    @staticmethod
    def parse_gnu_map_line(line: str) -> Optional[str]:
        """
        解析GNU map文件格式（跨行或同行）
        示例: 0x00005200                _SEGGER_RTT
        或:   .bss._SEGGER_RTT
              0x00005200       0xc0 _SEGGER_RTT
        """
        for symbol in MapFileParser.SYMBOL_NAMES:
            if symbol in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == symbol and i > 0:
                        for j in range(i-1, -1, -1):
                            try:
                                addr = int(parts[j], 16)
                                return f"0x{addr:08X}"
                            except ValueError:
                                continue
        return None
    
    @classmethod
    def search_symbol(cls, map_file_path: str, log_service=None) -> Tuple[Optional[str], Optional[str]]:
        """
        在map文件中搜索_SEGGER_RTT符号地址
        
        Args:
            map_file_path: map文件路径
            log_service: 日志服务（可选）
        
        Returns:
            (地址, 错误信息) - 成功时地址非None，失败时错误信息非None
        """
        if not os.path.exists(map_file_path):
            return None, f"文件不存在: {map_file_path}"
        
        if not os.path.isfile(map_file_path):
            return None, f"不是有效文件: {map_file_path}"
        
        encodings = ['utf-8', 'gbk', 'latin-1']
        
        for encoding in encodings:
            try:
                with open(map_file_path, 'r', encoding=encoding) as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        
                        for parser in [cls.parse_gcc_line, cls.parse_iar_line, cls.parse_keil_line, cls.parse_gnu_map_line]:
                            addr = parser(line)
                            if addr:
                                if log_service:
                                    log_service.success(f"在map文件第{line_num}行找到_SEGGER_RTT: {addr}")
                                return addr, None
                
                if log_service:
                    log_service.warning(f"map文件中未找到符号: {cls.SYMBOL_NAMES}")
                return None, f"未找到符号: {cls.SYMBOL_NAMES}"
                
            except UnicodeDecodeError:
                continue
            except Exception as e:
                if log_service:
                    log_service.error(f"解析map文件失败: {e}")
                return None, f"解析失败: {e}"
        
        return None, "无法识别文件编码"
