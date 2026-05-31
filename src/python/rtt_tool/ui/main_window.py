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
主窗口UI
包含工具栏、接收区、发送区、状态栏
"""

import functools

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QComboBox,
    QCheckBox, QLabel, QStatusBar, QToolBar, QAction,
    QSplitter, QGroupBox, QFileDialog, QMenu, QMessageBox,
    QStackedWidget, QSizePolicy, QActionGroup, QDialog,
    QFontDialog
)
from PyQt5.QtCore import Qt, pyqtSignal, QEvent, QObject, QTimer
from PyQt5.QtGui import QFont, QTextCursor
from PyQt5.QtWidgets import QApplication as QApp
from .connection_dialog import ConnectionDialog
from .log_window import LogWindow
from .waveform_widget import WaveformWidget
from .channel_panel import ChannelPanel
from ..utils.resource_utils import get_resource_path, is_frozen, get_external_file, get_exe_dir
from .. import __version__
from ..i18n import _ as i18n, language_changed as i18n_language_changed, set_language as i18n_set_language, get_language as i18n_get_language


STATUS_DISCONNECTED = "disconnected"
STATUS_CONNECTING = "connecting"
STATUS_CONNECTED = "connected"
STATUS_READY = "ready"
STATUS_LOADING_BACKEND = "loading_backend"
STATUS_INITIALIZING = "initializing"
STATUS_DISCONNECTING = "disconnecting"
STATUS_ERROR = "error"
STATUS_WARNING = "warning"

_STATUS_KEY_MAP = {
    STATUS_DISCONNECTED: "status.disconnected",
    STATUS_CONNECTING: "status.connecting",
    STATUS_CONNECTED: "status.connected",
    STATUS_READY: "status.ready",
    STATUS_LOADING_BACKEND: "status.loading_backend",
    STATUS_INITIALIZING: "status.initializing",
    STATUS_DISCONNECTING: "status.disconnecting",
    STATUS_ERROR: "status.error",
    STATUS_WARNING: "status.warning",
}

_STATUS_COLOR_MAP = {
    STATUS_DISCONNECTED: "#888888",
    STATUS_CONNECTING: "#FF8800",
    STATUS_CONNECTED: "#00AA00",
}


DARK_STYLESHEET = """
* { background-color: #2b2b2b; color: #e0e0e0; }
QGroupBox { border: 1px solid #555; margin-top: 1ex; font-weight: bold; }
QGroupBox::title { color: #e0e0e0; subcontrol-origin: margin; left: 10px; padding: 0 6px; }
QTextEdit, QLineEdit, QPlainTextEdit { background-color: #1e1e1e; color: #e0e0e0; border: 1px solid #555; }
QTextEdit:disabled, QLineEdit:disabled, QPlainTextEdit:disabled { background-color: #252525; color: #666; border: 1px dashed #444; }
QComboBox { background-color: #3c3c3c; color: #e0e0e0; border: 1px solid #555; padding-right: 16px; min-width: 60px; }
QComboBox:disabled { background-color: #2a2a2a; color: #666; border: 1px dashed #444; }
QComboBox QAbstractItemView { background-color: #3c3c3c; color: #e0e0e0; selection-background-color: #505050; }
QPushButton { background-color: #3c3c3c; color: #e0e0e0; border: 2px solid #666; border-radius: 3px; padding: 4px 8px; }
QPushButton:hover { background-color: #505050; border-color: #888; }
QPushButton:pressed { background-color: #2a2a2a; border-color: #444; padding-top: 5px; padding-bottom: 3px; }
QPushButton:disabled { background-color: #2a2a2a; color: #666; border: 1px dashed #444; }
QCheckBox { color: #e0e0e0; spacing: 4px; }
QCheckBox:disabled { color: #666; }
QSpinBox, QDoubleSpinBox { background-color: #3c3c3c; color: #e0e0e0; border: 1px solid #555; }
QSpinBox:disabled, QDoubleSpinBox:disabled { background-color: #2a2a2a; color: #666; border: 1px dashed #444; }
QStatusBar, QToolBar { background-color: #333; color: #e0e0e0; border: none; spacing: 4px; }
QMenu { background-color: #3c3c3c; color: #e0e0e0; border: 1px solid #555; }
QMenu::item:selected { background-color: #505050; }
QSplitter::handle { background-color: #555; }
QToolTip { background-color: #3c3c3c; color: #e0e0e0; border: 1px solid #555; }
QHeaderView { background-color: #3c3c3c; color: #e0e0e0; }
QHeaderView::section { background-color: #3c3c3c; color: #e0e0e0; border: 1px solid #555; padding: 4px; }
QTableWidget { background-color: #1e1e1e; color: #e0e0e0; border: 1px solid #555; }

QDialog { background-color: #2b2b2b; }
QListWidget { background-color: #1e1e1e; color: #e0e0e0; border: 1px solid #555; }
QListWidget::item:selected { background-color: #094771; }
QRadioButton { color: #e0e0e0; }
QRadioButton:disabled { color: #666; }
QLabel:disabled { color: #666; }
QToolButton { background-color: #3c3c3c; color: #e0e0e0; border: 2px solid #666; border-radius: 3px; padding: 4px 8px; }
QToolButton:hover { background-color: #505050; border-color: #888; }
QToolButton:pressed { background-color: #2a2a2a; border-color: #444; padding-top: 5px; padding-bottom: 3px; }
QToolButton:disabled { background-color: #2a2a2a; color: #666; border: 1px dashed #444; }
QGroupBox QWidget { background: transparent; }
"""

LIGHT_STYLESHEET = """
QToolButton { background-color: #f0f0f0; color: #333; border: 2px solid #aaa; border-radius: 3px; padding: 4px 8px; }
QToolButton:hover { background-color: #e0e0e0; border-color: #888; }
QToolButton:pressed { background-color: #d0d0d0; border-color: #666; padding-top: 5px; padding-bottom: 3px; }
QToolButton:disabled { background-color: #f5f5f5; color: #bbb; border: 1px dashed #ccc; }
QLabel:disabled { color: #bbb; }
QListWidget::item:selected { background-color: #094771; color: #ffffff; }
"""


def set_dark_title_bar(widget, dark):
    try:
        import ctypes
        hwnd = ctypes.wintypes.HWND(int(widget.winId()))
        DwmSetWindowAttribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
        value = ctypes.c_int(2 if dark else 0)
        for attr_id in (20, 19):
            DwmSetWindowAttribute(hwnd, attr_id, ctypes.byref(value), ctypes.sizeof(value))
    except Exception:
        pass


class DarkTitleBarFilter(QObject):
    """全局事件过滤器：自动为新弹出的顶层窗口设置暗色标题栏。"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._dark = False

    def set_dark(self, dark: bool) -> None:
        self._dark = dark

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Show and isinstance(obj, QWidget) and obj.isWindow():
            if self._dark:
                QTimer.singleShot(0, lambda o=obj: set_dark_title_bar(o, True))
        return super().eventFilter(obj, event)


def _patch_qdialog_dark_title_bar():
    """Monkey-patch QDialog.showEvent 使所有现有和未来的对话框自动应用暗色标题栏。"""
    original_show = QDialog.showEvent
    @functools.wraps(original_show)
    def _show_event(self, event):
        original_show(self, event)
        try:
            from PyQt5.QtWidgets import QApplication as QApp
            app = QApp.instance()
            if app is not None:
                dark = app.property('_dark_theme')
                if dark is None or dark:
                    set_dark_title_bar(self, True)
        except Exception:
            pass
    QDialog.showEvent = _show_event


def install_dark_title_bar_filter(app):
    """在 QApplication 上安装全局暗色标题栏过滤器 + 自动补丁所有 QDialog。"""
    filter_ = DarkTitleBarFilter(app)
    app.installEventFilter(filter_)
    app.setProperty('_dark_title_bar_filter', filter_)
    _patch_qdialog_dark_title_bar()
    return filter_


class MainWindow(QMainWindow):
    """主窗口"""
    
    # 信号定义
    connect_requested = pyqtSignal(dict)  # 连接请求信号（配置字典）
    quick_connect_requested = pyqtSignal()  # 快速连接请求信号（使用上次配置）
    disconnect_requested = pyqtSignal()  # 断开连接请求信号
    send_requested = pyqtSignal(str, bool, bool)  # 发送请求信号（数据、是否HEX、是否加换行）
    clear_requested = pyqtSignal()  # 清空请求信号
    font_changed = pyqtSignal(QFont)  # 字体改变信号
    timestamp_toggled = pyqtSignal(bool)  # 时间戳开关信号
    hex_display_toggled = pyqtSignal(bool)  # HEX显示开关信号
    config_changed = pyqtSignal(dict)  # 配置改变信号
    reset_counters_requested = pyqtSignal()  # 重置计数器信号
    mode_changed = pyqtSignal(str)  # 模式切换信号 ("log"/"oscilloscope"/"mixed")
    flash_requested = pyqtSignal()  # 烧录请求信号
    
    def __init__(self):
        super().__init__()
        _t0 = __import__('time').perf_counter()
        self.log_window = None
        self.log_service = None
        self.device_info_service = None
        self.last_config = {}
        
        from datetime import datetime
        import os
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        from ..runtime.path_config import RUNTIME_LOG_DIR
        self.data_log_file = os.path.join(RUNTIME_LOG_DIR, f"rtt_data_CH0_{timestamp}.log")
        self.data_log_handle = None
        self._channel_log_handles = {}

        self._max_display_lines = 1000
        
        self._log_throttle_enabled = True
        self._log_throttle_interval_ms = 50
        self._log_throttle_max_buffer_bytes = 65536
        self._pending_text = ''
        self._pending_signal_count = 0
        self._diagnostic_log_enabled = True
        self._log_manage_dialog = None
        from PyQt5.QtCore import QTimer
        self._log_throttle_timer = QTimer(self)
        self._log_throttle_timer.setInterval(self._log_throttle_interval_ms)
        self._log_throttle_timer.timeout.connect(self._flush_pending_log_text)
        
        try:
            self.data_log_handle = open(self.data_log_file, 'a', encoding='utf-8')
            self.data_log_handle.write(f"RTT Assistant CH0 数据日志\n")
            self.data_log_handle.write(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            self.data_log_handle.write(f"通道名: Terminal (日志通道)\n")
            self.data_log_handle.write(f"数据类型: 文本\n")
            self.data_log_handle.write(f"{'='*60}\n\n")
            self.data_log_handle.flush()
        except Exception as e:
            print(f"无法创建数据日志文件: {e}")
        
        self._log_timestamp = timestamp
        
        self.init_ui()
        print(f"[perf] MainWindow.__init__: {(__import__('time').perf_counter()-_t0)*1000:.0f}ms")
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle(f'{i18n("app.title")} v{__version__}')
        self.setGeometry(100, 100, 1000, 700)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建工具栏
        self._create_toolbar()
        
        # 使用QSplitter实现可拖拽调整大小
        splitter = QSplitter(Qt.Vertical)
        
        # 设置分隔条样式
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #3498db;
                height: 8px;
            }
            QSplitter::handle:hover {
                background-color: #2980b9;
            }
            QSplitter::handle:pressed {
                background-color: #1c5ea0;
            }
        """)
        
        # 创建接收区
        self._receive_group = self._create_receive_area()
        
        # 创建波形显示组件
        self.waveform_widget = WaveformWidget()
        
        # 使用 QStackedWidget 管理三种显示模式
        self._display_stack = QStackedWidget()
        
        # 日志模式页面
        self._log_page = QWidget()
        log_layout = QVBoxLayout(self._log_page)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_layout.addWidget(self._receive_group)
        self._display_stack.addWidget(self._log_page)
        
        # 示波器模式页面
        self._oscilloscope_page = QWidget()
        osc_layout = QVBoxLayout(self._oscilloscope_page)
        osc_layout.setContentsMargins(0, 0, 0, 0)

        self._osc_splitter = QSplitter(Qt.Horizontal)
        self._osc_splitter.addWidget(self.waveform_widget)

        self.channel_panel = ChannelPanel()
        self._osc_splitter.addWidget(self.channel_panel)

        self._osc_splitter.setStretchFactor(0, 3)
        self._osc_splitter.setStretchFactor(1, 0)
        self._osc_splitter.setSizes([700, ChannelPanel.COLLAPSED_WIDTH])

        osc_layout.addWidget(self._osc_splitter)
        self._display_stack.addWidget(self._oscilloscope_page)
        
        # 混合模式页面（接收区和波形上下分割）
        self._mixed_page = QWidget()
        mixed_layout = QVBoxLayout(self._mixed_page)
        mixed_layout.setContentsMargins(0, 0, 0, 0)
        self._mixed_splitter = QSplitter(Qt.Vertical)
        mixed_layout.addWidget(self._mixed_splitter)
        self._display_stack.addWidget(self._mixed_page)
        
        # 初始显示日志模式，混合模式页面延迟填充
        self._current_mode = 'log'
        self._display_stack.setCurrentIndex(0)
        
        splitter.addWidget(self._display_stack)
        
        # 创建发送区
        send_group = self._create_send_area()
        splitter.addWidget(send_group)
        
        # 设置初始比例(显示区大, 发送区~2行)
        splitter.setSizes([600, 120])
        
        main_layout.addWidget(splitter)
        
        # 创建状态栏
        self._create_status_bar()
    
    def _create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar(i18n("menu.toolbar"))
        toolbar.setObjectName("mainToolBar")
        self.addToolBar(toolbar)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self._toolbar = toolbar
        
        toolbar.setMovable(True)
        toolbar.setFloatable(False)
        toolbar.setContextMenuPolicy(Qt.PreventContextMenu)
        toolbar.setStyleSheet("QToolBar { spacing: 4px; padding: 2px; }")
        
        # 连接按钮 - 直接使用上次配置连接
        self.connect_action = QAction(i18n("menu.connect"), self)
        self.connect_action.setToolTip(i18n("tooltip.quick_connect"))
        self.connect_action.triggered.connect(self._on_quick_connect_clicked)
        toolbar.addAction(self.connect_action)
        
        # 配置按钮 - 打开配置对话框
        self.config_action = QAction(i18n("menu.config"), self)
        self.config_action.setToolTip(i18n("tooltip.config_params"))
        self.config_action.triggered.connect(self._on_config_clicked)
        toolbar.addAction(self.config_action)
        
        # 断开按钮
        self.disconnect_action = QAction(i18n("menu.disconnect"), self)
        self.disconnect_action.setToolTip(i18n("tooltip.disconnect"))
        self.disconnect_action.triggered.connect(self.disconnect_requested.emit)
        self.disconnect_action.setEnabled(False)
        toolbar.addAction(self.disconnect_action)
        
        toolbar.addSeparator()
        
        # 清空按钮
        self.clear_action = QAction(i18n("menu.clear"), self)
        self.clear_action.setToolTip(i18n("tooltip.clear_receive"))
        self.clear_action.triggered.connect(self._on_clear_clicked)
        toolbar.addAction(self.clear_action)
        
        toolbar.addSeparator()
        
        # 显示模式切换
        self._mode_menu = QMenu(self)
        self._mode_log_action = QAction(i18n("mode.log"), self)
        self._mode_log_action.setData("log")
        self._mode_osc_action = QAction(i18n("mode.oscilloscope"), self)
        self._mode_osc_action.setData("oscilloscope")
        self._mode_mixed_action = QAction(i18n("mode.mixed"), self)
        self._mode_mixed_action.setData("mixed")
        self._mode_menu.addAction(self._mode_log_action)
        self._mode_menu.addAction(self._mode_osc_action)
        self._mode_menu.addAction(self._mode_mixed_action)
        self._mode_menu.triggered.connect(self._on_mode_menu_clicked)

        self._mode_button = QPushButton(i18n("menu.mode"))
        self._mode_button.setMenu(self._mode_menu)
        toolbar.addWidget(self._mode_button)
        
        toolbar.addSeparator()
        
        # 烧录按钮
        self.flash_action = toolbar.addAction(i18n("btn.flash"))
        self.flash_action.setToolTip(i18n("tooltip.flash_firmware"))
        self.flash_action.triggered.connect(self._on_flash_clicked)
        self.flash_action.setEnabled(False)
        

        toolbar.addSeparator()
        
        # 时间戳开关
        self.timestamp_checkbox = QCheckBox(i18n("btn.timestamp"))
        self.timestamp_checkbox.setToolTip(i18n("tooltip.show_timestamp"))
        self.timestamp_checkbox.stateChanged.connect(
            lambda state: self.timestamp_toggled.emit(state == Qt.Checked)
        )
        toolbar.addWidget(self.timestamp_checkbox)
        
        # HEX显示开关
        self.hex_display_checkbox = QCheckBox(i18n("btn.hex_display"))
        self.hex_display_checkbox.setToolTip(i18n("tooltip.hex_display"))
        self.hex_display_checkbox.stateChanged.connect(
            lambda state: self.hex_display_toggled.emit(state == Qt.Checked)
        )
        toolbar.addWidget(self.hex_display_checkbox)
        
        # 语言切换按钮
        _cur = i18n_get_language()
        self._lang_toggle_btn = QPushButton("EN" if _cur == "zh" else "中")
        self._lang_toggle_btn.setToolTip(i18n("tooltip.switch_language"))
        self._lang_toggle_btn.setFixedWidth(40)
        self._lang_toggle_btn.clicked.connect(self._on_lang_toggle_clicked)
        toolbar.addWidget(self._lang_toggle_btn)
        
        toolbar.addSeparator()
        
        # 工具菜单
        self._tool_menu = QMenu(i18n("menu.tool"), self)
        
        # 字体设置
        font_action = QAction(i18n("menu.font"), self)
        font_action.setData("font")
        font_action.setToolTip(i18n("tooltip.set_font"))
        font_action.triggered.connect(self._on_font_clicked)
        self._tool_menu.addAction(font_action)
        
        self._tool_menu.addSeparator()
        
        # 主题切换
        theme_menu = QMenu(i18n("menu.theme"), self)
        self._theme_dark_action = QAction(i18n("theme.dark"), self)
        self._theme_dark_action.setData("dark")
        self._theme_dark_action.setCheckable(True)
        self._theme_light_action = QAction(i18n("theme.light"), self)
        self._theme_light_action.setData("light")
        self._theme_light_action.setCheckable(True)
        self._theme_group = QActionGroup(self)
        self._theme_group.addAction(self._theme_dark_action)
        self._theme_group.addAction(self._theme_light_action)
        self._theme_group.setExclusive(True)
        self._theme_group.triggered.connect(self._on_tools_theme_changed)

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
        self._tool_menu.addMenu(lang_menu)
        _cur_lang = i18n_get_language()
        self._lang_zh_action.setChecked(_cur_lang == "zh")
        self._lang_en_action.setChecked(_cur_lang == "en")

        theme_menu.addAction(self._theme_dark_action)
        theme_menu.addAction(self._theme_light_action)
        self._tool_menu.addMenu(theme_menu)
        
        self._tool_menu.addSeparator()
        
        # ANSI转义码染色开关
        self.ansi_color_action = QAction(i18n("group.ansi_color"), self)
        self.ansi_color_action.setData("ansi_color")
        self.ansi_color_action.setCheckable(True)
        self.ansi_color_action.setChecked(False)
        self.ansi_color_action.setToolTip(i18n("tooltip.ansi_color"))
        self._tool_menu.addAction(self.ansi_color_action)
        
        # 关键字高亮(含子菜单)
        keyword_menu = QMenu(i18n("group.keyword_highlight"), self)
        
        self.keyword_highlight_action = QAction(i18n("btn.enable"), self)
        self.keyword_highlight_action.setData("keyword_enable")
        self.keyword_highlight_action.setCheckable(True)
        self.keyword_highlight_action.setChecked(True)
        self.keyword_highlight_action.setToolTip(i18n("tooltip.keyword_enable"))
        keyword_menu.addAction(self.keyword_highlight_action)
        
        keyword_menu.addSeparator()
        
        keyword_config_action = QAction(i18n("group.keyword_rule_config"), self)
        keyword_config_action.setData("keyword_config")
        keyword_config_action.setToolTip(i18n("tooltip.keyword_config"))
        keyword_config_action.triggered.connect(self._on_keyword_highlight)
        keyword_menu.addAction(keyword_config_action)
        
        self._tool_menu.addMenu(keyword_menu)

        self._tool_menu.addSeparator()

        self.reset_config_action = self._tool_menu.addAction(i18n("menu.reset_config") if hasattr(self, '_tool_menu') else "恢复默认配置")
        self.reset_config_action.setToolTip("恢复所有配置为默认值并重启软件")
        self.reset_config_requested = self.reset_config_action.triggered

        # 添加工具菜单按钮
        self._tool_button = QPushButton(i18n("menu.tool"))
        self._tool_button.setMenu(self._tool_menu)
        toolbar.addWidget(self._tool_button)
        
        toolbar.addSeparator()
        
        # 帮助菜单
        self._help_menu = QMenu(i18n("menu.help"), self)
        
        help_action = QAction(i18n("group.feedback"), self)
        help_action.setData("feedback")
        help_action.setToolTip(i18n("tooltip.bug_feedback"))
        help_action.triggered.connect(self._on_help_contact)
        self._help_menu.addAction(help_action)
        
        usage_action = QAction(i18n("dialog.usage_doc"), self)
        usage_action.setData("usage")
        usage_action.setToolTip(i18n("tooltip.usage_doc"))
        usage_action.triggered.connect(self._on_usage_doc)
        self._help_menu.addAction(usage_action)
        
        changelog_action = QAction(i18n("dialog.changelog"), self)
        changelog_action.setData("changelog")
        changelog_action.setToolTip(i18n("tooltip.changelog"))
        changelog_action.triggered.connect(self._on_changelog)
        self._help_menu.addAction(changelog_action)
        
        upgrade_action = QAction(i18n("dialog.upgrade_guide"), self)
        upgrade_action.setData("upgrade")
        upgrade_action.setToolTip(i18n("tooltip.upgrade_guide"))
        upgrade_action.triggered.connect(self._on_upgrade_guide)
        self._help_menu.addAction(upgrade_action)
        
        self._help_menu.addSeparator()
        
        segger_menu = QMenu("SEGGER RTT", self)
        
        rtt_intro_action = QAction(i18n("group.rtt_intro"), self)
        rtt_intro_action.setData("rtt_intro")
        rtt_intro_action.setToolTip(i18n("tooltip.rtt_intro"))
        rtt_intro_action.triggered.connect(self._on_rtt_intro)
        segger_menu.addAction(rtt_intro_action)
        
        rtt_source_action = QAction(i18n("group.rtt_source"), self)
        rtt_source_action.setData("rtt_source")
        rtt_source_action.setToolTip(i18n("tooltip.rtt_source"))
        rtt_source_action.triggered.connect(self._on_rtt_source)
        segger_menu.addAction(rtt_source_action)
        
        rtt_porting_action = QAction(i18n("group.rtt_porting"), self)
        rtt_porting_action.setData("rtt_porting")
        rtt_porting_action.setToolTip(i18n("tooltip.rtt_porting"))
        rtt_porting_action.triggered.connect(self._on_rtt_porting)
        segger_menu.addAction(rtt_porting_action)
        
        self._help_menu.addMenu(segger_menu)
        
        self._help_menu.addSeparator()
        
        # 依赖管理
        dep_manage_action = QAction(i18n("group.dep_manage"), self)
        dep_manage_action.setData("dep_manage")
        dep_manage_action.setToolTip(i18n("tooltip.dep_manage"))
        dep_manage_action.triggered.connect(self._on_dependency_manage)
        self._help_menu.addAction(dep_manage_action)
        
        self._help_menu.addSeparator()
        
        # 关于
        about_action = QAction(i18n("group.about"), self)
        about_action.setData("about")
        about_action.setToolTip(i18n("tooltip.about"))
        about_action.triggered.connect(self._on_about)
        self._help_menu.addAction(about_action)
        
        # 添加帮助菜单按钮
        self._help_button = QPushButton(i18n("menu.help"))
        self._help_button.setMenu(self._help_menu)
        toolbar.addWidget(self._help_button)
        
        toolbar.addSeparator()
        
        # 日志菜单
        self._log_menu = QMenu(i18n("menu.log"), self)
        
        # 系统日志
        system_log_action = QAction(i18n("group.system_log"), self)
        system_log_action.setData("system_log")
        system_log_action.setToolTip(i18n("tooltip.system_log"))
        system_log_action.triggered.connect(self._on_log_clicked)
        self._log_menu.addAction(system_log_action)
        
        # 收发数据日志
        data_log_action = QAction(i18n("group.data_log"), self)
        data_log_action.setData("data_log")
        data_log_action.setToolTip(i18n("tooltip.data_log"))
        data_log_action.triggered.connect(self._on_open_data_log_folder)
        self._log_menu.addAction(data_log_action)
        
        log_manage_action = QAction(i18n("group.log_manage"), self)
        log_manage_action.setData("log_manage")
        log_manage_action.triggered.connect(self._on_log_manage_clicked)
        self._log_menu.addAction(log_manage_action)
        
        # 添加日志菜单按钮
        self._log_button = QPushButton(i18n("menu.log"))
        self._log_button.setMenu(self._log_menu)
        toolbar.addWidget(self._log_button)

        # 弹性空间将置顶按钮推到最右
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(spacer)

        # 窗口置顶按钮（书钉图标）
        self._pin_btn = QPushButton("📌")
        self._pin_btn.setToolTip(i18n("tooltip.window_topmost"))
        self._pin_btn.setCheckable(True)
        self._pin_btn.toggled.connect(self._on_pin_toggled)
        toolbar.addWidget(self._pin_btn)
    
    def _create_receive_area(self):
        """创建接收区"""
        self._receive_group = QGroupBox(i18n("group.receive"))
        layout = QVBoxLayout(self._receive_group)
        
        self.receive_text = QTextEdit()
        self.receive_text.setReadOnly(True)
        self.receive_text.setFont(QFont("Courier New", 10))
        layout.addWidget(self.receive_text)
        
        return self._receive_group
    
    def _create_send_area(self):
        """创建发送区"""
        self._send_group = QGroupBox(i18n("group.send"))
        layout = QVBoxLayout(self._send_group)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(3)
        
        # 发送文本框（占主要空间）
        self.send_input = QTextEdit()
        self.send_input.setFont(QFont("Courier New", 10))
        self.send_input.setMinimumHeight(20)
        self.send_input.setPlaceholderText(i18n("placeholder.send_input"))
        self.send_input.installEventFilter(self)
        layout.addWidget(self.send_input)
        
        # 底部行：模式 + 加换行 + 弹性空间 + 发送按钮
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(4)
        
        self._mode_label = QLabel(i18n("label.mode"))
        bottom_layout.addWidget(self._mode_label)
        
        self.send_mode_combo = QComboBox()
        self.send_mode_combo.addItem(i18n("combo.send_string"), "string")
        self.send_mode_combo.addItem(i18n("combo.send_hex"), "hex")
        self.send_mode_combo.setToolTip(i18n("tooltip.send_mode"))
        fm = self.send_mode_combo.fontMetrics()
        self.send_mode_combo.setMinimumWidth(fm.horizontalAdvance(i18n("combo.send_string")) + 30)
        bottom_layout.addWidget(self.send_mode_combo)
        
        self.add_newline_checkbox = QCheckBox(i18n("btn.add_newline"))
        self.add_newline_checkbox.setToolTip(i18n("tooltip.add_newline"))
        bottom_layout.addWidget(self.add_newline_checkbox)
        
        bottom_layout.addStretch()
        
        self.send_btn = QPushButton(i18n("btn.send"))
        self.send_btn.setToolTip(i18n("tooltip.send_data"))
        self.send_btn.clicked.connect(self._on_send_clicked)
        bottom_layout.addWidget(self.send_btn)
        
        layout.addLayout(bottom_layout)
        
        return self._send_group
    
    def _create_status_bar(self):
        """创建状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 创建状态标签
        self.status_label = QLabel()
        self.status_bar.addWidget(self.status_label)
        self.set_status(STATUS_DISCONNECTED)
        
        # 添加分隔符
        self.status_bar.addWidget(QLabel("  |  "))
        
        # 接收字节数
        self.rx_label = QLabel("RX: 0")
        self.status_bar.addWidget(self.rx_label)
        
        # 添加分隔符
        self.status_bar.addWidget(QLabel("  |  "))
        
        # 发送字节数
        self.tx_label = QLabel("TX: 0")
        self.status_bar.addWidget(self.tx_label)
        
        # 添加分隔符
        self.status_bar.addWidget(QLabel("  |  "))
        
        # 重置按钮
        self.reset_btn = QPushButton(i18n("btn.reset"))
        self.reset_btn.setToolTip(i18n("tooltip.reset_counters"))
        self.reset_btn.clicked.connect(self.reset_counters_requested.emit)
        self.status_bar.addWidget(self.reset_btn)
        
        # 添加弹性空间
        self.status_bar.addWidget(QLabel(""), 1)
        
        # 探针信息(连接时显示)
        self.probe_info_label = QLabel("")
        self.probe_info_label.setStyleSheet("color: #666666;")
        self.status_bar.addPermanentWidget(self.probe_info_label)
    
    def eventFilter(self, obj, event):
        if obj is self.send_input and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if event.modifiers() & Qt.ShiftModifier:
                    return super().eventFilter(obj, event)
                self._on_send_clicked()
                return True
        return super().eventFilter(obj, event)

    def _on_pin_toggled(self, checked):
        self.setWindowFlag(Qt.WindowStaysOnTopHint, checked)
        self.show()

    def showEvent(self, event):
        super().showEvent(event)
        theme = getattr(self, '_current_theme', 'dark')
        set_dark_title_bar(self, theme == 'dark')

    def set_app_theme(self, theme):
        self._current_theme = theme
        dark = theme == 'dark'
        app = QApp.instance()
        if app is not None:
            app.setProperty('_dark_theme', dark)
            app.setStyleSheet(DARK_STYLESHEET if dark else LIGHT_STYLESHEET)
            _filter = app.property('_dark_title_bar_filter')
            if _filter:
                _filter.set_dark(dark)
        set_dark_title_bar(self, dark)
        if app is not None:
            for w in app.topLevelWidgets():
                if w is not self:
                    set_dark_title_bar(w, dark)
        self.waveform_widget.set_color_theme(theme)
        # Connect i18n signal (only once)
        _sig = i18n_language_changed()
        if _sig and not hasattr(self, '_i18n_connected'):
            _sig.connect(self._refresh_on_language_changed)
            self._i18n_connected = True
        if hasattr(self, '_theme_group'):
            self._theme_dark_action.setChecked(theme == 'dark')
            self._theme_light_action.setChecked(theme == 'light')

    
    def _on_language_menu_changed(self, action):
        lang = action.data() or "zh"
        i18n_set_language(lang)

    def _on_lang_toggle_clicked(self):
        current = i18n_get_language()
        new_lang = "en" if current == "zh" else "zh"
        i18n_set_language(new_lang)

    def _refresh_on_language_changed(self, lang):
        """语言变更时刷新所有UI文本"""
        # Toolbar actions
        self.connect_action.setText(i18n("menu.connect"))
        self.connect_action.setToolTip(i18n("tooltip.quick_connect"))
        self.config_action.setText(i18n("menu.config"))
        self.config_action.setToolTip(i18n("tooltip.config_params"))
        self.disconnect_action.setText(i18n("menu.disconnect"))
        self.disconnect_action.setToolTip(i18n("tooltip.disconnect"))
        self.clear_action.setText(i18n("menu.clear"))
        self.clear_action.setToolTip(i18n("tooltip.clear_receive"))
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
        # Language toggle button
        self._lang_toggle_btn.setText("EN" if lang == "zh" else "中")
        self._lang_toggle_btn.setToolTip(i18n("tooltip.switch_language"))
        # Status bar
        if hasattr(self, '_current_status_id'):
            self.set_status(self._current_status_id, getattr(self, '_current_status_detail', ''))
        # Group boxes
        if hasattr(self, '_receive_group'):
            self._receive_group.setTitle(i18n("group.receive"))
        if hasattr(self, '_send_group'):
            self._send_group.setTitle(i18n("group.send"))
        # Send area
        if hasattr(self, '_mode_label'):
            self._mode_label.setText(i18n("label.mode"))
        self.send_mode_combo.setItemText(0, i18n("combo.send_string"))
        self.send_mode_combo.setItemText(1, i18n("combo.send_hex"))
        if hasattr(self, 'add_newline_checkbox'):
            self.add_newline_checkbox.setText(i18n("btn.add_newline"))
        self.send_input.setPlaceholderText(i18n("placeholder.send_input"))
        # Send/Reset buttons
        if hasattr(self, 'send_btn'):
            self.send_btn.setText(i18n("btn.send"))
            self.send_btn.setToolTip(i18n("tooltip.send_data"))
        if hasattr(self, 'reset_btn'):
            self.reset_btn.setText(i18n("btn.reset"))
            self.reset_btn.setToolTip(i18n("tooltip.reset_counters"))
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
        # Tool menu actions
        if hasattr(self, '_tool_menu'):
            self._tool_menu.setTitle(i18n("menu.tool"))
            for act in self._tool_menu.actions():
                d = act.data()
                if d == "font": act.setText(i18n("menu.font")); act.setToolTip(i18n("tooltip.set_font"))
                elif d == "ansi_color": act.setText(i18n("group.ansi_color")); act.setToolTip(i18n("tooltip.ansi_color"))
                elif d == "keyword_enable": act.setText(i18n("btn.enable")); act.setToolTip(i18n("tooltip.keyword_enable"))
                elif d == "keyword_config": act.setText(i18n("group.keyword_rule_config")); act.setToolTip(i18n("tooltip.keyword_config"))
        # Help menu actions
        if hasattr(self, '_help_menu'):
            self._help_menu.setTitle(i18n("menu.help"))
            for act in self._help_menu.actions():
                d = act.data()
                if d == "feedback": act.setText(i18n("group.feedback")); act.setToolTip(i18n("tooltip.bug_feedback"))
                elif d == "usage": act.setText(i18n("dialog.usage_doc")); act.setToolTip(i18n("tooltip.usage_doc"))
                elif d == "changelog": act.setText(i18n("dialog.changelog")); act.setToolTip(i18n("tooltip.changelog"))
                elif d == "upgrade": act.setText(i18n("dialog.upgrade_guide")); act.setToolTip(i18n("tooltip.upgrade_guide"))
                elif d == "rtt_intro": act.setText(i18n("group.rtt_intro")); act.setToolTip(i18n("tooltip.rtt_intro"))
                elif d == "rtt_source": act.setText(i18n("group.rtt_source")); act.setToolTip(i18n("tooltip.rtt_source"))
                elif d == "rtt_porting": act.setText(i18n("group.rtt_porting")); act.setToolTip(i18n("tooltip.rtt_porting"))
                elif d == "dep_manage": act.setText(i18n("group.dep_manage")); act.setToolTip(i18n("tooltip.dep_manage"))
                elif d == "about": act.setText(i18n("group.about")); act.setToolTip(i18n("tooltip.about"))
        # Log menu actions
        if hasattr(self, '_log_menu'):
            self._log_menu.setTitle(i18n("menu.log"))
            for act in self._log_menu.actions():
                d = act.data()
                if d == "system_log": act.setText(i18n("group.system_log")); act.setToolTip(i18n("tooltip.system_log"))
                elif d == "data_log": act.setText(i18n("group.data_log")); act.setToolTip(i18n("tooltip.data_log"))
                elif d == "log_manage": act.setText(i18n("group.log_manage"))
        # Window title
        self.setWindowTitle(f'{i18n("app.title")} v{__version__}')

    def _on_tools_theme_changed(self, action):
        theme = action.data() or 'dark'
        self.set_app_theme(theme)
        self.waveform_widget.theme_changed.emit(theme)

    def _on_quick_connect_clicked(self):
        """快速连接按钮点击 - 使用上次配置直接连接"""
        from datetime import datetime
        if self.log_service:
            self.log_service.debug(f"[性能] 点击连接按钮: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
        self.quick_connect_requested.emit()
    
    def _on_config_clicked(self):
        """配置按钮点击 - 打开配置对话框"""
        from datetime import datetime
        if self.log_service:
            self.log_service.debug(f"[性能] 点击配置按钮: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
        
        # 显示连接对话框,传入上次的配置
        dialog = ConnectionDialog(
            self,
            last_rtt_address=self.last_config.get('rtt_address', ''),
            last_device=self.last_config.get('device', 'Cortex-M4'),
            rtt_mode=self.last_config.get('rtt_mode', 'auto'),
            rtt_range_start=self.last_config.get('rtt_range_start', ''),
            rtt_range_size=self.last_config.get('rtt_range_size', ''),
            map_file_path=self.last_config.get('map_file_path', ''),
            log_service=self.log_service,
            device_info_service=self.device_info_service,
            debugger_manager=getattr(self, '_debugger_manager', None),
            connect_mode=self.last_config.get('connect_mode', 'under_reset'),
            pyocd_target=self.last_config.get('pyocd_target', ''),
            probe_name=self.last_config.get('probe_name', ''),
            probe_backend=self.last_config.get('probe_backend', ''),
            probe_serial=self.last_config.get('probe_serial', ''),
            interface=self.last_config.get('interface', 'SWD'),
            speed=self.last_config.get('speed', 4000)
        )
        
        # 恢复固件路径到配置对话框（优先从config_service读取，确保持久化恢复）
        try:
            from ..utils.config_service import ConfigService
            from ..runtime.path_config import RUNTIME_CONFIG_JSON
            cs = ConfigService(RUNTIME_CONFIG_JSON)
            cs.load()
            firmware_paths = cs.get('firmware_paths', [])
            active_firmware_index = cs.get('active_firmware_index', -1)
        except Exception:
            firmware_paths = self.last_config.get('firmware_paths', [])
            active_firmware_index = self.last_config.get('active_firmware_index', -1)
        if firmware_paths:
            dialog.firmware_path_panel.set_firmware_paths(firmware_paths, active_firmware_index)
        

        if self.log_service:
            self.log_service.debug(f"[性能] 创建对话框完成: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
        
        if dialog.exec_() == ConnectionDialog.Accepted:
            # 获取配置
            config = dialog.get_config()
            # 保存配置
            self.last_config = config
            self.config_changed.emit(config)

    
    def _on_disconnect_clicked(self):
        """断开按钮点击"""
        self.disconnect_requested.emit()
    
    def _on_mode_menu_clicked(self, action):
        """模式菜单点击"""
        new_mode = action.data()
        if new_mode is None:
            return
        self._mode_button.setText(action.text())
        self._apply_mode(new_mode)

    def _on_flash_clicked(self):
        """烧录按钮点击"""
        self.flash_requested.emit()

    def set_flash_button_enabled(self, enabled: bool):
        """设置烧录按钮启用状态"""
        self.flash_action.setEnabled(enabled)

    def _on_mode_changed(self, index):
        """显示模式切换（保留兼容，实际由 _on_mode_menu_clicked 代替）"""
        modes = ['log', 'oscilloscope', 'mixed']
        if not (0 <= index < len(modes)):
            return
        new_mode = modes[index]
        self._mode_button.setText([i18n("mode.log"), i18n("mode.oscilloscope"), i18n("mode.mixed")][index])
        self._apply_mode(new_mode)

    def _apply_mode(self, new_mode):
        index = ['log', 'oscilloscope', 'mixed'].index(new_mode)
        
        if new_mode == 'mixed' and self._current_mode != 'mixed':
            self._receive_group.setParent(None)
            self.waveform_widget.setParent(None)
            self._mixed_splitter.addWidget(self._receive_group)
            self._mixed_splitter.addWidget(self.waveform_widget)
            self._mixed_splitter.setSizes([300, 300])
            if hasattr(self, 'channel_panel'):
                self.channel_panel.hide()
        elif new_mode == 'log' and self._current_mode == 'mixed':
            self._receive_group.setParent(None)
            self.waveform_widget.setParent(None)
            log_layout = self._log_page.layout()
            log_layout.addWidget(self._receive_group)
            osc_layout = self._oscilloscope_page.layout()
            self._rebuild_osc_page()
            if hasattr(self, 'channel_panel'):
                self.channel_panel.hide()
        elif new_mode == 'oscilloscope' and self._current_mode == 'mixed':
            self._receive_group.setParent(None)
            self.waveform_widget.setParent(None)
            log_layout = self._log_page.layout()
            log_layout.addWidget(self._receive_group)
            self._rebuild_osc_page()
            if hasattr(self, 'channel_panel'):
                self.channel_panel.show()
        elif new_mode == 'oscilloscope' and self._current_mode != 'oscilloscope':
            self._rebuild_osc_page()
            if hasattr(self, 'channel_panel'):
                self.channel_panel.show()
        elif new_mode == 'log' and self._current_mode == 'oscilloscope':
            if hasattr(self, 'channel_panel'):
                self.channel_panel.hide()
        
        self._display_stack.setCurrentIndex(index)
        self._current_mode = new_mode
        self.mode_changed.emit(new_mode)
        if hasattr(self, 'config_service') and self.config_service:
            self.config_service.set('display_mode', new_mode)
            self.config_service.save()

    def _rebuild_osc_page(self):
        osc_layout = self._oscilloscope_page.layout()
        while osc_layout.count():
            item = osc_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
        self._osc_splitter = QSplitter(Qt.Horizontal)
        self._osc_splitter.addWidget(self.waveform_widget)
        self._osc_splitter.addWidget(self.channel_panel)
        self._osc_splitter.setStretchFactor(0, 3)
        self._osc_splitter.setStretchFactor(1, 0)
        self._osc_splitter.setSizes([700, ChannelPanel.COLLAPSED_WIDTH])
        osc_layout.addWidget(self._osc_splitter)

    def _on_clear_clicked(self):
        """清空按钮点击"""
        self.receive_text.clear()
        self.clear_requested.emit()
    
    def _on_send_clicked(self):
        """发送按钮点击"""
        text = self.send_input.toPlainText()  # 使用toPlainText获取多行文本
        if not text:
            return
        
        is_hex = self.send_mode_combo.currentData() == "hex"
        add_newline = self.add_newline_checkbox.isChecked()
        
        # HEX模式验证
        if is_hex:
            # 移除空格
            hex_str = text.replace(" ", "")
            
            # 验证是否为空
            if not hex_str:
                QMessageBox.warning(self, i18n("error.hex_format"), i18n("error.hex_empty"))
                return
            
            # 验证是否为偶数长度
            if len(hex_str) % 2 != 0:
                QMessageBox.warning(self, i18n("error.hex_format"), 
                    i18n("error.hex_odd_length").format(len(hex_str)))
                return
            
            # 验证是否都是有效的十六进制字符
            valid_chars = set('0123456789ABCDEFabcdef')
            invalid_chars = set(hex_str) - valid_chars
            if invalid_chars:
                QMessageBox.warning(self, i18n("error.hex_format"), 
                    i18n("error.hex_invalid_char").format(invalid_chars))
                return
        
        self.send_requested.emit(text, is_hex, add_newline)
        
        # 保存到数据日志文件
        if self.data_log_handle:
            try:
                from datetime import datetime
                timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                mode = "HEX" if is_hex else "TXT"
                self.data_log_handle.write(f"[{timestamp}] [TX][{mode}] {text}\n")
                self.data_log_handle.flush()
            except Exception:
                pass
    
    def _on_font_clicked(self):
        """字体按钮点击"""
        from PyQt5.QtWidgets import QFontDialog
        dialog = QFontDialog(self.receive_text.font(), self)
        dialog.setWindowTitle(i18n("dialog.select_font"))
        set_dark_title_bar(dialog, getattr(self, '_current_theme', 'dark') == 'dark')
        if dialog.exec_():
            font = dialog.selectedFont()
            self.receive_text.setFont(font)
            self.font_changed.emit(font)
    
    def _on_keyword_highlight(self):
        """关键字高亮配置对话框"""
        from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                                     QTableWidgetItem, QPushButton, QHeaderView, QColorDialog)
        from PyQt5.QtGui import QColor
        
        dialog = QDialog(self)
        dialog.setWindowTitle(i18n("dialog.keyword_config"))
        dialog.resize(500, 350)
        set_dark_title_bar(dialog, getattr(self, '_current_theme', 'dark') == 'dark')
        layout = QVBoxLayout(dialog)
        
        table = QTableWidget(0, 2)
        table.setHorizontalHeaderLabels([i18n("header.keyword"), i18n("header.color")])
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        
        default_colors = {
            "ERROR": "#ff0000",
            "WARN": "#ffff00",
            "WARNING": "#ffff00",
            "FAIL": "#ff0000",
            "OK": "#00ff00",
            "SUCCESS": "#00ff00",
        }
        
        rules = getattr(self, '_keyword_rules', None)
        if rules is None:
            rules = dict(default_colors)
        
        for keyword, color in rules.items():
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(keyword))
            color_item = QTableWidgetItem(color)
            color_item.setForeground(QColor(color))
            table.setItem(row, 1, color_item)
        
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton(i18n("btn.add"))
        def on_add():
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(""))
            table.setItem(row, 1, QTableWidgetItem("#ff0000"))
        add_btn.clicked.connect(on_add)
        btn_layout.addWidget(add_btn)
        
        del_btn = QPushButton(i18n("btn.delete"))
        del_btn.clicked.connect(lambda: table.removeRow(table.currentRow()) if table.currentRow() >= 0 else None)
        btn_layout.addWidget(del_btn)
        
        color_btn = QPushButton(i18n("btn.select_color"))
        def on_pick_color():
            row = table.currentRow()
            if row >= 0:
                color = QColorDialog.getColor(QColor("#ff0000"), dialog, i18n("btn.select_color"))
                if color.isValid():
                    table.item(row, 1).setText(color.name())
                    table.item(row, 1).setForeground(color)
        color_btn.clicked.connect(on_pick_color)
        btn_layout.addWidget(color_btn)
        
        btn_layout.addStretch()
        layout.addWidget(table)
        layout.addLayout(btn_layout)
        
        ok_btn = QPushButton(i18n("btn.ok"))
        ok_layout = QHBoxLayout()
        ok_layout.addStretch()
        ok_layout.addWidget(ok_btn)
        ok_layout.addStretch()
        layout.addLayout(ok_layout)
        
        ok_btn.clicked.connect(dialog.accept)
        
        if dialog.exec_() == QDialog.Accepted:
            self._keyword_rules = {}
            for row in range(table.rowCount()):
                kw_item = table.item(row, 0)
                color_item = table.item(row, 1)
                if kw_item and color_item and kw_item.text().strip():
                    self._keyword_rules[kw_item.text().strip()] = color_item.text()
            # 保存到配置
            if self.log_service:
                try:
                    from rtt_tool.utils.config_service import ConfigService
                    cs = ConfigService()
                    cs.set('keyword_rules', self._keyword_rules)
                    cs.save()
                except Exception:
                    pass
    
    def _parse_ansi_and_insert(self, text):
        """
        解析ANSI转义码并插入带颜色的文本到接收区
        
        Args:
            text: 可能包含ANSI转义码的文本
        """
        import re
        from PyQt5.QtGui import QTextCharFormat, QColor
        
        ANSI_COLOR_MAP = {
            30: "#555555", 31: "#ff0000", 32: "#00ff00", 33: "#ffff00",
            34: "#0000ff", 35: "#ff00ff", 36: "#00ffff", 37: "#ffffff",
            90: "#888888", 91: "#ff6666", 92: "#66ff66", 93: "#ffff66",
            94: "#6666ff", 95: "#ff66ff", 96: "#66ffff", 97: "#ffffff",
        }
        
        cursor = self.receive_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        default_format = cursor.charFormat()
        current_format = QTextCharFormat(default_format)
        
        pattern = re.compile(r'\x1B\[([\d;]*)m')
        last_end = 0
        
        for match in pattern.finditer(text):
            if match.start() > last_end:
                plain = text[last_end:match.start()]
                cursor.setCharFormat(current_format)
                cursor.insertText(plain)
            
            codes = match.group(1)
            if not codes:
                current_format = QTextCharFormat(default_format)
            else:
                for code in codes.split(';'):
                    code = int(code) if code.isdigit() else 0
                    if code == 0:
                        current_format = QTextCharFormat(default_format)
                    elif code in ANSI_COLOR_MAP:
                        current_format.setForeground(QColor(ANSI_COLOR_MAP[code]))
                    elif code == 1:
                        f = QTextCharFormat(current_format)
                        current_format = f
            
            last_end = match.end()
        
        if last_end < len(text):
            remaining = text[last_end:]
            cursor.setCharFormat(current_format)
            cursor.insertText(remaining)
    
    def _apply_keyword_highlight(self, text, cursor):
        """
        对非ANSI着色的文本应用关键字高亮
        
        Args:
            text: 纯文本
            cursor: QTextCursor
        """
        from PyQt5.QtGui import QTextCharFormat, QColor
        
        rules = getattr(self, '_keyword_rules', {})
        if not rules:
            return
        
        for keyword, color in rules.items():
            pos = 0
            while True:
                idx = text.find(keyword, pos)
                if idx == -1:
                    break
                
                cursor.setPosition(cursor.document().characterCount() - len(text) + idx)
                cursor.setPosition(cursor.position() + len(keyword), QTextCursor.KeepAnchor)
                
                fmt = QTextCharFormat(cursor.charFormat())
                fmt.setForeground(QColor(color))
                cursor.mergeCharFormat(fmt)
                
                pos = idx + len(keyword)
    
    def _direct_insert_text(self, text):
        scrollbar = self.receive_text.verticalScrollBar()
        at_bottom = scrollbar.value() >= scrollbar.maximum() - 2

        ansi_enabled = hasattr(self, 'ansi_color_action') and self.ansi_color_action.isChecked()
        keyword_enabled = hasattr(self, 'keyword_highlight_action') and self.keyword_highlight_action.isChecked()
        keyword_rules = getattr(self, '_keyword_rules', {}) if keyword_enabled else {}
        has_ansi = '\x1B' in text if text else False
        
        if ansi_enabled and has_ansi:
            self._parse_ansi_and_insert(text)
        elif keyword_rules:
            cursor = QTextCursor(self.receive_text.document())
            cursor.movePosition(QTextCursor.End)
            cursor.insertText(text)
            
            for keyword, color in keyword_rules.items():
                if keyword in text:
                    from PyQt5.QtGui import QTextCharFormat, QColor
                    fmt = QTextCharFormat()
                    fmt.setForeground(QColor(color))
                    doc = self.receive_text.document()
                    search_cursor = QTextCursor(doc)
                    search_cursor.movePosition(QTextCursor.End)
                    end_pos = search_cursor.position()
                    search_pos = max(0, end_pos - len(text) - len(keyword))
                    
                    search_cursor.setPosition(search_pos)
                    while True:
                        found = doc.find(keyword, search_cursor)
                        if found.isNull() or found.selectionStart() < search_pos or found.selectionEnd() > end_pos:
                            break
                        found.mergeCharFormat(fmt)
                        search_cursor = QTextCursor(doc)
                        search_cursor.setPosition(found.selectionEnd())
        else:
            cursor = QTextCursor(self.receive_text.document())
            cursor.movePosition(QTextCursor.End)
            cursor.insertText(text)
        
        doc = self.receive_text.document()
        if doc.blockCount() > self._max_display_lines:
            cursor = QTextCursor(doc)
            cursor.movePosition(QTextCursor.Start)
            lines_to_remove = doc.blockCount() - self._max_display_lines
            for _ in range(lines_to_remove):
                cursor.movePosition(QTextCursor.NextBlock, QTextCursor.KeepAnchor)
            cursor.removeSelectedText()

        if at_bottom:
            self.receive_text.verticalScrollBar().setValue(self.receive_text.verticalScrollBar().maximum())

    def _flush_pending_log_text(self):
        if not self._pending_text:
            return
        accumulated = self._pending_text
        self._pending_text = ''
        signal_count = self._pending_signal_count
        self._pending_signal_count = 0
        self._direct_insert_text(accumulated)
        if getattr(self, '_diagnostic_log_enabled', False):
            import logging
            logging.getLogger(__name__).debug(f"UI flush: {signal_count} signals merged, {len(accumulated)}B")

    def append_receive_data(self, text):
        """
        追加接收数据（支持节流模式）
        
        Args:
            text: 要追加的文本
        """
        has_ansi = '\x1B' in text if text else False
        if self.data_log_handle:
            try:
                from datetime import datetime
                import re
                timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                clean_text = re.sub(r'\x1B\[[\d;]*m', '', text) if has_ansi else text
                self.data_log_handle.write(f"[{timestamp}] [RX] {clean_text}\n")
                self.data_log_handle.flush()
            except Exception:
                pass

        if getattr(self, '_log_throttle_enabled', False):
            self._pending_text += text
            self._pending_signal_count += 1
            if len(self._pending_text.encode('utf-8', errors='replace')) > self._log_throttle_max_buffer_bytes:
                self._flush_pending_log_text()
            if not self._log_throttle_timer.isActive():
                self._log_throttle_timer.start()
        else:
            self._direct_insert_text(text)
    
    def set_connected(self, connected):
        """
        设置连接状态
        
        Args:
            connected: 是否已连接
        """
        self.connect_action.setEnabled(not connected)
        self.disconnect_action.setEnabled(connected)
        
        if connected:
            self.set_status(STATUS_CONNECTED)
            self._update_probe_info()
        else:
            self.set_status(STATUS_DISCONNECTED)
    
    def set_status(self, status_id, detail=""):
        self._current_status_id = status_id
        self._current_status_detail = detail
        text = i18n(_STATUS_KEY_MAP.get(status_id, status_id))
        if detail:
            text = f"{text} - {detail}"
        self.status_label.setText(text)
        bg = _STATUS_COLOR_MAP.get(status_id, "")
        if bg:
            self.status_label.setStyleSheet(
                f"background-color: {bg}; color: #ffffff; padding: 0 6px; font-weight: bold; border-radius: 2px;"
            )
        else:
            self.status_label.setStyleSheet("")
    
    def update_receive_group_title(self, ch_name: str = "", buf_size: int = 0):
        """更新接收区GroupBox标题: 显示通道名+缓冲区大小"""
        parts = [i18n("label.receive_area_prefix")]
        if ch_name:
            parts.append(f' "{ch_name}"')
        if buf_size > 0:
            parts.append(f" {buf_size}B")
        parts.append(")")
        self._receive_group.setTitle("".join(parts))
    
    def update_send_group_title(self, ch_name: str = "", buf_size: int = 0):
        """更新发送区GroupBox标题: 显示下行通道名+缓冲区大小"""
        parts = [i18n("label.send_area_prefix")]
        if ch_name:
            parts.append(f' "{ch_name}"')
        if buf_size > 0:
            parts.append(f" {buf_size}B")
        else:
            parts.append(i18n("label.send_area_no_down"))
        parts.append(")")
        self._send_group.setTitle("".join(parts))
    
    def update_rx_bytes(self, count):
        """
        更新接收字节数
        
        Args:
            count: 接收字节数
        """
        self.rx_label.setText(f"RX: {count}")
    
    def update_tx_bytes(self, count):
        """
        更新发送字节数
        
        Args:
            count: 发送字节数
        """
        self.tx_label.setText(f"TX: {count}")

    def create_channel_log(self, channel: int, ch_name: str = '', ch_format: str = '', buf_size: int = 0):
        if channel in self._channel_log_handles:
            return self._channel_log_handles[channel]
        try:
            from ..runtime.path_config import RUNTIME_LOG_DIR
            import os
            from datetime import datetime
            os.makedirs(RUNTIME_LOG_DIR, exist_ok=True)
            path = os.path.join(RUNTIME_LOG_DIR, f"rtt_data_CH{channel}_{self._log_timestamp}.log")
            handle = open(path, 'a', encoding='utf-8')
            handle.write(f"RTT Assistant CH{channel} 数据日志\n")
            handle.write(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            if ch_name:
                handle.write(f"通道名: {ch_name}\n")
            if ch_format:
                handle.write(f"数据类型: {ch_format}\n")
            if buf_size > 0:
                handle.write(f"缓冲区大小: {buf_size} 字节\n")
            handle.write(f"{'='*60}\n\n")
            handle.flush()
            self._channel_log_handles[channel] = handle
            return handle
        except Exception:
            return None

    def restore_display_mode(self):
        if hasattr(self, 'config_service') and self.config_service:
            saved = self.config_service.get('display_mode', 'log')
            if saved in ('log', 'oscilloscope', 'mixed') and saved != self._current_mode:
                mode_names = {'log': i18n('mode.log'), 'oscilloscope': i18n('mode.oscilloscope'), 'mixed': i18n('mode.mixed')}
                self._mode_button.setText(mode_names.get(saved, i18n("menu.mode")))
                self._apply_mode(saved)
    
    def _on_log_clicked(self):
        """日志按钮点击"""
        if self.log_window is None:
            self.log_window = LogWindow()
        
        if self.log_window.isVisible():
            self.log_window.hide()
        else:
            self.log_window.show()
    
    def get_log_window(self):
        """
        获取日志窗口
        
        Returns:
            LogWindow: 日志窗口对象
        """
        return self.log_window
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        if hasattr(self, '_save_geometry_callback'):
            try:
                self._save_geometry_callback()
            except Exception:
                pass
        if hasattr(self, '_log_throttle_timer'):
            self._log_throttle_timer.stop()
        if hasattr(self, '_flush_pending_log_text'):
            self._flush_pending_log_text()
        # 关闭数据日志文件
        if self.data_log_handle:
            try:
                self.data_log_handle.close()
            except Exception:
                pass
        for ch, handle in getattr(self, '_channel_log_handles', {}).items():
            try:
                handle.close()
            except Exception:
                pass
        event.accept()
    
    def _on_help_contact(self):
        from PyQt5.QtWidgets import QDialog, QLabel, QVBoxLayout, QPushButton, QHBoxLayout
        dlg = QDialog(self)
        dlg.setWindowTitle(i18n("dialog.bug_feedback"))
        dlg.setMinimumWidth(320)
        dlg.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel(i18n("label.bug_feedback_hint")))
        email_label = QLabel('<b>292812832@qq.com</b>')
        email_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(email_label)
        layout.addWidget(QLabel(i18n("label.will_fix_soon")))
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = QPushButton(i18n("btn.ok"))
        ok_btn.clicked.connect(dlg.accept)
        btn_layout.addWidget(ok_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        dlg.exec_()

    def _get_doc_path(self, zh_name: str, en_name: str) -> str:
        lang = i18n_get_language()
        doc_name = en_name if lang == "en" else zh_name
        return get_resource_path(f"doc/{doc_name}")

    def _on_usage_doc(self):
        import os
        doc_file = self._get_doc_path("使用说明.html", "Usage Guide.html")
        if doc_file and os.path.exists(doc_file):
            os.startfile(doc_file)
        else:
            QMessageBox.information(self, i18n("dialog.usage_doc"), i18n("error.doc_not_found"))

    def _on_changelog(self):
        import os
        doc_file = self._get_doc_path("更新说明.html", "Changelog.html")
        if doc_file and os.path.exists(doc_file):
            os.startfile(doc_file)
        else:
            QMessageBox.information(self, i18n("dialog.changelog"), i18n("error.doc_not_found"))

    def _on_upgrade_guide(self):
        import os
        doc_file = self._get_doc_path("升级指南.html", "Upgrade Guide.html")
        if doc_file and os.path.exists(doc_file):
            os.startfile(doc_file)
        else:
            QMessageBox.information(self, i18n("dialog.upgrade_guide"), i18n("error.doc_not_found"))
    
    def _on_open_data_log_folder(self):
        """打开收发数据日志文件夹"""
        import os
        import sys
        
        folder = get_exe_dir()
        
        # 打开文件夹
        os.startfile(folder)
    
    def _on_log_manage_clicked(self):
        """打开诊断日志管理窗口"""
        if self._log_manage_dialog is None:
            from ..service.diag_log_registry import DiagLogRegistry
            from .log_manage_dialog import LogManageDialog
            config_service = getattr(self, 'config_service', None)
            registry = DiagLogRegistry(config_service=config_service)
            self._log_manage_dialog = LogManageDialog(registry, parent=self)
        self._log_manage_dialog.show()
        self._log_manage_dialog.raise_()
    
    def _update_probe_info(self):
        """更新状态栏探针信息（支持J-Link和PyOCD）"""
        try:
            backend_type = self.last_config.get('probe_backend', 'jlink') if hasattr(self, 'last_config') else 'jlink'
        except Exception:
            backend_type = 'jlink'

        if backend_type == 'jlink':
            try:
                if not hasattr(self, '_jlink_ref') or self._jlink_ref is None:
                    self.probe_info_label.setText("")
                    return
                j = self._jlink_ref
                hw_ver = j.hardware_version
                fw_ver = j.firmware_version
                sn = j.serial_number
                self.probe_info_label.setText(f"J-Link SN:{sn} | HW:{hw_ver} | FW:{fw_ver}")
            except Exception:
                self.probe_info_label.setText("")
        else:
            try:
                probe_name = self.last_config.get('probe_name', '') if hasattr(self, 'last_config') else ''
                probe_serial = self.last_config.get('probe_serial', '') if hasattr(self, 'last_config') else ''
                target = self.last_config.get('pyocd_target', '') if hasattr(self, 'last_config') else ''
                info = f"{probe_name}" if probe_name else backend_type.upper()
                if probe_serial:
                    info += f" SN:{probe_serial}"
                if target:
                    info += f" | Target:{target}"
                self.probe_info_label.setText(info)
            except Exception:
                self.probe_info_label.setText(backend_type.upper())
    
    def _get_jlink_dll_info(self):
        """读取J-Link DLL版本信息(仅软件信息，无需探针)"""
        import os
        try:
            dll_path = get_external_file("JLink_x64.dll")
            if dll_path is None:
                dll_path = get_external_file("JLinkARM.dll")
            if dll_path is None:
                return None
            
            import pylink
            from pylink import library
            jlink_lib = library.Library(dllpath=dll_path)
            j = pylink.JLink(lib=jlink_lib)
            
            dll_ver = j.version
            num_devices = j.num_supported_devices()
            
            return (f"<p style='font-size:10px;'>"
                    f"<b>J-Link DLL:</b> {dll_ver} | "
                    f"<b>支持设备:</b> {num_devices}个"
                    f"</p>")
        except Exception as e:
            return f"<p style='font-size:10px; color:#cc0000;'>J-Link DLL读取失败: {e}</p>"
    
    def _get_pyocd_info(self):
        """读取PyOCD版本、目标数和Pack数"""
        import os
        try:
            import pyocd
            pyocd_ver = pyocd.__version__
        except ImportError:
            return "<p style='font-size:10px;'>PyOCD: 未安装</p>"
        except Exception:
            pyocd_ver = '?'
        target_count = 0
        pack_count = 0
        try:
            from ..runtime.path_config import RUNTIME_PYOCD_TARGETS_TXT, RUNTIME_PACKS_DIR
            targets_file = RUNTIME_PYOCD_TARGETS_TXT
            if os.path.exists(targets_file):
                with open(targets_file, 'r', encoding='utf-8') as f:
                    target_count = len([l for l in f if l.strip()])
            packs_dir = RUNTIME_PACKS_DIR
            if os.path.isdir(packs_dir):
                pack_count = len([f for f in os.listdir(packs_dir) if f.endswith('.pack')])
        except Exception:
            pass
        return (f"<p style='font-size:10px;'>"
                f"<b>PyOCD:</b> v{pyocd_ver} | "
                f"<b>支持目标:</b> {target_count}个 | "
                f"<b>Pack文件:</b> {pack_count}个"
                f"</p>")
    
    def _on_dependency_manage(self):
        try:
            from rtt_tool.runtime.dependency_upgrade import show_dependency_upgrade_dialog
            dialog = show_dependency_upgrade_dialog(parent=self)
            dialog.exec_()
        except Exception as e:
            import traceback
            traceback.print_exc()
            try:
                if hasattr(self, '_log_service') and self._log_service:
                    self._log_service.error(f'打开依赖管理失败: {e}')
            except Exception:
                pass
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, i18n("dialog.error_title"), f'{i18n("error.open_dep_manage_failed")}: {e}')

    def _on_about(self):
        """显示关于对话框"""
        from PyQt5.QtWidgets import QDialog, QLabel, QVBoxLayout, QPushButton
        from PyQt5.QtGui import QPixmap
        from PyQt5.QtCore import Qt
        
        # 读取J-Link DLL版本信息
        jlink_info = self._get_jlink_dll_info()
        # 读取PyOCD信息
        pyocd_info = self._get_pyocd_info()
        
        # 创建自定义对话框
        dialog = QDialog(self)
        dialog.setWindowTitle(i18n("dialog.about"))
        dialog.setFixedSize(450, 500)
        set_dark_title_bar(dialog, getattr(self, '_current_theme', 'dark') == 'dark')
        
        layout = QVBoxLayout(dialog)
        
        # 标题
        title = QLabel("<h2>RTT Assistant</h2>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 版本信息
        version = QLabel(f"<p>{i18n('label.version_info').format(__version__)} v{__version__}</p><p>{i18n('label.rtt_assistant_desc')}</p><p>{i18n('label.based_on_segger_rtt')}</p>")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)
        
        # J-Link DLL信息
        if jlink_info:
            jlink_label = QLabel(jlink_info)
            jlink_label.setAlignment(Qt.AlignCenter)
            jlink_label.setStyleSheet("color: #666666;")
            layout.addWidget(jlink_label)
        
        # PyOCD信息
        if pyocd_info:
            pyocd_label = QLabel(pyocd_info)
            pyocd_label.setAlignment(Qt.AlignCenter)
            pyocd_label.setStyleSheet("color: #666666;")
            layout.addWidget(pyocd_label)
        
        # 分隔线
        layout.addWidget(QLabel("<hr>"))
        
        # 作者信息
        author = QLabel(f"<p><b>{i18n('label.author')}</b> {i18n('label.author_name')}</p>")
        author.setAlignment(Qt.AlignCenter)
        layout.addWidget(author)
        
        # 公众号(可点击)
        wechat_label = QLabel('<p><a href="#" style="text-decoration:none; color:#0000ff;"><b>公众号:</b> 嵌入式科普</a></p>')
        wechat_label.setAlignment(Qt.AlignCenter)
        wechat_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        wechat_label.linkActivated.connect(lambda: self._show_qrcode(dialog))
        layout.addWidget(wechat_label)
        
        # B站(可点击)
        bilibili_label = QLabel('<p><a href="https://space.bilibili.com/417060922" style="text-decoration:none; color:#0000ff;"><b>B站:</b> 嵌入式科普</a></p>')
        bilibili_label.setAlignment(Qt.AlignCenter)
        bilibili_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        bilibili_label.setOpenExternalLinks(True)
        layout.addWidget(bilibili_label)
        
        # GitHub(可点击)
        github_label = QLabel('<p><a href="https://github.com/cl234583745/RTT-Assistant" style="text-decoration:none; color:#0000ff;"><b>GitHub:</b> cl234583745</a></p>')
        github_label.setAlignment(Qt.AlignCenter)
        github_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        github_label.setOpenExternalLinks(True)
        layout.addWidget(github_label)
        
        # Gitee(可点击)
        gitee_label = QLabel('<p><a href="https://gitee.com/292812832/RTT-Assistant" style="text-decoration:none; color:#0000ff;"><b>Gitee:</b> 292812832</a></p>')
        gitee_label.setAlignment(Qt.AlignCenter)
        gitee_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        gitee_label.setOpenExternalLinks(True)
        layout.addWidget(gitee_label)
        
        # 分隔线
        layout.addWidget(QLabel("<hr>"))

        # 检查更新按钮
        check_update_btn = QPushButton(i18n("btn.check_update"))
        check_update_btn.clicked.connect(lambda: self._on_check_update(dialog))
        layout.addWidget(check_update_btn)

        # 版权信息
        copyright_label = QLabel("<p>© 2024 RTT Assistant. All rights reserved.</p>")
        copyright_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(copyright_label)
        
        # 确定按钮
        ok_btn = QPushButton(i18n("btn.ok"))
        ok_btn.clicked.connect(dialog.accept)
        layout.addWidget(ok_btn)
        
        dialog.exec_()

    def _on_check_update(self, parent):
        from .update_dialog import UpdateDialog
        dlg = UpdateDialog(parent)
        dlg.exec_()

    def _show_qrcode(self, parent):
        """显示公众号二维码"""
        import os
        import sys
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel
        from PyQt5.QtGui import QPixmap
        from PyQt5.QtCore import Qt
        
        # 创建对话框
        dialog = QDialog(parent)
        dialog.setWindowTitle(i18n("label.wechat_public"))
        dialog.setFixedSize(350, 400)
        
        layout = QVBoxLayout(dialog)
        
        # 标题
        title = QLabel(f"<h3>{i18n('label.scan_qrcode')}</h3>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 二维码图片
        qrcode_label = QLabel()
        
        # 查找二维码图片
        qrcode_path = get_resource_path("resources/duokajiangfllpll.png")
        
        if qrcode_path and os.path.exists(qrcode_path):
            pixmap = QPixmap(qrcode_path)
            if not pixmap.isNull():
                # 缩放图片
                scaled_pixmap = pixmap.scaled(280, 280, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                qrcode_label.setPixmap(scaled_pixmap)
            else:
                qrcode_label.setText(i18n("label.cannot_load_qrcode"))
        else:
            qrcode_label.setText(i18n("label.qrcode_not_found"))
        
        qrcode_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(qrcode_label)
        
        # 提示
        tip = QLabel(f"<p>{i18n('label.wechat')} <b>{i18n('label.wechat_name')}</b></p>")
        tip.setAlignment(Qt.AlignCenter)
        layout.addWidget(tip)
        
        dialog.exec_()
    
    def _on_rtt_intro(self):
        """打开SEGGER RTT介绍网页"""
        import webbrowser
        url = "https://kb.segger.com/RTT"
        try:
            webbrowser.open(url)
        except Exception as e:
            QMessageBox.warning(self, i18n("dialog.error_title"), f'{i18n("error.cannot_open_web")}: {e}')
    
    def _on_rtt_source(self):
        """打开SEGGER RTT源码"""
        import os
        from ..runtime.path_config import RUNTIME_RESOURCES_DIR

        zip_path = os.path.join(RUNTIME_RESOURCES_DIR, 'RTT.zip')
        if os.path.isfile(zip_path):
            QMessageBox.information(self, i18n("dialog.rtt_source"),
                i18n("error.rtt_source_location").format(zip_path))
            os.startfile(zip_path)
        else:
            QMessageBox.warning(self, i18n("dialog.rtt_source_not_found"),
                i18n("error.rtt_zip_not_found").format(zip_path))
    
    def _on_rtt_porting(self):
        import os
        guide_path = self._get_doc_path("SEGGER_RTT移植指南.html", "SEGGER_RTT Porting Guide.html")
        if guide_path and os.path.exists(guide_path):
            os.startfile(guide_path)
        else:
            self._show_porting_doc()
    
    def _show_porting_doc(self):
        """显示SEGGER RTT移植文档"""
        QMessageBox.information(self, i18n("dialog.rtt_porting_guide"),
            "<h3>" + i18n("porting.step1") + "</h3>"
            "<ol>"
            "<li><b>" + i18n("porting.step1") + "</b><br>"
            "" + i18n("porting.step1_desc") + "</li>"
            "<li><b>" + i18n("porting.step2") + "</b><br>"
            "" + i18n("porting.step2_desc") + "</li>"
            "<li><b>" + i18n("porting.step3") + "</b><br>"
            "" + i18n("porting.step3_desc") + "</li>"
            "<li><b>" + i18n("porting.step4") + "</b><br>"
            "" + i18n("porting.step4_desc") + "</li>"
            "<li><b>" + i18n("porting.step5") + "</b><br>"
            "" + i18n("porting.step5_desc") + "</li>"
            "</ol>"
            "<hr>"
            "<p><b>详细文档:</b> https://kb.segger.com/RTT</p>")
    
    def set_last_config(self, config):
        """
        设置上次的连接配置
        
        Args:
            config: 配置字典
        """
        self.last_config = config
    
    
    def _on_export_data(self):
        """导出收发数据"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            i18n("dialog.export_data"),
            "rtt_data.txt",
            f"{i18n('filter.text_file')} (*.txt);;{i18n('filter.all_file')} (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.receive_text.toPlainText())
            except Exception as e:
                pass
    

