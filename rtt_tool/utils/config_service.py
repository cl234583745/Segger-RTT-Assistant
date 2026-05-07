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
配置管理服务
加载、保存、修改配置
"""

import json
import os
from .resource_utils import get_exe_dir


class ConfigService:
    """配置管理服务"""
    
    DEFAULT_CONFIG = {
        "device": "Cortex-M4",
        "interface": "SWD",
        "speed": 4000,
        "jlink_path": None,
        "show_timestamp": False,
        "hex_display": False,
        "hex_send": False,
        "add_newline": True,
        "window_topmost": False,
        "font_family": "Courier New",
        "font_size": 10,
        "window_width": 1000,
        "window_height": 700,
        "rtt_address": "",  # RTT控制块地址(上次输入)
        "last_device": "Cortex-M4",  # 上次选择的设备型号
        "rtt_mode": "auto",  # RTT控制块模式: auto/address/range
        "rtt_range_start": "",  # RTT搜索范围起始地址
        "rtt_range_size": "",  # RTT搜索范围大小
        "map_file_path": "",  # map文件路径(用于搜索RTT地址)
        "ansi_color_enabled": False,  # ANSI转义码染色开关
        "keyword_highlight_enabled": True,  # 关键字高亮开关
        "keyword_rules": {  # 关键字高亮规则
            "ERROR": "#ff0000",
            "WARN": "#ffff00",
            "WARNING": "#ffff00",
            "FAIL": "#ff0000",
            "OK": "#00ff00",
            "SUCCESS": "#00ff00",
        },
    }
    
    def __init__(self, config_file=None):
        """
        初始化配置服务
        
        Args:
            config_file: 配置文件路径，None则自动定位到exe所在目录
        """
        if config_file is None:
            config_file = os.path.join(get_exe_dir(), "config.json")
        self.config_file = config_file
        self.config = {}
        self.load()
    
    def load(self):
        """加载配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                
                # 合并默认配置（处理新增配置项）
                for key, value in self.DEFAULT_CONFIG.items():
                    if key not in self.config:
                        self.config[key] = value
                
            except Exception as e:
                print(f"加载配置失败: {e}")
                self.config = self.DEFAULT_CONFIG.copy()
        else:
            self.config = self.DEFAULT_CONFIG.copy()
    
    def save(self):
        """保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    def get(self, key, default=None):
        """
        获取配置项
        
        Args:
            key: 配置项键
            default: 默认值
        
        Returns:
            配置项值
        """
        return self.config.get(key, default)
    
    def set(self, key, value):
        """
        设置配置项
        
        Args:
            key: 配置项键
            value: 配置项值
        """
        self.config[key] = value
    
    def get_all(self):
        """
        获取所有配置
        
        Returns:
            dict: 所有配置
        """
        return self.config.copy()
    
    def set_all(self, config):
        """
        设置所有配置
        
        Args:
            config: 配置字典
        """
        self.config.update(config)
