#!/usr/bin/env python3
"""Patch main_controller.py for i18n status bar calls."""
import re

filepath = 'G:/opencode/RTT-Assistant/src/python/rtt_tool/controller/main_controller.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Add imports
if 'from ..ui.main_window import STATUS_DISCONNECTED' not in content:
    content = content.replace(
        'from ..models.channel_config import ChannelRoute',
        'from ..models.channel_config import ChannelRoute\nfrom ..i18n import _ as i18n\nfrom ..ui.main_window import STATUS_DISCONNECTED, STATUS_CONNECTING, STATUS_CONNECTED, STATUS_READY, STATUS_LOADING_BACKEND, STATUS_INITIALIZING, STATUS_DISCONNECTING, STATUS_ERROR, STATUS_WARNING'
    )

# Replace set_status calls
replacements = [
    ('self.window.set_status("正在加载调试器后端...")', 'self.window.set_status(STATUS_LOADING_BACKEND)'),
    ('self.window.set_status("正在初始化处理器...")', 'self.window.set_status(STATUS_INITIALIZING)'),
    ('self.window.set_status("就绪")', 'self.window.set_status(STATUS_READY)'),
    ('self.window.set_status("正在初始化...")', 'self.window.set_status(STATUS_INITIALIZING)'),
    ('self.window.set_status("连接中")', 'self.window.set_status(STATUS_CONNECTING)'),
    ('self.window.set_status("正在断开...")', 'self.window.set_status(STATUS_DISCONNECTING)'),
    ('self.window.set_status("请先配置连接参数")', 'self.window.set_status(STATUS_DISCONNECTED, i18n("status.please_config"))'),
    ('self.window.set_status("请先在配置页面刷新探针并选择")', 'self.window.set_status(STATUS_DISCONNECTED, i18n("status.please_select_probe"))'),
    ('self.window.set_status("请先连接设备")', 'self.window.set_status(STATUS_DISCONNECTED, i18n("status.please_connect"))'),
    ('self.window.set_status("连接失败")', 'self.window.set_status(STATUS_ERROR, i18n("status.connect_failed"))'),
    ('self.window.set_status("未连接")', 'self.window.set_status(STATUS_DISCONNECTED)'),
    ('self.window.set_status("已连接")', 'self.window.set_status(STATUS_CONNECTED)'),
]

for old, new in replacements:
    if old in content:
        content = content.replace(old, new)
        print(f"  Replaced: {old[:50]}...")
    else:
        print(f"  NOT FOUND: {old[:50]}...")

# Handle f-string status messages
fstring_replacements = [
    ('self.window.set_status(f"连接失败: {error_msg}")', 'self.window.set_status(STATUS_ERROR, error_msg)'),
    ('self.window.set_status(f"连接超时({timeout}s)")', 'self.window.set_status(STATUS_ERROR, f"{i18n(\'status.connect_timeout\').split(\'(\')[0]}({timeout}s)")'),
    ('self.window.set_status(f"警告: {error_msg}")', 'self.window.set_status(STATUS_WARNING, error_msg)'),
    ('self.window.set_status(f"错误: {error_msg}")', 'self.window.set_status(STATUS_ERROR, error_msg)'),
    ('self.window.set_status(f"发送失败: {str(e)}")', 'self.window.set_status(STATUS_ERROR, str(e))'),
]

for old, new in fstring_replacements:
    if old in content:
        content = content.replace(old, new)
        print(f"  Replaced f-string: {old[:50]}...")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Controller patched successfully")