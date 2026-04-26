#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
配置管理服务
加载、保存、修改配置
"""

import json
import os


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
        "rtt_range_end": "",  # RTT搜索范围结束地址
    }
    
    def __init__(self, config_file="config.json"):
        """
        初始化配置服务
        
        Args:
            config_file: 配置文件路径
        """
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
