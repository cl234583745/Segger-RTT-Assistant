#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
连接配置对话框
类似JLinkRTTViewer的连接配置界面
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QRadioButton, QCheckBox, QLineEdit,
    QPushButton, QComboBox, QLabel, QFileDialog, QDialogButtonBox
)
from PyQt5.QtCore import Qt
from ..utils.resource_utils import get_external_file, get_exe_dir


class ConnectionDialog(QDialog):
    """连接配置对话框"""
    
    def __init__(self, parent=None, last_rtt_address="", last_device="Cortex-M4", 
                 rtt_mode="auto", rtt_range_start="", rtt_range_size="", log_service=None):
        super().__init__(parent)
        self.setWindowTitle("连接配置")
        self.setModal(True)
        self.resize(500, 400)
        
        self.last_rtt_address = last_rtt_address
        self.last_device = last_device
        self.rtt_mode = rtt_mode
        self.rtt_range_start = rtt_range_start
        self.rtt_range_size = rtt_range_size
        self.log_service = log_service
        
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        connection_group = self._create_connection_group()
        layout.addWidget(connection_group)
        
        device_group = self._create_device_group()
        layout.addWidget(device_group)
        
        interface_group = self._create_interface_group()
        layout.addWidget(interface_group)
        
        rtt_group = self._create_rtt_group()
        layout.addWidget(rtt_group)
        
        button_layout = self._create_buttons()
        layout.addLayout(button_layout)
    
    def _create_connection_group(self):
        """创建连接方式选择组"""
        group = QGroupBox("连接方式")
        layout = QHBoxLayout(group)
        
        self.usb_radio = QRadioButton("USB")
        self.usb_radio.setChecked(True)
        layout.addWidget(self.usb_radio)
        
        self.sn_checkbox = QCheckBox("SN/Nickname")
        layout.addWidget(self.sn_checkbox)
        
        self.sn_edit = QLineEdit()
        self.sn_edit.setPlaceholderText("序列号或昵称")
        self.sn_edit.setEnabled(False)
        layout.addWidget(self.sn_edit)
        
        self.tcp_radio = QRadioButton("TCP/IP")
        layout.addWidget(self.tcp_radio)
        
        self.ip_edit = QLineEdit()
        self.ip_edit.setPlaceholderText("IP地址")
        self.ip_edit.setEnabled(False)
        layout.addWidget(self.ip_edit)
        
        self.sn_checkbox.stateChanged.connect(
            lambda state: self.sn_edit.setEnabled(state == Qt.Checked)
        )
        
        self.usb_radio.toggled.connect(self._on_connection_changed)
        self.tcp_radio.toggled.connect(self._on_connection_changed)
        
        return group
    
    def _create_device_group(self):
        """创建目标设备选择组"""
        group = QGroupBox("目标设备")
        layout = QHBoxLayout(group)
        
        layout.addWidget(QLabel("设备型号:"))
        
        self.device_combo = QComboBox()
        self.device_combo.setEditable(True)
        
        device_list = self._load_device_list()
        
        self.device_combo.addItems(device_list)
        self.device_combo.setCurrentText(self.last_device)
        layout.addWidget(self.device_combo)
        
        browse_btn = QPushButton("...")
        browse_btn.setFixedWidth(30)
        browse_btn.setToolTip("筛选设备型号")
        browse_btn.clicked.connect(self._on_browse_device)
        layout.addWidget(browse_btn)
        
        update_btn = QPushButton("更新")
        update_btn.setFixedWidth(40)
        update_btn.setToolTip("从J-Link DLL更新设备列表到devices.txt")
        update_btn.clicked.connect(self._on_update_devices)
        layout.addWidget(update_btn)
        
        self.force_checkbox = QCheckBox("Force go on connect")
        layout.addWidget(self.force_checkbox)
        
        return group
    
    def _create_interface_group(self):
        """创建接口和速度设置组"""
        group = QGroupBox("接口设置")
        layout = QHBoxLayout(group)
        
        layout.addWidget(QLabel("接口:"))
        self.interface_combo = QComboBox()
        self.interface_combo.addItems(["SWD", "JTAG"])
        layout.addWidget(self.interface_combo)
        
        layout.addSpacing(20)
        
        layout.addWidget(QLabel("速度:"))
        self.speed_combo = QComboBox()
        self.speed_combo.addItems([
            "1000 kHz",
            "2000 kHz",
            "4000 kHz",
            "8000 kHz",
            "12000 kHz",
            "16000 kHz",
            "20000 kHz",
        ])
        self.speed_combo.setCurrentText("4000 kHz")
        layout.addWidget(self.speed_combo)
        
        return group
    
    def _create_rtt_group(self):
        """创建RTT控制块设置组"""
        group = QGroupBox("RTT控制块")
        layout = QVBoxLayout(group)
        
        auto_layout = QHBoxLayout()
        self.auto_radio = QRadioButton("自动检测")
        auto_layout.addWidget(self.auto_radio)
        auto_hint = QLabel('<a href="https://kb.segger.com/RTT#Auto-detection" style="text-decoration:none; color:#888888; font-size:9px;">先查向量表0x20,再扫SRAM | 详情</a>')
        auto_hint.setOpenExternalLinks(True)
        auto_layout.addWidget(auto_hint)
        auto_layout.addStretch()
        layout.addLayout(auto_layout)
        
        address_layout = QHBoxLayout()
        self.address_radio = QRadioButton("地址:")
        address_layout.addWidget(self.address_radio)
        
        self.address_edit = QLineEdit()
        self.address_edit.setPlaceholderText("从map文件搜索_SEGGER_RTT")
        self.address_edit.setEnabled(False)
        if self.last_rtt_address:
            self.address_edit.setText(self.last_rtt_address)
        address_layout.addWidget(self.address_edit)
        
        address_layout.addStretch()
        layout.addLayout(address_layout)
        
        range_layout = QHBoxLayout()
        self.range_radio = QRadioButton("搜索范围:")
        range_layout.addWidget(self.range_radio)
        
        self.range_start_edit = QLineEdit()
        self.range_start_edit.setPlaceholderText("起始地址")
        self.range_start_edit.setEnabled(False)
        if self.rtt_range_start:
            self.range_start_edit.setText(self.rtt_range_start)
        range_layout.addWidget(self.range_start_edit)
        
        range_layout.addWidget(QLabel("-"))
        
        self.range_size_edit = QLineEdit()
        self.range_size_edit.setPlaceholderText("大小")
        self.range_size_edit.setEnabled(False)
        if self.rtt_range_size:
            self.range_size_edit.setText(self.rtt_range_size)
        range_layout.addWidget(self.range_size_edit)
        
        range_layout.addStretch()
        layout.addLayout(range_layout)
        
        self.auto_radio.toggled.connect(self._on_rtt_mode_changed)
        self.address_radio.toggled.connect(self._on_rtt_mode_changed)
        self.range_radio.toggled.connect(self._on_rtt_mode_changed)
        
        if self.rtt_mode == "address":
            self.address_radio.setChecked(True)
        elif self.rtt_mode == "range":
            self.range_radio.setChecked(True)
        else:
            self.auto_radio.setChecked(True)
        
        return group
    
    def _create_buttons(self):
        """创建按钮"""
        layout = QHBoxLayout()
        layout.addStretch()
        
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)
        
        return layout
    
    def _on_connection_changed(self):
        """连接方式变化"""
        is_usb = self.usb_radio.isChecked()
        self.sn_checkbox.setEnabled(is_usb)
        self.sn_edit.setEnabled(is_usb and self.sn_checkbox.isChecked())
        self.ip_edit.setEnabled(not is_usb)
    
    def _load_device_list(self):
        """从配置文件加载设备列表"""
        import os
        
        default_devices = [
            "Cortex-M0", "Cortex-M0+", "Cortex-M1", "Cortex-M3", "Cortex-M4", "Cortex-M7",
            "STM32F103", "STM32F407", "STM32H743",
            "NRF52832", "NRF52840",
            "R9A07G084M04",
        ]
        
        config_paths = [
            get_external_file("devices.txt"),
            os.path.join(os.getcwd(), "devices.txt"),
            os.path.join(os.path.dirname(__file__), "..", "..", "devices.txt"),
        ]
        
        for config_path in config_paths:
            if config_path is None:
                continue
            if os.path.exists(config_path):
                try:
                    devices = []
                    with open(config_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                devices.append(line)
                    
                    if devices:
                        return devices
                except:
                    pass
        
        return default_devices
    
    def _on_browse_device(self):
        """浏览设备 - 打开筛选对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("设备型号筛选")
        dialog.setMinimumSize(400, 500)
        
        layout = QVBoxLayout(dialog)
        
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("搜索:"))
        search_edit = QLineEdit()
        search_edit.setPlaceholderText("输入关键字筛选")
        search_layout.addWidget(search_edit)
        layout.addLayout(search_layout)
        
        from PyQt5.QtWidgets import QListWidget
        device_list_widget = QListWidget()
        
        devices = [self.device_combo.itemText(i) for i in range(self.device_combo.count())]
        device_list_widget.addItems(devices)
        layout.addWidget(device_list_widget)
        
        def filter_devices(text):
            device_list_widget.clear()
            filtered = [d for d in devices if text.lower() in d.lower()]
            device_list_widget.addItems(filtered)
        
        search_edit.textChanged.connect(filter_devices)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        if dialog.exec_() == QDialog.Accepted:
            current_item = device_list_widget.currentItem()
            if current_item:
                self.device_combo.setCurrentText(current_item.text())
    
    def _on_update_devices(self):
        """从J-Link DLL更新设备列表到devices.txt"""
        from PyQt5.QtWidgets import QMessageBox, QProgressDialog
        from PyQt5.QtCore import Qt
        import pylink
        from pylink import library
        import os
        
        dll_path = get_external_file("JLink_x64.dll")
        if dll_path is None:
            dll_path = get_external_file("JLinkARM.dll")
        if dll_path is None:
            err_msg = "未找到JLink DLL文件"
            if self.log_service:
                self.log_service.error(f"更新设备列表失败: {err_msg}")
            QMessageBox.warning(self, "错误", err_msg)
            return
        
        try:
            jlink_lib = library.Library(dllpath=dll_path)
            jlink = pylink.JLink(lib=jlink_lib)
            jlink.open()
            num_devices = jlink.num_supported_devices()
            
            if self.log_service:
                self.log_service.info(f"开始从DLL读取设备列表, 共{num_devices}个设备")
            
            progress = QProgressDialog(f"正在从DLL读取{num_devices}个设备...", "取消", 0, num_devices, self)
            progress.setWindowTitle("更新设备列表")
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.show()
            
            devices = []
            for i in range(num_devices):
                if progress.wasCanceled():
                    break
                try:
                    d = jlink.supported_device(i)
                    if d and d.name:
                        devices.append(d.name)
                except:
                    pass
                if i % 200 == 0:
                    progress.setValue(i)
                    from PyQt5.QtWidgets import QApplication
                    QApplication.processEvents()
            
            progress.setValue(num_devices)
            jlink.close()
            
            if not devices:
                err_msg = "未能从DLL读取到设备列表"
                if self.log_service:
                    self.log_service.error(f"更新设备列表失败: {err_msg}")
                QMessageBox.warning(self, "错误", err_msg)
                return
            
            devices.sort()
            
            devices_file = os.path.join(get_exe_dir(), "devices.txt")
            with open(devices_file, 'w', encoding='utf-8') as f:
                f.write("# RTT Assistant - 支持的设备型号列表\n")
                f.write(f"# 从J-Link DLL自动生成, 共{len(devices)}个设备\n")
                f.write("#\n")
                for d in devices:
                    f.write(f"{d}\n")
            
            self.device_combo.clear()
            self.device_combo.addItems(devices)
            self.device_combo.setCurrentText(self.last_device)
            
            if self.log_service:
                self.log_service.success(f"设备列表已更新: {len(devices)}个设备, 保存至{devices_file}")
            QMessageBox.information(self, "完成", f"已更新设备列表: {len(devices)}个设备\n保存至: {devices_file}")
            
        except Exception as e:
            err_msg = f"更新设备列表失败: {e}"
            if self.log_service:
                self.log_service.error(err_msg)
            QMessageBox.warning(self, "错误", err_msg)
    
    def _on_rtt_mode_changed(self):
        """RTT模式变化"""
        self.address_edit.setEnabled(self.address_radio.isChecked())
        self.range_start_edit.setEnabled(self.range_radio.isChecked())
        self.range_size_edit.setEnabled(self.range_radio.isChecked())
    
    def get_config(self):
        """获取配置信息"""
        speed_str = self.speed_combo.currentText()
        speed = int(speed_str.split()[0])
        
        config = {
            "connection_type": "USB" if self.usb_radio.isChecked() else "TCP",
            "serial_number": self.sn_edit.text() if self.sn_checkbox.isChecked() else None,
            "ip_address": self.ip_edit.text() if self.tcp_radio.isChecked() else None,
            "device": self.device_combo.currentText(),
            "force_go": self.force_checkbox.isChecked(),
            "interface": self.interface_combo.currentText(),
            "speed": speed,
            "rtt_mode": "auto" if self.auto_radio.isChecked() else 
                       "address" if self.address_radio.isChecked() else "range",
            "rtt_address": self.address_edit.text() if self.address_radio.isChecked() else None,
            "rtt_range_start": self.range_start_edit.text() if self.range_radio.isChecked() else None,
            "rtt_range_size": self.range_size_edit.text() if self.range_radio.isChecked() else None,
        }
        
        return config
