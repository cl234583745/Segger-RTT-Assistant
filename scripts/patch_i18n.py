#!/usr/bin/env python3
"""Batch i18n patcher for RTT-Assistant UI files."""
import re
import sys

def patch_file(filepath, replacements, extra_ops=None):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
        else:
            print(f"  WARNING: not found: {old[:60]}...")
    
    if extra_ops:
        content = extra_ops(content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  Patched: {filepath}")

def patch_main_window():
    filepath = 'G:/opencode/RTT-Assistant/src/python/rtt_tool/ui/main_window.py'
    
    replacements = [
        # Toolbar buttons
        ('QAction("连接", self)', 'QAction(i18n("menu.connect"), self)'),
        ('QAction("配置", self)', 'QAction(i18n("menu.config"), self)'),
        ('QAction("断开", self)', 'QAction(i18n("menu.disconnect"), self)'),
        ('QAction("清空", self)', 'QAction(i18n("menu.clear"), self)'),
        
        # Tooltips for toolbar
        ('"使用上次配置连接"', 'i18n("tooltip.quick_connect")'),
        ('"配置连接参数"', 'i18n("tooltip.config_params")'),
        ('"断开连接"', 'i18n("tooltip.disconnect")'),
        ('"清空接收区"', 'i18n("tooltip.clear_receive")'),
        
        # Mode menu
        ('QMenu(self)', 'QMenu(self)'),  # skip, handled below
        
        # Send area
        ('QGroupBox("发送区 (CH0↓)")', 'QGroupBox(i18n("group.send"))'),
        ('QCheckBox("时间戳")', 'QCheckBox(i18n("btn.timestamp"))'),
        ('QCheckBox("HEX显示")', 'QCheckBox(i18n("btn.hex_display"))'),
        ('"显示时间戳"', 'i18n("tooltip.show_timestamp")'),
        ('"以HEX格式显示数据"', 'i18n("tooltip.hex_display")'),
        ('QPushButton("发送")', 'QPushButton(i18n("btn.send"))'),
        ('QPushButton("模式")', 'QPushButton(i18n("menu.mode"))'),
        ('QPushButton("工具")', 'QPushButton(i18n("menu.tool"))'),
        ('QPushButton("帮助")', 'QPushButton(i18n("menu.help"))'),
        ('QPushButton("日志")', 'QPushButton(i18n("menu.log"))'),
        ('QPushButton("重置")', 'QPushButton(i18n("btn.reset"))'),
        ('"重置收发计数"', 'i18n("tooltip.reset_counters")'),
        ('"发送模式"', 'i18n("tooltip.send_mode")'),
        ('"发送时自动添加换行符"', 'i18n("tooltip.add_newline")'),
        ('"发送数据 (或按 Enter 直接发送)\\nShift+Enter 换行"', 'i18n("tooltip.send_data")'),
        ('"Enter=发送  Shift+Enter=换行"', 'i18n("placeholder.send_input")'),
        
        # Status
        ('self.set_status("未连接")', 'self.set_status(STATUS_DISCONNECTED)'),
        
        # Theme actions
        ('QAction("暗色", self)', 'QAction(i18n("theme.dark"), self)'),
        ('QAction("亮色", self)', 'QAction(i18n("theme.light"), self)'),
        
        # Tool menu items
        ('QAction("字体", self)', 'QAction(i18n("menu.font"), self)'),
        ('"设置字体"', 'i18n("tooltip.set_font")'),
        ('QAction("ANSI染色", self)', 'QAction(i18n("group.ansi_color"), self)'),
        ('"解析ANSI转义码进行颜色渲染(默认关闭)"', 'i18n("tooltip.ansi_color")'),
        ('QAction("启用", self)', 'QAction(i18n("btn.enable"), self)'),
        ('"启用关键字高亮(默认开启)"', 'i18n("tooltip.keyword_enable")'),
        ('QAction("规则配置", self)', 'QAction(i18n("group.keyword_rule_config"), self)'),
        ('"配置关键字高亮规则"', 'i18n("tooltip.keyword_config")'),
        
        # Help menu
        ('QAction("反馈", self)', 'QAction(i18n("group.feedback"), self)'),
        ('"Bug反馈：发送日志给作者"', 'i18n("tooltip.bug_feedback")'),
        ('QAction("使用说明", self)', 'QAction(i18n("dialog.usage_doc"), self)'),
        ('"打开使用说明文档"', 'i18n("tooltip.usage_doc")'),
        ('QAction("更新说明", self)', 'QAction(i18n("dialog.changelog"), self)'),
        ('"查看更新说明"', 'i18n("tooltip.changelog")'),
        ('QAction("升级指南", self)', 'QAction(i18n("dialog.upgrade_guide"), self)'),
        ('"查看升级指南"', 'i18n("tooltip.upgrade_guide")'),
        ('QAction("RTT介绍", self)', 'QAction(i18n("group.rtt_intro"), self)'),
        ('"打开SEGGER RTT官方文档"', 'i18n("tooltip.rtt_intro")'),
        ('QAction("RTT源码", self)', 'QAction(i18n("group.rtt_source"), self)'),
        ('"查看SEGGER RTT源码"', 'i18n("tooltip.rtt_source")'),
        ('QAction("移植文档", self)', 'QAction(i18n("group.rtt_porting"), self)'),
        ('"查看SEGGER RTT移植指南"', 'i18n("tooltip.rtt_porting")'),
        ('QAction("依赖管理", self)', 'QAction(i18n("group.dep_manage"), self)'),
        ('"管理运行时依赖和升级"', 'i18n("tooltip.dep_manage")'),
        ('QAction("关于", self)', 'QAction(i18n("group.about"), self)'),
        ('"关于RTT Assistant"', 'i18n("tooltip.about")'),
        
        # Log menu
        ('QAction("系统日志", self)', 'QAction(i18n("group.system_log"), self)'),
        ('"显示系统日志窗口"', 'i18n("tooltip.system_log")'),
        ('QAction("收发数据日志", self)', 'QAction(i18n("group.data_log"), self)'),
        ('"打开收发数据日志文件夹"', 'i18n("tooltip.data_log")'),
        ('QAction("日志管理", self)', 'QAction(i18n("group.log_manage"), self)'),
        
        # Window topmost
        ('"窗口置顶"', 'i18n("tooltip.window_topmost")'),
        
        # Keyword highlight dialog
        ('"关键字高亮配置"', 'i18n("dialog.keyword_config")'),
        ('"选择字体"', 'i18n("dialog.select_font")'),
        ('["关键字", "颜色"]', '[i18n("header.keyword"), i18n("header.color")]'),
        ('QPushButton("添加")', 'QPushButton(i18n("btn.add"))'),
        ('QPushButton("删除")', 'QPushButton(i18n("btn.delete"))'),
        ('QPushButton("选择颜色")', 'QPushButton(i18n("btn.select_color"))'),
        ('"选择通道颜色"', 'i18n("dialog.select_channel_color")'),
        ('"选择颜色"', 'i18n("btn.select_color")'),
        
        # HEX format errors
        ('"HEX格式错误"', 'i18n("error.hex_format")'),
        ('"HEX数据不能为空"', 'i18n("error.hex_empty")'),
        
        # About dialog
        ('"关于 RTT Assistant"', 'i18n("dialog.about")'),
        ('"RTT调试助手"', 'i18n("label.rtt_assistant_desc")'),
        ('"基于SEGGER JLink RTT技术"', 'i18n("label.based_on_segger_rtt")'),
        ('"作者: 陈卡卡"', 'i18n("label.author") + " " + i18n("label.author_name")'),
        ('"公众号: 嵌入式科普"', 'i18n("label.wechat_public")'),
        ('"B站: 嵌入式科普"', 'i18n("label.bilibili") + " " + i18n("label.wechat_name")'),
        ('QPushButton("检查更新")', 'QPushButton(i18n("btn.check_update"))'),
        
        # Bug feedback dialog
        ('"Bug反馈"', 'i18n("dialog.bug_feedback")'),
        ('"如遇Bug，请将log文件夹发送至：可复制邮箱"', 'i18n("label.bug_feedback_hint")'),
        ('"我们会尽快修复。"', 'i18n("label.will_fix_soon")'),
        ("QPushButton('确定')", 'QPushButton(i18n("btn.ok"))'),
        
        # Doc not found messages
        ('"文档未找到，请查看doc/目录"', 'i18n("error.doc_not_found")'),
        ('"无法打开网页"', 'i18n("error.cannot_open_web")'),
        ('"打开依赖管理失败"', 'i18n("error.open_dep_manage_failed")'),
        
        # Export dialog
        ('"导出收发数据"', 'i18n("dialog.export_data")'),
        ('"文本文件 (*.txt);;所有文件 (*)"', 'f"{i18n(\'filter.text_file\')} (*.txt);;{i18n(\'filter.all_file\')} (*)"'),
        
        # QR code dialog
        ('"公众号: 嵌入式科普"', 'i18n("label.wechat_public")'),
        ('"扫码关注公众号"', 'i18n("label.scan_qrcode")'),
        ('"无法加载二维码图片"', 'i18n("label.cannot_load_qrcode")'),
        ('"未找到二维码图片"', 'i18n("label.qrcode_not_found")'),
    ]
    
    def extra_ops(content):
        # Fix theme change handler
        content = content.replace(
            "theme = 'dark' if action.text() == '暗色' else 'light'",
            "theme = action.data() or 'dark'"
        )
        
        # Add setData to theme actions
        content = content.replace(
            'self._theme_dark_action = QAction(i18n("theme.dark"), self)',
            'self._theme_dark_action = QAction(i18n("theme.dark"), self)\n        self._theme_dark_action.setData("dark")'
        )
        content = content.replace(
            'self._theme_light_action = QAction(i18n("theme.light"), self)',
            'self._theme_light_action = QAction(i18n("theme.light"), self)\n        self._theme_light_action.setData("light")'
        )
        
        # Fix mode menu - add setData
        content = content.replace(
            'self._mode_menu.addAction(i18n("mode.log"))',
            '_log_act = QAction(i18n("mode.log"), self); _log_act.setData("log"); self._mode_menu.addAction(_log_act)'
        )
        content = content.replace(
            'self._mode_menu.addAction(i18n("mode.oscilloscope"))',
            '_osc_act = QAction(i18n("mode.oscilloscope"), self); _osc_act.setData("oscilloscope"); self._mode_menu.addAction(_osc_act)'
        )
        content = content.replace(
            'self._mode_menu.addAction(i18n("mode.mixed"))',
            '_mix_act = QAction(i18n("mode.mixed"), self); _mix_act.setData("mixed"); self._mode_menu.addAction(_mix_act)'
        )
        
        # Fix send mode combo - add userData
        content = content.replace(
            'self.send_mode_combo.addItem(i18n("combo.send_string"))',
            'self.send_mode_combo.addItem(i18n("combo.send_string"), "string")'
        )
        content = content.replace(
            'self.send_mode_combo.addItem(i18n("combo.send_hex"))',
            'self.send_mode_combo.addItem(i18n("combo.send_hex"), "hex")'
        )
        
        # Fix HEX check - use currentData
        content = content.replace(
            'self.send_mode_combo.currentText() == "HEX"',
            'self.send_mode_combo.currentData() == "hex"'
        )
        content = content.replace(
            'self.send_mode_combo.currentText() == i18n("combo.send_hex")',
            'self.send_mode_combo.currentData() == "hex"'
        )
        
        # Fix set_status method
        old_set_status = '''def set_status(self, text):
        self.status_label.setText(text)'''
        new_set_status = '''def set_status(self, status_id, detail=""):
        text = i18n(_STATUS_KEY_MAP.get(status_id, status_id))
        if detail:
            text = f"{text} - {detail}"
        self.status_label.setText(text)'''
        content = content.replace(old_set_status, new_set_status)
        
        # Fix status color mapping
        old_color_map = '''color_map = {
            "未连接": "#888888",
            "连接中": "#FF8800",
            "已连接": "#00AA00",
        }
        bg = color_map.get(text, "")'''
        new_color_map = '''bg = _STATUS_COLOR_MAP.get(status_id, "")'''
        content = content.replace(old_color_map, new_color_map)
        
        # Fix status label style setting
        old_style = '''if bg:
            self.status_label.setStyleSheet(
                f"background-color: {bg}; color: #ffffff; padding: 0 6px; font-weight: bold; border-radius: 2px;"
            )
        else:
            self.status_label.setStyleSheet("")'''
        # This part should already be there from set_status replacement
        # But need to ensure the old set_status body is fully replaced
        
        # Add language menu after theme menu in _create_toolbar
        # Find the tool_menu section and add language menu
        lang_menu_code = '''
        # Language menu
        lang_menu = QMenu(i18n("menu.language"), self)
        self._lang_zh_action = QAction("中文", self)
        self._lang_zh_action.setData("zh")
        self._lang_zh_action.setCheckable(True)
        self._lang_en_action = QAction("English", self)
        self._lang_en_action.setData("en")
        self._lang_en_action.setCheckable(True)
        self._lang_group = QActionGroup(self)
        self._lang_group.addAction(self._lang_zh_action)
        self._lang_group.addAction(self._lang_en_action)
        self._lang_group.setExclusive(True)
        self._lang_group.triggered.connect(self._on_language_menu_changed)
        lang_menu.addAction(self._lang_zh_action)
        lang_menu.addAction(self._lang_en_action)
        tool_menu.addMenu(lang_menu)
        _cur_lang = i18n_get_language()
        self._lang_zh_action.setChecked(_cur_lang == "zh")
        self._lang_en_action.setChecked(_cur_lang == "en")
'''
        # Insert after theme menu trigger connect
        content = content.replace(
            'self._theme_group.triggered.connect(self._on_tools_theme_changed)',
            'self._theme_group.triggered.connect(self._on_tools_theme_changed)\n' + lang_menu_code
        )
        
        # Add _on_language_menu_changed method and _refresh_on_language_changed
        # Find a good place to insert - before _on_tools_theme_changed
        lang_methods = '''
    def _on_language_menu_changed(self, action):
        lang = action.data() or "zh"
        i18n_set_language(lang)

    def _refresh_on_language_changed(self, lang):
        """语言变更时刷新所有UI文本"""
        # Toolbar actions
        self.connect_action.setText(i18n("menu.connect"))
        self.connect_action.setToolTip(i18n("tooltip.quick_connect"))
        config_act = self.findChild(QAction, "")  # skip, refresh by text
        # Mode menu
        for act in self._mode_menu.actions():
            mode = act.data()
            if mode == "log":
                act.setText(i18n("mode.log"))
            elif mode == "oscilloscope":
                act.setText(i18n("mode.oscilloscope"))
            elif mode == "mixed":
                act.setText(i18n("mode.mixed"))
        # Theme actions
        self._theme_dark_action.setText(i18n("theme.dark"))
        self._theme_light_action.setText(i18n("theme.light"))
        # Language actions
        self._lang_zh_action.setChecked(lang == "zh")
        self._lang_en_action.setChecked(lang == "en")
        # Status bar
        if hasattr(self, '_current_status_id'):
            self.set_status(self._current_status_id, getattr(self, '_current_status_detail', ''))
        # Group boxes
        if hasattr(self, '_receive_group'):
            self._receive_group.setTitle(i18n("group.receive"))
        if hasattr(self, '_send_group'):
            self._send_group.setTitle(i18n("group.send"))
        # Send area
        self.send_mode_combo.setItemText(0, i18n("combo.send_string"))
        self.send_mode_combo.setItemText(1, i18n("combo.send_hex"))
        if hasattr(self, 'add_newline_checkbox'):
            self.add_newline_checkbox.setText(i18n("btn.add_newline"))
        self.send_input.setPlaceholderText(i18n("placeholder.send_input"))
        # Checkboxes
        if hasattr(self, 'timestamp_checkbox'):
            self.timestamp_checkbox.setText(i18n("btn.timestamp"))
        if hasattr(self, 'hex_display_checkbox'):
            self.hex_display_checkbox.setText(i18n("btn.hex_display"))
        # Buttons
        if hasattr(self, '_mode_button'):
            self._mode_button.setText(i18n("menu.mode"))
        if hasattr(self, '_tool_button'):
            self._tool_button.setText(i18n("menu.tool"))
        if hasattr(self, '_help_button'):
            self._help_button.setText(i18n("menu.help"))
        if hasattr(self, '_log_button'):
            self._log_button.setText(i18n("menu.log"))
        # Window title
        self.setWindowTitle(f'RTT Assistant v{__version__}')

'''
        content = content.replace(
            'def _on_tools_theme_changed(self, action):',
            lang_methods + '    def _on_tools_theme_changed(self, action):'
        )
        
        # Connect language_changed signal in __init__ or init_ui
        # Find the end of __init__ or a suitable place
        content = content.replace(
            'self.waveform_widget.set_color_theme(theme)',
            'self.waveform_widget.set_color_theme(theme)\n        # Connect i18n signal\n        _sig = i18n_language_changed()\n        if _sig:\n            _sig.connect(self._refresh_on_language_changed)'
        )
        
        # Fix mode menu click handler - remove text_to_mode dict
        content = re.sub(
            r'text_to_mode = \{[^}]+\}\s*new_mode = text_to_mode\.get\(action\.text\(\)\)',
            'new_mode = action.data()',
            content
        )
        
        # Fix receive group box
        content = content.replace(
            'QGroupBox("接收区 (CH0)")',
            'QGroupBox(i18n("group.receive"))'
        )
        
        # Fix mode name mapping
        content = content.replace(
            "{'log': '日志', 'oscilloscope': '示波器', 'mixed': '混合'}",
            "{'log': i18n('mode.log'), 'oscilloscope': i18n('mode.oscilloscope'), 'mixed': i18n('mode.mixed')}"
        )
        
        # Store current status for refresh
        content = content.replace(
            'def set_status(self, status_id, detail=""):\n        text = i18n(_STATUS_KEY_MAP.get(status_id, status_id))\n        if detail:\n            text = f"{text} - {detail}"\n        self.status_label.setText(text)',
            'def set_status(self, status_id, detail=""):\n        self._current_status_id = status_id\n        self._current_status_detail = detail\n        text = i18n(_STATUS_KEY_MAP.get(status_id, status_id))\n        if detail:\n            text = f"{text} - {detail}"\n        self.status_label.setText(text)'
        )
        
        # Fix connection status updates
        content = content.replace(
            'self.set_status("已连接")',
            'self.set_status(STATUS_CONNECTED)'
        )
        content = content.replace(
            'self.set_status("未连接")',
            'self.set_status(STATUS_DISCONNECTED)'
        )
        
        # Fix channel name labels that use Chinese
        content = content.replace(
            '"通道名: Terminal (日志通道)"',
            'i18n("label.channel") + ": Terminal"'
        )
        content = content.replace(
            '"数据类型: 文本"',
            'i18n("label.type") + ": Text"'
        )
        content = content.replace(
            '"RTT Assistant CH0 数据日志"',
            '"RTT Assistant CH0 " + i18n("label.channel") + " " + i18n("mode.log")'
        )
        
        # Fix keyword highlight menu
        content = content.replace(
            'QMenu("关键字高亮", self)',
            'QMenu(i18n("group.keyword_highlight"), self)'
        )
        
        # Fix theme menu
        content = content.replace(
            'QMenu("主题", self)',
            'QMenu(i18n("menu.theme"), self)'
        )
        
        # Fix tool/help/log menus
        content = content.replace(
            'QMenu("工具", self)',
            'QMenu(i18n("menu.tool"), self)'
        )
        content = content.replace(
            'QMenu("帮助", self)',
            'QMenu(i18n("menu.help"), self)'
        )
        content = content.replace(
            'QMenu("日志", self)',
            'QMenu(i18n("menu.log"), self)'
        )
        
        # Fix probe_info_label
        content = content.replace(
            '"支持设备:',
            'i18n("label.supported_devices") + ":'  # approximate
        )
        
        # Fix "J-Link DLL读取失败"
        content = content.replace(
            '"J-Link DLL读取失败"',
            'i18n("error.jlink_dll_read_failed")'
        )
        
        # Fix "PyOCD: 未安装"
        content = content.replace(
            '"PyOCD: 未安装"',
            '"PyOCD: " + i18n("error.not_installed")'
        )
        
        return content
    
    patch_file(filepath, replacements, extra_ops)

if __name__ == '__main__':
    print("Patching main_window.py...")
    patch_main_window()
    print("Done!")