#!/usr/bin/env python3
"""Safely patch connection_dialog.py - only single-line safe replacements."""
import re

filepath = 'G:/opencode/RTT-Assistant/src/python/rtt_tool/ui/connection_dialog.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Only do safe single-line replacements that won't break multi-line strings
replacements = [
    ('QGroupBox("步骤1: 调试器选择")', 'QGroupBox(i18n("label.step1_debugger"))'),
    ('QGroupBox("步骤2: 连接方式")', 'QGroupBox(i18n("label.step2_connection"))'),
    ('QGroupBox("步骤3: 目标设备")', 'QGroupBox(i18n("label.step3_device"))'),
    ('QGroupBox("步骤4: 接口设置")', 'QGroupBox(i18n("label.step4_interface"))'),
    ('QGroupBox("步骤5: RTT控制块")', 'QGroupBox(i18n("label.step5_rtt"))'),
    ('QGroupBox("Map文件搜索")', 'QGroupBox(i18n("label.map_file_search"))'),
    ('QPushButton("刷新")', 'QPushButton(i18n("btn.refresh"))'),
    ('QPushButton("更新")', 'QPushButton(i18n("btn.update"))'),
    ('QPushButton("确定")', 'QPushButton(i18n("btn.ok"))'),
    ('QPushButton("取消")', 'QPushButton(i18n("btn.cancel"))'),
    ('QPushButton("打开map文件")', 'QPushButton(i18n("btn.open_map_file"))'),
    ('QPushButton("搜索_SEGGER_RTT")', 'QPushButton(i18n("btn.search_rtt_symbol"))'),
    ('QPushButton("获取自动检测地址")', 'QPushButton(i18n("btn.auto_fill_address"))'),
    ('QPushButton("选择颜色")', 'QPushButton(i18n("btn.select_color"))'),
    ('"J-Link 目标设备:"', 'i18n("label.jlink_device")'),
    ('"其他Link 目标设备:"', 'i18n("label.pyocd_device")'),
    ('"接口:"', 'i18n("label.interface")'),
    ('"速度:"', 'i18n("label.speed")'),
    ('"连接模式:"', 'i18n("label.connect_mode")'),
    ('"已连接探针:"', 'i18n("label.connected_probes")'),
    ('"序列号或昵称"', 'i18n("placeholder.serial_number")'),
    ('"IP地址"', 'i18n("placeholder.ip_address")'),
    ('"如: 0x22002848 或从map文件搜索"', 'i18n("placeholder.rtt_address")'),
    ('"起始地址"', 'i18n("placeholder.range_start")'),
    ('"大小"', 'i18n("placeholder.range_size")'),
    ('"筛选设备型号"', 'i18n("tooltip.filter_device")'),
    ('"PyOCD目标类型名称"', 'i18n("tooltip.pyocd_target_name")'),
    ('"筛选PyOCD目标设备"', 'i18n("tooltip.filter_pyocd_target")'),
    ('"重新探测调试器"', 'i18n("tooltip.refresh_debugger")'),
    ('"J-Link 设备型号筛选"', 'i18n("dialog.jlink_device_filter")'),
    ('"PyOCD 目标设备筛选"', 'i18n("dialog.pyocd_target_filter")'),
    ('"选择Map文件"', 'i18n("dialog.select_map_file")'),
    ('"搜索:"', 'i18n("label.search")'),
    ('"输入关键字筛选"', 'i18n("placeholder.keyword_filter")'),
    ('"探测失败"', 'i18n("dialog.probe_detect_failed")'),
    ('"搜索失败"', 'i18n("dialog.search_failed")'),
    ('"错误"', 'i18n("dialog.error_title")'),
    ('"提示"', 'i18n("dialog.hint_title")'),
    ('"完成"', 'i18n("dialog.complete_title")'),
    ('"更新设备列表"', 'i18n("dialog.update_device_list")'),
    ('"更新 PyOCD 目标"', 'i18n("dialog.update_pyocd_target")'),
    ('"下载 Pack"', 'i18n("dialog.download_pack")'),
    ('"下载失败"', 'i18n("dialog.download_failed")'),
    ('"下载成功"', 'i18n("dialog.download_success")'),
    ('"下载 CMSIS Pack"', 'i18n("dialog.download_cmsis_pack")'),
    ('"-- 请点击「刷新」探测探针 --"', 'i18n("error.please_click_refresh")'),
    ('"-- 调试器管理器未初始化 --"', 'i18n("error.debugger_not_init")'),
    ('"正在探测..."', 'i18n("error.detecting")'),
    ('"-- 未探测到探针 --"', 'i18n("error.probe_not_found")'),
    ('"-- 探测失败 --"', 'i18n("error.probe_detect_error")'),
    ('"正在更新目标索引..."', 'i18n("error.updating_target_index")'),
    ('"正在从DLL读取设备列表..."', 'i18n("error.reading_device_list")'),
    ('"未找到JLink DLL文件"', 'i18n("error.jlink_dll_not_found")'),
    ('"未能从DLL读取到设备列表"', 'i18n("error.device_list_read_failed")'),
    ('"请先选择设备型号"', 'i18n("error.please_select_device")'),
    ('"请先选择map文件"', 'i18n("error.please_select_map_file")'),
    ('"未找到_SEGGER_RTT符号"', 'i18n("error.rtt_symbol_not_found")'),
    ('"选择颜色"', 'i18n("btn.select_color")'),
    ('QRadioButton("自动检测")', 'QRadioButton(i18n("combo.rtt_auto_detect"))'),
    ('QRadioButton("地址:")', 'QRadioButton(i18n("combo.rtt_address"))'),
    ('QRadioButton("搜索范围:")', 'QRadioButton(i18n("combo.rtt_range"))'),
    ('"map文件路径（可手动编辑）"', 'i18n("placeholder.map_file_path")'),
    ('"刷新 PyOCD 目标索引"', 'i18n("tooltip.refresh_pyocd_index")'),
    ('"下载 CMSIS Pack 增强芯片支持"', 'i18n("tooltip.download_cmsis_pack")'),
    ('"全部"', 'i18n("combo.all")'),
    ('"内置"', 'i18n("combo.builtin")'),
    ('"Pack"', 'i18n("combo.pack")'),
]

count = 0
for old, new in replacements:
    if old in content:
        content = content.replace(old, new)
        count += 1

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print(f"Replaced {count} strings in connection_dialog.py")