#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
日志窗口
显示连接、通讯和错误日志
实时读取日志文件
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QComboBox, QLabel, QFileDialog
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QTextCursor, QColor


class LogWindow(QWidget):
    """日志窗口"""
    
    # 信号定义
    clear_requested = pyqtSignal()  # 清空日志信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.log_service = None  # 日志服务
        self.last_content = ""  # 上次的内容
        self.init_ui()
        
        # 创建定时器,定期刷新日志
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._refresh_log)
        self.refresh_timer.start(1000)  # 每秒刷新一次
    
    def init_ui(self):
        """初始化UI"""
        # 设置窗口属性
        self.setWindowTitle('系统日志')
        self.setMinimumSize(600, 400)
        
        # 主布局
        layout = QVBoxLayout()
        
        # 工具栏
        toolbar_layout = QHBoxLayout()
        
        # 日志类型过滤
        toolbar_layout.addWidget(QLabel('日志类型:'))
        self.type_combo = QComboBox()
        self.type_combo.addItems(['全部', 'INFO', 'WARNING', 'ERROR', 'SUCCESS'])
        self.type_combo.currentTextChanged.connect(self.on_filter_changed)
        toolbar_layout.addWidget(self.type_combo)
        
        toolbar_layout.addStretch()
        
        # 清空按钮
        self.clear_btn = QPushButton('清空')
        self.clear_btn.clicked.connect(self.on_clear_clicked)
        toolbar_layout.addWidget(self.clear_btn)
        
        # 打开日志文件按钮
        self.open_file_btn = QPushButton('打开日志文件')
        self.open_file_btn.clicked.connect(self._on_open_log_file)
        toolbar_layout.addWidget(self.open_file_btn)
        
        layout.addLayout(toolbar_layout)
        
        # 日志显示区域
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: Consolas, 'Courier New', monospace;
                font-size: 10pt;
            }
        """)
        layout.addWidget(self.log_text)
        
        self.setLayout(layout)
    
    def showEvent(self, event):
        """窗口显示事件"""
        super().showEvent(event)
        # 窗口显示时立即刷新日志
        self._refresh_log()
        # 启动定时器
        if not self.refresh_timer.isActive():
            self.refresh_timer.start(1000)
        
        # 存储所有日志
        self.all_logs = []
    
    def set_log_service(self, log_service):
        """
        设置日志服务
        
        Args:
            log_service: 日志服务对象
        """
        self.log_service = log_service
        # 立即刷新一次
        self._refresh_log()
    
    def _refresh_log(self):
        """刷新日志(从文件读取)"""
        if not self.log_service:
            return
        
        # 读取日志文件
        content = self.log_service.read_log_file()
        
        # 如果内容有变化,更新显示
        if content != self.last_content:
            self.last_content = content
            self._display_log_content(content)
    
    def _display_log_content(self, content):
        """
        显示日志内容
        
        Args:
            content: 日志内容
        """
        # 清空显示
        self.log_text.clear()
        
        # 获取当前过滤类型
        filter_type = self.type_combo.currentText()
        
        # 按行处理
        lines = content.split('\n')
        for line in lines:
            if not line.strip():
                continue
            
            # 解析日志行
            # 格式: [HH:MM:SS.mmm] [TYPE] message
            import re
            match = re.match(r'\[(\d{2}:\d{2}:\d{2}\.\d{3})\] \[(\w+)\] (.+)', line)
            
            if match:
                timestamp, log_type, message = match.groups()
                
                # 根据过滤条件显示
                if filter_type == '全部' or filter_type == log_type:
                    self._append_log(timestamp, log_type, message)
            else:
                # 不是标准日志格式,直接显示(如分隔线)
                cursor = self.log_text.textCursor()
                cursor.movePosition(QTextCursor.End)
                cursor.insertText(line + '\n')
        
        # 滚动到底部
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_text.setTextCursor(cursor)
        self.log_text.ensureCursorVisible()
    
    def _append_log(self, timestamp, log_type, message):
        """
        追加日志到显示区域
        
        Args:
            timestamp: 时间戳
            log_type: 日志类型
            message: 日志消息
        """
        # 获取颜色
        color = self._get_color(log_type)
        
        # 格式化日志
        log_text = f'[{timestamp}] [{log_type}] {message}'
        
        # 追加带颜色的文本
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        # 设置颜色
        format = cursor.charFormat()
        format.setForeground(QColor(color))
        cursor.setCharFormat(format)
        
        # 插入文本
        cursor.insertText(log_text + '\n')
    
    def _get_color(self, log_type):
        """
        获取日志类型对应的颜色
        
        Args:
            log_type: 日志类型
        
        Returns:
            str: 颜色代码
        """
        colors = {
            'INFO': '#00ff00',      # 绿色
            'WARNING': '#ffff00',   # 黄色
            'ERROR': '#ff0000',     # 红色
            'SUCCESS': '#00ffff'    # 青色
        }
        return colors.get(log_type, '#d4d4d4')
    
    def on_filter_changed(self, filter_type):
        """
        日志类型过滤改变
        
        Args:
            filter_type: 过滤类型
        """
        # 重新显示日志
        if self.log_service:
            content = self.log_service.read_log_file()
            self._display_log_content(content)
    
    def on_clear_clicked(self):
        """清空按钮点击"""
        self.all_logs.clear()
        self.log_text.clear()
        self.clear_requested.emit()
    
    def clear(self):
        """清空日志"""
        self.all_logs.clear()
        self.log_text.clear()
    
    def _on_open_log_file(self):
        """打开日志文件"""
        import os
        if self.log_service and os.path.exists(self.log_service.log_file_path):
            os.startfile(self.log_service.log_file_path)
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 停止定时器
        self.refresh_timer.stop()
        event.accept()
    
    def _on_auto_save_toggled(self, state):
        """自动保存开关切换"""
        self.auto_save_enabled = (state == Qt.Checked)
        self.auto_save_toggled.emit(self.auto_save_enabled)
    
    def _on_export_clicked(self):
        """导出按钮点击"""
        # 选择保存文件
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出日志",
            "rtt_log.txt",
            "文本文件 (*.txt);;所有文件 (*)"
        )
        
        if file_path:
            try:
                # 写入日志
                with open(file_path, 'w', encoding='utf-8') as f:
                    for log in self.all_logs:
                        line = f'[{log["timestamp"]}] [{log["type"]}] {log["message"]}\n'
                        f.write(line)
                
                # 提示成功
                self.add_log('', 'INFO', f'日志已导出到: {file_path}')
            except Exception as e:
                self.add_log('', 'ERROR', f'导出失败: {e}')
