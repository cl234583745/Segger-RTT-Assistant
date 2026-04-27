#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
主窗口UI
包含工具栏、接收区、发送区、状态栏
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QComboBox,
    QCheckBox, QLabel, QStatusBar, QToolBar, QAction,
    QSplitter, QGroupBox, QFileDialog, QMenu, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QTextCursor
from .connection_dialog import ConnectionDialog
from .log_window import LogWindow
from ..utils.resource_utils import get_resource_path, is_frozen


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
    
    def __init__(self):
        super().__init__()
        self.log_window = None  # 日志窗口
        self.last_config = {}  # 上次的连接配置
        
        # 收发数据日志文件
        from datetime import datetime
        import os
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.data_log_file = f"rtt_data_{timestamp}.log"
        self.data_log_handle = None
        
        # 打开数据日志文件
        try:
            self.data_log_handle = open(self.data_log_file, 'w', encoding='utf-8')
            self.data_log_handle.write(f"RTT Assistant 收发数据日志\n")
            self.data_log_handle.write(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            self.data_log_handle.write(f"{'='*60}\n\n")
            self.data_log_handle.flush()
        except Exception as e:
            print(f"无法创建数据日志文件: {e}")
        
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle('RTT Assistant v1.3.1')
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
        receive_group = self._create_receive_area()
        splitter.addWidget(receive_group)
        
        # 创建发送区
        send_group = self._create_send_area()
        splitter.addWidget(send_group)
        
        # 设置初始比例(接收区:发送区 = 3:1)
        splitter.setSizes([500, 200])
        
        main_layout.addWidget(splitter)
        
        # 创建状态栏
        self._create_status_bar()
    
    def _create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("工具栏")
        self.addToolBar(toolbar)
        
        # 禁用右键菜单
        toolbar.setContextMenuPolicy(Qt.PreventContextMenu)
        
        # 连接按钮 - 直接使用上次配置连接
        self.connect_action = QAction("连接", self)
        self.connect_action.setToolTip("使用上次配置连接")
        self.connect_action.triggered.connect(self._on_quick_connect_clicked)
        toolbar.addAction(self.connect_action)
        
        # 配置按钮 - 打开配置对话框
        config_action = QAction("配置", self)
        config_action.setToolTip("配置连接参数")
        config_action.triggered.connect(self._on_config_clicked)
        toolbar.addAction(config_action)
        
        # 断开按钮
        self.disconnect_action = QAction("断开", self)
        self.disconnect_action.setToolTip("断开连接")
        self.disconnect_action.triggered.connect(self.disconnect_requested.emit)
        self.disconnect_action.setEnabled(False)
        toolbar.addAction(self.disconnect_action)
        
        toolbar.addSeparator()
        
        # 清空按钮
        clear_action = QAction("清空", self)
        clear_action.setToolTip("清空接收区")
        clear_action.triggered.connect(self._on_clear_clicked)
        toolbar.addAction(clear_action)
        
        toolbar.addSeparator()
        
        # 时间戳开关
        self.timestamp_checkbox = QCheckBox("时间戳")
        self.timestamp_checkbox.setToolTip("显示时间戳")
        self.timestamp_checkbox.stateChanged.connect(
            lambda state: self.timestamp_toggled.emit(state == Qt.Checked)
        )
        toolbar.addWidget(self.timestamp_checkbox)
        
        # HEX显示开关
        self.hex_display_checkbox = QCheckBox("HEX显示")
        self.hex_display_checkbox.setToolTip("以HEX格式显示数据")
        self.hex_display_checkbox.stateChanged.connect(
            lambda state: self.hex_display_toggled.emit(state == Qt.Checked)
        )
        toolbar.addWidget(self.hex_display_checkbox)
        
        toolbar.addSeparator()
        
        # 字体设置
        font_action = QAction("字体", self)
        font_action.setToolTip("设置字体")
        font_action.triggered.connect(self._on_font_clicked)
        toolbar.addAction(font_action)
        
        # 窗口置顶
        self.topmost_checkbox = QCheckBox("置顶")
        self.topmost_checkbox.setToolTip("窗口置顶")
        self.topmost_checkbox.stateChanged.connect(
            lambda state: self.setWindowFlag(
                Qt.WindowStaysOnTopHint,
                state == Qt.Checked
            )
        )
        self.topmost_checkbox.stateChanged.connect(self.show)
        toolbar.addWidget(self.topmost_checkbox)
        
        toolbar.addSeparator()
        
        # 帮助菜单
        help_menu = QMenu("帮助", self)
        
        # 帮助文档
        help_doc_action = QAction("帮助文档", self)
        help_doc_action.setToolTip("打开帮助文档")
        help_doc_action.triggered.connect(self._on_help_document)
        help_menu.addAction(help_doc_action)
        
        # 升级日志
        changelog_action = QAction("升级日志", self)
        changelog_action.setToolTip("查看升级日志")
        changelog_action.triggered.connect(self._on_changelog)
        help_menu.addAction(changelog_action)
        
        help_menu.addSeparator()
        
        # SEGGER RTT子菜单
        segger_menu = QMenu("SEGGER RTT", self)
        
        # RTT介绍
        rtt_intro_action = QAction("RTT介绍", self)
        rtt_intro_action.setToolTip("打开SEGGER RTT官方文档")
        rtt_intro_action.triggered.connect(self._on_rtt_intro)
        segger_menu.addAction(rtt_intro_action)
        
        # RTT源码
        rtt_source_action = QAction("RTT源码", self)
        rtt_source_action.setToolTip("查看SEGGER RTT源码")
        rtt_source_action.triggered.connect(self._on_rtt_source)
        segger_menu.addAction(rtt_source_action)
        
        # RTT移植文档
        rtt_porting_action = QAction("移植文档", self)
        rtt_porting_action.setToolTip("查看SEGGER RTT移植文档")
        rtt_porting_action.triggered.connect(self._on_rtt_porting)
        segger_menu.addAction(rtt_porting_action)
        
        help_menu.addMenu(segger_menu)
        
        help_menu.addSeparator()
        
        # 关于
        about_action = QAction("关于", self)
        about_action.setToolTip("关于RTT Assistant")
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)
        
        # 添加帮助菜单按钮
        help_button = QPushButton("帮助")
        help_button.setMenu(help_menu)
        toolbar.addWidget(help_button)
        
        toolbar.addSeparator()
        
        # 日志菜单
        log_menu = QMenu("日志", self)
        
        # 系统日志
        system_log_action = QAction("系统日志", self)
        system_log_action.setToolTip("显示系统日志窗口")
        system_log_action.triggered.connect(self._on_log_clicked)
        log_menu.addAction(system_log_action)
        
        # 收发数据日志
        data_log_action = QAction("收发数据日志", self)
        data_log_action.setToolTip("打开收发数据日志文件夹")
        data_log_action.triggered.connect(self._on_open_data_log_folder)
        log_menu.addAction(data_log_action)
        
        # 添加日志菜单按钮
        log_button = QPushButton("日志")
        log_button.setMenu(log_menu)
        toolbar.addWidget(log_button)
    
    def _create_receive_area(self):
        """创建接收区"""
        group = QGroupBox("接收区")
        layout = QVBoxLayout(group)
        
        # 接收文本框
        self.receive_text = QTextEdit()
        self.receive_text.setReadOnly(True)
        self.receive_text.setFont(QFont("Courier New", 10))
        layout.addWidget(self.receive_text)
        
        return group
    
    def _create_send_area(self):
        """创建发送区"""
        group = QGroupBox("发送区")
        layout = QVBoxLayout(group)
        
        # 发送选项布局
        option_layout = QHBoxLayout()
        
        # 发送模式选择
        self.send_mode_combo = QComboBox()
        self.send_mode_combo.addItems(["字符串", "HEX"])
        self.send_mode_combo.setToolTip("发送模式")
        option_layout.addWidget(QLabel("模式:"))
        option_layout.addWidget(self.send_mode_combo)
        
        # 是否加换行
        self.add_newline_checkbox = QCheckBox("加换行")
        self.add_newline_checkbox.setToolTip("发送时自动添加换行符")
        option_layout.addWidget(self.add_newline_checkbox)
        
        option_layout.addStretch()
        
        layout.addLayout(option_layout)
        
        # 发送文本框(多行)
        self.send_input = QTextEdit()
        self.send_input.setFont(QFont("Courier New", 10))
        self.send_input.setMaximumHeight(150)  # 设置最大高度
        self.send_input.setToolTip("输入要发送的数据")
        layout.addWidget(self.send_input)
        
        # 发送按钮
        send_btn_layout = QHBoxLayout()
        send_btn_layout.addStretch()
        
        send_btn = QPushButton("发送")
        send_btn.setToolTip("发送数据")
        send_btn.clicked.connect(self._on_send_clicked)
        send_btn_layout.addWidget(send_btn)
        
        layout.addLayout(send_btn_layout)
        
        return group
    
    def _create_status_bar(self):
        """创建状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 创建状态标签
        self.status_label = QLabel("未连接")
        self.status_bar.addWidget(self.status_label)
        
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
        
        # 添加弹性空间
        self.status_bar.addWidget(QLabel(""), 1)
        
        # 重置按钮
        self.reset_btn = QPushButton("重置")
        self.reset_btn.setToolTip("重置收发计数")
        self.reset_btn.setMaximumWidth(60)
        self.reset_btn.clicked.connect(self.reset_counters_requested.emit)
        self.status_bar.addPermanentWidget(self.reset_btn)
    
    def _on_quick_connect_clicked(self):
        """快速连接按钮点击 - 使用上次配置直接连接"""
        self.quick_connect_requested.emit()
    
    def _on_config_clicked(self):
        """配置按钮点击 - 打开配置对话框"""
        # 显示连接对话框,传入上次的配置
        dialog = ConnectionDialog(
            self, 
            self.last_config.get('rtt_address', ''),
            self.last_config.get('device', 'Cortex-M4'),
            self.last_config.get('rtt_mode', 'auto'),
            self.last_config.get('rtt_range_start', ''),
            self.last_config.get('rtt_range_end', '')
        )
        
        if dialog.exec_() == ConnectionDialog.Accepted:
            # 获取配置
            config = dialog.get_config()
            # 保存配置
            self.last_config = config
            self.config_changed.emit(config)
    
    def _on_disconnect_clicked(self):
        """断开按钮点击"""
        self.disconnect_requested.emit()
    
    def _on_clear_clicked(self):
        """清空按钮点击"""
        self.receive_text.clear()
        self.clear_requested.emit()
    
    def _on_send_clicked(self):
        """发送按钮点击"""
        text = self.send_input.toPlainText()  # 使用toPlainText获取多行文本
        if not text:
            return
        
        is_hex = self.send_mode_combo.currentText() == "HEX"
        add_newline = self.add_newline_checkbox.isChecked()
        
        # HEX模式验证
        if is_hex:
            # 移除空格
            hex_str = text.replace(" ", "")
            
            # 验证是否为空
            if not hex_str:
                QMessageBox.warning(self, "HEX格式错误", "HEX数据不能为空")
                return
            
            # 验证是否为偶数长度
            if len(hex_str) % 2 != 0:
                QMessageBox.warning(self, "HEX格式错误", 
                    f"HEX数据长度必须为偶数\n当前长度: {len(hex_str)}个字符\n\n请检查输入数据")
                return
            
            # 验证是否都是有效的十六进制字符
            valid_chars = set('0123456789ABCDEFabcdef')
            invalid_chars = set(hex_str) - valid_chars
            if invalid_chars:
                QMessageBox.warning(self, "HEX格式错误", 
                    f"包含非法字符: {invalid_chars}\n\nHEX数据只能包含0-9和A-F(或a-f)")
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
            except:
                pass
    
    def _on_font_clicked(self):
        """字体按钮点击"""
        # TODO: 显示字体对话框
        from PyQt5.QtWidgets import QFontDialog
        font, ok = QFontDialog.getFont(self.receive_text.font(), self)
        if ok:
            self.receive_text.setFont(font)
            self.font_changed.emit(font)
    
    def append_receive_data(self, text):
        """
        追加接收数据
        
        Args:
            text: 要追加的文本
        """
        self.receive_text.moveCursor(QTextCursor.End)
        self.receive_text.insertPlainText(text)
        self.receive_text.moveCursor(QTextCursor.End)
        
        # 保存到数据日志文件
        if self.data_log_handle:
            try:
                from datetime import datetime
                timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                self.data_log_handle.write(f"[{timestamp}] [RX] {text}\n")
                self.data_log_handle.flush()
            except:
                pass
    
    def set_connected(self, connected):
        """
        设置连接状态
        
        Args:
            connected: 是否已连接
        """
        self.connect_action.setEnabled(not connected)
        self.disconnect_action.setEnabled(connected)
        
        if connected:
            self.status_label.setText("已连接")
        else:
            self.status_label.setText("未连接")
    
    def set_status(self, text):
        """
        设置状态栏文本
        
        Args:
            text: 状态文本
        """
        self.status_label.setText(text)
    
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
        # 关闭数据日志文件
        if self.data_log_handle:
            try:
                self.data_log_handle.close()
            except:
                pass
        event.accept()
    
    def _on_help_document(self):
        """打开帮助文档"""
        import os
        help_file = get_resource_path("README.md")
        if help_file and os.path.exists(help_file):
            os.startfile(help_file)
        else:
            QMessageBox.information(self, "帮助", 
                "RTT Assistant - RTT调试助手\n\n"
                "使用方法:\n"
                "1. 点击'配置'设置连接参数\n"
                "2. 点击'连接'连接到MCU\n"
                "3. 在发送区输入数据并发送\n"
                "4. 接收区显示MCU返回的数据\n\n"
                "详细文档请查看README.md")
    
    def _on_changelog(self):
        """显示升级日志"""
        import os
        changelog_file = get_resource_path("更新说明.md")
        if changelog_file and os.path.exists(changelog_file):
            os.startfile(changelog_file)
        else:
            QMessageBox.information(self, "升级日志",
                "RTT Assistant v1.3.1\n\n"
                "新增功能:\n"
                "• 系统日志窗口\n"
                "• 数据自动保存和导出\n"
                "• 设备型号筛选功能\n"
                "• 帮助菜单\n\n"
                "改进:\n"
                "• 扩展设备型号列表(300+)\n"
                "• 优化配置管理\n"
                "• 添加软件图标")
    
    def _on_open_data_log_folder(self):
        """打开收发数据日志文件夹"""
        import os
        import sys
        
        # 获取当前目录
        if getattr(sys, 'frozen', False):
            # 打包后
            folder = os.path.dirname(sys.executable)
        else:
            # 开发模式
            folder = os.getcwd()
        
        # 打开文件夹
        os.startfile(folder)
    
    def _on_about(self):
        """显示关于对话框"""
        from PyQt5.QtWidgets import QDialog, QLabel, QVBoxLayout, QPushButton
        from PyQt5.QtGui import QPixmap
        from PyQt5.QtCore import Qt
        
        # 创建自定义对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("关于 RTT Assistant")
        dialog.setFixedSize(450, 400)
        
        layout = QVBoxLayout(dialog)
        
        # 标题
        title = QLabel("<h2>RTT Assistant</h2>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 版本信息
        version = QLabel("<p>版本: v1.3.1</p><p>RTT调试助手</p><p>基于SEGGER JLink RTT技术</p>")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)
        
        # 分隔线
        layout.addWidget(QLabel("<hr>"))
        
        # 作者信息
        author = QLabel("<p><b>作者:</b> 陈卡卡</p>")
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
        github_label = QLabel('<p><a href="https://github.com/cl234583745" style="text-decoration:none; color:#0000ff;"><b>GitHub:</b> cl234583745</a></p>')
        github_label.setAlignment(Qt.AlignCenter)
        github_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        github_label.setOpenExternalLinks(True)
        layout.addWidget(github_label)
        
        # Gitee(可点击)
        gitee_label = QLabel('<p><a href="https://gitee.com/292812832" style="text-decoration:none; color:#0000ff;"><b>Gitee:</b> 292812832</a></p>')
        gitee_label.setAlignment(Qt.AlignCenter)
        gitee_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        gitee_label.setOpenExternalLinks(True)
        layout.addWidget(gitee_label)
        
        # 分隔线
        layout.addWidget(QLabel("<hr>"))
        
        # 版权信息
        copyright_label = QLabel("<p>© 2024 RTT Assistant. All rights reserved.</p>")
        copyright_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(copyright_label)
        
        # 确定按钮
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(dialog.accept)
        layout.addWidget(ok_btn)
        
        dialog.exec_()
    
    def _show_qrcode(self, parent):
        """显示公众号二维码"""
        import os
        import sys
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel
        from PyQt5.QtGui import QPixmap
        from PyQt5.QtCore import Qt
        
        # 创建对话框
        dialog = QDialog(parent)
        dialog.setWindowTitle("公众号: 嵌入式科普")
        dialog.setFixedSize(350, 400)
        
        layout = QVBoxLayout(dialog)
        
        # 标题
        title = QLabel("<h3>扫码关注公众号</h3>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 二维码图片
        qrcode_label = QLabel()
        
        # 查找二维码图片
        qrcode_path = get_resource_path("duokajiangfllpll.png")
        
        if qrcode_path and os.path.exists(qrcode_path):
            pixmap = QPixmap(qrcode_path)
            if not pixmap.isNull():
                # 缩放图片
                scaled_pixmap = pixmap.scaled(280, 280, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                qrcode_label.setPixmap(scaled_pixmap)
            else:
                qrcode_label.setText("无法加载二维码图片")
        else:
            qrcode_label.setText("未找到二维码图片")
        
        qrcode_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(qrcode_label)
        
        # 提示
        tip = QLabel("<p>公众号: <b>嵌入式科普</b></p>")
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
            QMessageBox.warning(self, "错误", f"无法打开网页: {e}")
    
    def _on_rtt_source(self):
        """打开SEGGER RTT源码"""
        import os
        import sys
        
        # 检查是否是打包后的exe
        if is_frozen():
            # 打包后,打开zip文件
            zip_path = get_resource_path("SEGGER_RTT.zip")
            if zip_path and os.path.exists(zip_path):
                os.startfile(zip_path)
            else:
                QMessageBox.warning(self, "错误", 
                    f"未找到SEGGER RTT源码包\n\n"
                    f"请确保SEGGER_RTT.zip文件被打包")
        else:
            # 开发模式,打开源码目录
            source_dir = get_resource_path("SEGGER_RTT")
            if source_dir and os.path.exists(source_dir):
                os.startfile(source_dir)
            else:
                QMessageBox.warning(self, "错误", 
                    f"未找到SEGGER RTT源码目录")
    
    def _on_rtt_porting(self):
        """打开SEGGER RTT移植文档"""
        import os
        import sys
        
        # 尝试打开md文档
        guide_path = get_resource_path("SEGGER_RTT移植指南.md")
        if guide_path and os.path.exists(guide_path):
            os.startfile(guide_path)
        else:
            # 显示内置文档
            self._show_porting_doc()
    
    def _show_porting_doc(self):
        """显示SEGGER RTT移植文档"""
        QMessageBox.information(self, "SEGGER RTT移植指南",
            "<h3>SEGGER RTT移植步骤</h3>"
            "<ol>"
            "<li><b>添加源码文件</b><br>"
            "将SEGGER_RTT.c、SEGGER_RTT.h、SEGGER_RTT_Conf.h添加到工程</li>"
            "<li><b>配置RTT</b><br>"
            "修改SEGGER_RTT_Conf.h配置缓冲区大小和通道数</li>"
            "<li><b>初始化RTT</b><br>"
            "在main函数开头调用SEGGER_RTT_Init()</li>"
            "<li><b>使用RTT输出</b><br>"
            "使用SEGGER_RTT_printf()或SEGGER_RTT_Write()输出数据</li>"
            "<li><b>连接JLink</b><br>"
            "使用JLink RTT Viewer或RTT Assistant查看输出</li>"
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
            "导出收发数据",
            "rtt_data.txt",
            "文本文件 (*.txt);;所有文件 (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.receive_text.toPlainText())
            except Exception as e:
                pass
    

