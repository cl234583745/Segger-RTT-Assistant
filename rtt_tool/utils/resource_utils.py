#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
资源路径解析模块
统一处理开发环境和打包环境的资源文件路径
"""

import sys
import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def is_frozen() -> bool:
    """
    判断是否为打包后的运行环境
    
    Returns:
        bool: True表示打包环境，False表示开发环境
    """
    return getattr(sys, 'frozen', False)


def get_base_dir() -> str:
    """
    获取资源文件的基础目录
    
    打包环境：返回sys._MEIPASS（PyInstaller临时解压目录）
    开发环境：返回项目根目录
    
    Returns:
        str: 基础目录路径
    """
    if is_frozen():
        try:
            return sys._MEIPASS
        except AttributeError:
            logger.warning("打包环境但sys._MEIPASS不存在，降级到exe所在目录")
            return os.path.dirname(sys.executable)
    else:
        current_file = os.path.abspath(__file__)
        utils_dir = os.path.dirname(current_file)
        rtt_tool_dir = os.path.dirname(utils_dir)
        project_root = os.path.dirname(rtt_tool_dir)
        return project_root


def get_exe_dir() -> str:
    """
    获取exe所在目录（打包环境）或项目根目录（开发环境）
    
    用于查找与exe平级放置的外部文件：
    config.json、JLink_x64.dll、devices.txt
    
    Returns:
        str: exe所在目录或项目根目录
    """
    if is_frozen():
        return os.path.dirname(sys.executable)
    else:
        current_file = os.path.abspath(__file__)
        utils_dir = os.path.dirname(current_file)
        rtt_tool_dir = os.path.dirname(utils_dir)
        project_root = os.path.dirname(rtt_tool_dir)
        return project_root


def get_external_file(filename: str) -> Optional[str]:
    """
    获取与exe平级放置的外部文件路径
    
    查找顺序：
    1. exe所在目录（打包环境）或项目根目录（开发环境）
    2. 当前工作目录
    
    Args:
        filename: 文件名（如config.json、devices.txt、JLink_x64.dll）
        
    Returns:
        Optional[str]: 文件绝对路径，不存在返回None
    """
    search_dirs = [get_exe_dir()]
    cwd = os.path.abspath(os.getcwd())
    if cwd != search_dirs[0]:
        search_dirs.append(cwd)
    
    for d in search_dirs:
        path = os.path.join(d, filename)
        if os.path.exists(path):
            logger.debug(f"外部文件找到: {filename} -> {path}")
            return path
    
    logger.warning(f"外部文件未找到: {filename} (搜索目录: {search_dirs})")
    return None


def get_resource_path(relative_path: str) -> Optional[str]:
    """
    获取资源文件的绝对路径
    
    Args:
        relative_path: 相对于项目根目录的资源文件路径
        
    Returns:
        Optional[str]: 资源文件的绝对路径，文件不存在时返回None
    """
    base_dir = get_base_dir()
    absolute_path = os.path.join(base_dir, relative_path)
    absolute_path = os.path.abspath(absolute_path)
    
    if os.path.exists(absolute_path):
        logger.debug(f"资源路径解析成功: {relative_path} -> {absolute_path}")
        return absolute_path
    else:
        logger.warning(f"资源文件不存在: {absolute_path} (base={base_dir}, relative={relative_path})")
        return None
