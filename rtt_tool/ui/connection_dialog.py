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
连接配置对话框
类似JLinkRTTViewer的连接配置界面
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QRadioButton, QCheckBox, QLineEdit,
    QPushButton, QComboBox, QLabel, QFileDialog, QDialogButtonBox, QMessageBox,
    QListWidget, QAbstractItemView
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from ..utils.resource_utils import get_external_file, get_exe_dir
from ..utils.device_info_service import DeviceInfoService


class _ProbeDetectThread(QThread):
    """后台探测线程，避免阻塞UI。"""
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, debugger_manager, parent=None):
        super().__init__(parent)
        self._debugger_manager = debugger_manager

    def run(self):
        try:
            probes = self._debugger_manager.detect_all_probes()
            self.finished.emit(probes)
        except Exception as e:
            self.error.emit(f"{type(e).__name__}: {e}")


class ConnectionDialog(QDialog):
    """连接配置对话框"""
    
    def __init__(self, parent=None, last_rtt_address="", last_device="Cortex-M4",
                 rtt_mode="auto", rtt_range_start="", rtt_range_size="", map_file_path="",
                 log_service=None, device_info_service=None, debugger_manager=None,
                 connect_mode="under_reset", pyocd_target="",
                 probe_name="", probe_backend="", probe_serial=""):
        super().__init__(parent)
        self.setWindowTitle("连接配置")
        self.setModal(True)
        self.resize(500, 500)

        self.last_rtt_address = last_rtt_address
        self.last_device = last_device
        self.rtt_mode = rtt_mode
        self.rtt_range_start = rtt_range_start
        self.rtt_range_size = rtt_range_size
        self.map_file_path = map_file_path
        self.connect_mode = connect_mode
        self.last_pyocd_target = pyocd_target
        self.log_service = log_service
        self._device_info_service = device_info_service if device_info_service else DeviceInfoService(log_service=log_service)
        self._debugger_manager = debugger_manager

        self._saved_probe_name = probe_name
        self._saved_probe_backend = probe_backend
        self._saved_probe_serial = probe_serial

        self._detected_probes = []
        self._current_backend = 'jlink'

        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        from datetime import datetime
        if self.log_service:
            self.log_service.debug(f"[性能] 开始初始化UI: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #cccccc;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px;
            }
        """)
        
        debugger_group = self._create_debugger_group()
        layout.addWidget(debugger_group)
        
        connection_group = self._create_connection_group()
        layout.addWidget(connection_group)
        
        if self.log_service:
            self.log_service.debug(f"[性能] 连接组创建完成: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
        
        device_group = self._create_device_group()
        layout.addWidget(device_group)
        
        if self.log_service:
            self.log_service.debug(f"[性能] 设备组创建完成: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
        
        interface_group = self._create_interface_group()
        layout.addWidget(interface_group)
        
        rtt_group = self._create_rtt_group()
        layout.addWidget(rtt_group)
        
        # 设备组已创建完毕，应用保存的探针对应的后端UI
        if self._saved_probe_backend:
            self._update_device_ui_for_backend(self._saved_probe_backend)
        
        # 所有UI控件已创建完毕，连接探针选择信号
        self.probe_list.currentItemChanged.connect(self._on_probe_selection_changed)
        
        button_layout = self._create_buttons()
        layout.addLayout(button_layout)
        
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(0, self._deferred_load)
        
        if self.log_service:
            self.log_service.debug(f"[性能] UI初始化完成: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
    
    def _deferred_load(self):
        """延迟加载设备列表和PyOCD目标（对话框已显示后执行）"""
        try:
            if not self._device_list_loaded:
                device_list = self._load_device_list()
                if device_list:
                    current = self.device_combo.currentText()
                    self.device_combo.clear()
                    self.device_combo.addItems(device_list)
                    self.device_combo.setCurrentText(current or self.last_device)
                self._device_list_loaded = True
        except Exception as e:
            if self.log_service:
                self.log_service.warning(f'延迟加载设备列表失败: {e}')
            self._device_list_loaded = True
        try:
            self._load_pyocd_targets()
        except Exception as e:
            if self.log_service:
                self.log_service.warning(f'延迟加载PyOCD目标失败: {e}')

    def _create_debugger_group(self):
        """创建调试器选择组"""
        group = QGroupBox("步骤1: 调试器选择")
        layout = QHBoxLayout(group)
        
        layout.addWidget(QLabel("已连接探针:"))
        self.probe_list = QListWidget()
        self.probe_list.setFixedHeight(100)
        self.probe_list.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addWidget(self.probe_list, 1)
        
        btn_layout = QVBoxLayout()
        self._refresh_btn = QPushButton("刷新")
        self._refresh_btn.setToolTip("重新探测调试器")
        self._refresh_btn.clicked.connect(self._start_probe_detect)
        btn_layout.addWidget(self._refresh_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # 显示已保存的探针（不自动探测）
        self._show_saved_probe()
        
        return group
    
    def _show_saved_probe(self):
        """显示上次保存的探针"""
        self.probe_list.clear()
        if self._saved_probe_name:
            from PyQt5.QtWidgets import QListWidgetItem
            display = f"[{self._saved_probe_backend}] {self._saved_probe_name}"
            if self._saved_probe_serial:
                display += f" (SN:{self._saved_probe_serial})"
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, {
                'name': self._saved_probe_name,
                'backend': self._saved_probe_backend,
                'serial': self._saved_probe_serial,
            })
            self.probe_list.addItem(item)
            self.probe_list.setCurrentItem(item)
        else:
            self.probe_list.addItem("-- 请点击「刷新」探测探针 --")
    
    def _start_probe_detect(self):
        """启动后台探测"""
        if self._debugger_manager is None:
            self.probe_list.clear()
            self.probe_list.addItem("-- 调试器管理器未初始化 --")
            return
        
        self._refresh_btn.setEnabled(False)
        self.probe_list.clear()
        self.probe_list.addItem("正在探测...")
        
        self._detected_probes = []
        
        self._detect_thread = _ProbeDetectThread(self._debugger_manager, self)
        self._detect_thread.finished.connect(self._on_probe_detect_finished)
        self._detect_thread.error.connect(self._on_probe_detect_error)
        self._detect_thread.start()
    
    def _on_probe_detect_finished(self, probes):
        """后台探测完成"""
        self._refresh_btn.setEnabled(True)
        self.probe_list.clear()

        if not probes:
            self.probe_list.addItem("-- 未探测到探针 --")
            if self.log_service:
                self.log_service.warning("探测结果: 未发现任何探针")
            self._update_device_ui_for_backend('jlink')
            return

        self._detected_probes = probes
        from PyQt5.QtWidgets import QListWidgetItem

        for probe in probes:
            ptype = probe.get('type', '?')
            pname = probe.get('name', 'Unknown')
            pserial = probe.get('serial', '')
            display = f"[{ptype}] {pname}" + (f" (SN:{pserial})" if pserial else "")
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, probe)
            self.probe_list.addItem(item)

        self.probe_list.setCurrentRow(0)
        if self.log_service:
            self.log_service.success(f"探测到 {len(probes)} 个探针")

        first_probe = probes[0] if probes else {}
        backend = first_probe.get('backend', 'jlink')
        self._update_device_ui_for_backend(backend)
    
    def _on_probe_detect_error(self, error_msg):
        """后台探测出错"""
        self._refresh_btn.setEnabled(True)
        self.probe_list.clear()
        self.probe_list.addItem("-- 探测失败 --")
        if self.log_service:
            self.log_service.error(f"探测探针失败: {error_msg}")
        QMessageBox.warning(self, "探测失败", f"错误详情:\n{error_msg}")

    def _on_probe_selection_changed(self, current, previous):
        """探针选择变化"""
        if current is None:
            return
        selected_probe = current.data(Qt.UserRole)
        if selected_probe and isinstance(selected_probe, dict):
            backend = selected_probe.get('backend', 'jlink')
            self._update_device_ui_for_backend(backend)

    def _update_device_ui_for_backend(self, backend):
        """根据后端类型切换设备UI"""
        is_jlink = backend == 'jlink'
        is_pyocd = backend == 'pyocd'
        self._current_backend = backend

        # J-Link 设备选择控件
        self.jlink_device_label.setEnabled(is_jlink)
        self.device_combo.setEnabled(is_jlink)
        self.browse_btn.setEnabled(is_jlink)
        self.update_btn.setEnabled(is_jlink)

        # PyOCD 目标选择控件
        self.pyocd_device_label.setEnabled(is_pyocd)
        self.pyocd_target_combo.setEnabled(is_pyocd)
        self.pyocd_browse_btn.setEnabled(is_pyocd)
        self.pyocd_update_btn.setEnabled(is_pyocd)

        # J-Link 专用控件："获取自动检测地址"依赖J-Link设备数据库，PyOCD时禁用
        if hasattr(self, 'auto_fill_btn'):
            self.auto_fill_btn.setEnabled(is_jlink and self.range_radio.isChecked())

    def _load_pyocd_targets(self):
        """加载 PyOCD 支持的目标列表（从文件或Pack）"""
        if self._pyocd_targets_loaded:
            return
        from ..utils.resource_utils import get_exe_dir
        import os

        targets_file = os.path.join(get_exe_dir(), 'pyocd_targets.txt')

        if os.path.exists(targets_file):
            try:
                with open(targets_file, 'r', encoding='utf-8') as f:
                    targets = [line.strip() for line in f if line.strip()]
                if targets:
                    self.pyocd_target_combo.addItems(targets)
                    self._pyocd_targets_loaded = True
                    if self.last_pyocd_target:
                        self.pyocd_target_combo.setCurrentText(self.last_pyocd_target)
                    if self.log_service:
                        self.log_service.debug(f'从文件加载 {len(targets)} 个PyOCD目标')
                    return
            except Exception as e:
                if self.log_service:
                    self.log_service.warning(f'读取PyOCD目标文件失败: {e}')

        self._pyocd_targets_loaded = True

    def _update_pyocd_targets_from_pack(self):
        """从PyOCD Pack读取目标列表"""
        try:
            from ..utils.resource_utils import sync_pyocd_yaml
            updated, pack_count, yaml_path = sync_pyocd_yaml()
            if updated and self.log_service:
                self.log_service.info(f'pyocd.yaml 已同步: {pack_count} 个Pack')
            elif pack_count == 0 and self.log_service:
                self.log_service.warning('packs 目录为空，请添加 .pack 文件后刷新')
        except Exception as e:
            if self.log_service:
                self.log_service.warning(f'pyocd.yaml 同步失败: {e}')

        targets = []
        try:
            import os
            import sys
            import pyocd
            from pyocd.core import targets as pyocd_targets
            from ..utils.resource_utils import get_exe_dir
            packs_dir = os.path.join(get_exe_dir(), 'packs')
            if os.path.isdir(packs_dir):
                import glob as _glob
                pack_files = sorted(_glob.glob(os.path.join(packs_dir, '*.pack')))
                if pack_files:
                    from pyocd.pack.pack_target import PackTarget
                    for pf in pack_files:
                        try:
                            PackTarget.add_pack_from_file(pf)
                        except Exception:
                            pass
            targets = sorted(pyocd_targets.TARGET.keys())
        except Exception:
            pass

        if not targets and not getattr(sys, 'frozen', False):
            try:
                import subprocess
                import shutil
                pyocd_exe = None
                for cmd in ['pyocd']:
                    if os.path.isfile(cmd) or shutil.which(cmd):
                        pyocd_exe = cmd
                        break
                if not pyocd_exe:
                    raise FileNotFoundError('pyocd 可执行文件未找到，请确认已安装 PyOCD 并加入 PATH')
                result = subprocess.run(
                    [pyocd_exe, 'list', '--targets'],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith('#') and not line.startswith('-'):
                            parts = line.split()
                            if parts:
                                target_name = parts[0]
                                if target_name and target_name not in targets:
                                    targets.append(target_name)
            except Exception as e:
                if self.log_service:
                    self.log_service.warning(f'从Pack加载PyOCD目标失败: {e}')

        if targets:
            self.pyocd_target_combo.clear()
            self.pyocd_target_combo.addItems(targets)
            self._save_pyocd_targets(targets)
            if self.log_service:
                self.log_service.success(f'从Pack加载 {len(targets)} 个PyOCD目标')
            return

        # 回退：添加常用目标
        common_targets = [
            'cortex_m',
            'R7KA8P1KF',
            'R7FA6M5AF',
            'R7FA4M2AB',
            'stm32f407vg',
            'nrf52840',
        ]
        self.pyocd_target_combo.addItems(common_targets)

    def _save_pyocd_targets(self, targets):
        """保存PyOCD目标列表到文件"""
        from ..utils.resource_utils import get_exe_dir
        import os

        targets_file = os.path.join(get_exe_dir(), 'pyocd_targets.txt')
        try:
            with open(targets_file, 'w', encoding='utf-8') as f:
                for target in targets:
                    f.write(target + '\n')
            if self.log_service:
                self.log_service.debug(f'已保存 {len(targets)} 个PyOCD目标到 {targets_file}')
        except Exception as e:
            if self.log_service:
                self.log_service.warning(f'保存PyOCD目标文件失败: {e}')

    def _on_update_pyocd_targets(self):
        """更新PyOCD目标列表按钮点击"""
        self.pyocd_target_combo.clear()
        self.pyocd_target_combo.addItem("正在更新...")
        self.pyocd_target_combo.setEnabled(False)

        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, self._update_pyocd_targets_from_pack)

        # 恢复状态
        QTimer.singleShot(500, lambda: self.pyocd_target_combo.setEnabled(True))
    
    def _create_connection_group(self):
        """创建连接方式选择组"""
        group = QGroupBox("步骤2: 连接方式")
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
        group = QGroupBox("步骤3: 目标设备")
        layout = QVBoxLayout(group)

        # J-Link 目标设备行
        jlink_layout = QHBoxLayout()
        self.jlink_device_label = QLabel("J-Link 目标设备:")
        jlink_layout.addWidget(self.jlink_device_label)

        self.device_combo = QComboBox()
        self.device_combo.setEditable(True)
        self._device_list_loaded = False
        self.device_combo.addItem(self.last_device or "Cortex-M4")
        jlink_layout.addWidget(self.device_combo)

        self.browse_btn = QPushButton("...")
        self.browse_btn.setFixedWidth(30)
        self.browse_btn.setToolTip("筛选设备型号")
        self.browse_btn.clicked.connect(self._on_browse_device)
        jlink_layout.addWidget(self.browse_btn)

        self.update_btn = QPushButton("更新")
        self.update_btn.setFixedWidth(40)
        self.update_btn.setToolTip("从J-Link DLL更新设备列表到devices.txt")
        self.update_btn.clicked.connect(self._on_update_devices)
        jlink_layout.addWidget(self.update_btn)

        jlink_layout.addStretch()
        layout.addLayout(jlink_layout)

        # PyOCD 目标设备行
        pyocd_layout = QHBoxLayout()
        self.pyocd_device_label = QLabel("其他Link 目标设备:")
        pyocd_layout.addWidget(self.pyocd_device_label)

        self.pyocd_target_combo = QComboBox()
        self.pyocd_target_combo.setEditable(True)
        self.pyocd_target_combo.setMinimumWidth(200)
        self.pyocd_target_combo.setToolTip("PyOCD目标类型名称")
        self._pyocd_targets_loaded = False
        if self.last_pyocd_target:
            self.pyocd_target_combo.setCurrentText(self.last_pyocd_target)
        pyocd_layout.addWidget(self.pyocd_target_combo)

        self.pyocd_browse_btn = QPushButton("...")
        self.pyocd_browse_btn.setFixedWidth(30)
        self.pyocd_browse_btn.setToolTip("筛选PyOCD目标设备")
        self.pyocd_browse_btn.clicked.connect(self._on_browse_pyocd_target)
        pyocd_layout.addWidget(self.pyocd_browse_btn)

        self.pyocd_update_btn = QPushButton("更新")
        self.pyocd_update_btn.setFixedWidth(40)
        self.pyocd_update_btn.setToolTip("从PyOCD Pack更新目标列表")
        self.pyocd_update_btn.clicked.connect(self._on_update_pyocd_targets)
        pyocd_layout.addWidget(self.pyocd_update_btn)

        pyocd_layout.addStretch()
        layout.addLayout(pyocd_layout)

        # 默认显示 J-Link 设备选择
        self._update_device_ui_for_backend('jlink')

        return group
    
    def _create_interface_group(self):
        """创建接口和速度设置组"""
        group = QGroupBox("步骤4: 接口设置")
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

        layout.addSpacing(20)

        layout.addWidget(QLabel("连接模式:"))
        self.connect_mode_combo = QComboBox()
        self.connect_mode_combo.addItems([
            "under_reset",
            "halt_on_connect",
            "pre_reset",
            "default",
        ])
        self.connect_mode_combo.setCurrentText(self.connect_mode if self.connect_mode else "under_reset")
        self.connect_mode_combo.setToolTip(
            "under_reset: 复位状态下连接(推荐)\n"
            "halt_on_connect: 连接后立即暂停\n"
            "pre_reset: 连接前复位\n"
            "default: 默认模式"
        )
        layout.addWidget(self.connect_mode_combo)

        return group
    
    def _create_rtt_group(self):
        """创建RTT控制块设置组"""
        group = QGroupBox("步骤5: RTT控制块")
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
        self.address_edit.setPlaceholderText("如: 0x22002848 或从map文件搜索")
        if self.last_rtt_address:
            self.address_edit.setText(self.last_rtt_address)
        address_layout.addWidget(self.address_edit)

        address_layout.addStretch()
        layout.addLayout(address_layout)
        
        # Map文件搜索组
        map_group = QGroupBox("Map文件搜索")
        map_group_layout = QHBoxLayout(map_group)
        
        self.open_map_btn = QPushButton("打开map文件")
        self.open_map_btn.setFixedHeight(24)
        self.open_map_btn.setEnabled(False)
        self.open_map_btn.clicked.connect(self._on_open_map_file)
        map_group_layout.addWidget(self.open_map_btn)
        
        self.map_path_edit = QLineEdit()
        self.map_path_edit.setPlaceholderText("map文件路径（可手动编辑）")
        self.map_path_edit.setFixedWidth(250)
        if self.map_file_path:
            self.map_path_edit.setText(self.map_file_path)
        self.map_path_edit.textChanged.connect(self._on_map_path_changed)
        map_group_layout.addWidget(self.map_path_edit)
        
        self.search_map_btn = QPushButton("搜索_SEGGER_RTT")
        self.search_map_btn.setFixedHeight(24)
        self.search_map_btn.setEnabled(False)
        self.search_map_btn.clicked.connect(self._on_search_map_file)
        map_group_layout.addWidget(self.search_map_btn)
        
        layout.addWidget(map_group)
        
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
        
        self.auto_fill_btn = QPushButton("获取自动检测地址")
        self.auto_fill_btn.setFixedHeight(24)
        self.auto_fill_btn.setEnabled(False)
        self.auto_fill_btn.clicked.connect(self._on_auto_fill_range)
        range_layout.addWidget(self.auto_fill_btn)
        
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
        device_names, _ = self._device_info_service.load_device_list()
        return device_names
    
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
    
    def _on_browse_pyocd_target(self):
        """浏览PyOCD目标 - 打开筛选对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("PyOCD目标设备筛选")
        dialog.setMinimumSize(400, 500)

        layout = QVBoxLayout(dialog)

        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("搜索:"))
        search_edit = QLineEdit()
        search_edit.setPlaceholderText("输入关键字筛选")
        search_layout.addWidget(search_edit)
        layout.addLayout(search_layout)

        from PyQt5.QtWidgets import QListWidget
        target_list_widget = QListWidget()

        targets = [self.pyocd_target_combo.itemText(i) for i in range(self.pyocd_target_combo.count())]
        target_list_widget.addItems(targets)
        layout.addWidget(target_list_widget)

        def filter_targets(text):
            target_list_widget.clear()
            filtered = [t for t in targets if text.lower() in t.lower()]
            target_list_widget.addItems(filtered)

        search_edit.textChanged.connect(filter_targets)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        if dialog.exec_() == QDialog.Accepted:
            current_item = target_list_widget.currentItem()
            if current_item:
                self.pyocd_target_combo.setCurrentText(current_item.text())
    
    def _on_update_devices(self):
        """从J-Link DLL更新设备列表到devices.txt"""
        from PyQt5.QtWidgets import QMessageBox, QProgressDialog, QApplication
        from PyQt5.QtCore import Qt
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
        
        progress = None
        num_devices = [0]
        
        def progress_cb(current, total):
            nonlocal progress
            if total > 0 and progress is None:
                num_devices[0] = total
                progress = QProgressDialog(f"正在从DLL读取{total}个设备...", "取消", 0, total, self)
                progress.setWindowTitle("更新设备列表")
                progress.setWindowModality(Qt.WindowModal)
                progress.setMinimumDuration(0)
                progress.show()
            if progress is not None:
                progress.setValue(current)
                QApplication.processEvents()
                return progress.wasCanceled()
            return False
        
        try:
            device_names, _ = self._device_info_service.update_device_list(
                dll_path, progress_callback=progress_cb
            )
            
            if progress is not None:
                progress.setValue(num_devices[0])
            
            if not device_names:
                err_msg = "未能从DLL读取到设备列表"
                if self.log_service:
                    self.log_service.error(f"更新设备列表失败: {err_msg}")
                QMessageBox.warning(self, "错误", err_msg)
                return
            
            self.device_combo.clear()
            self.device_combo.addItems(device_names)
            self.device_combo.setCurrentText(self.last_device)
            
            devices_file = os.path.join(get_exe_dir(), "devices.txt")
            if self.log_service:
                self.log_service.success(f"设备列表已更新: {len(device_names)}个设备, 保存至{devices_file}")
            QMessageBox.information(self, "完成", f"已更新设备列表: {len(device_names)}个设备\n保存至: {devices_file}")
            
        except Exception as e:
            if progress is not None:
                progress.setValue(num_devices[0])
            err_msg = f"更新设备列表失败: {e}"
            if self.log_service:
                self.log_service.error(err_msg)
            QMessageBox.warning(self, "错误", err_msg)
    
    def _on_rtt_mode_changed(self):
        """RTT模式变化"""
        is_jlink = getattr(self, '_current_backend', 'jlink') == 'jlink'
        is_address = self.address_radio.isChecked()
        is_range = self.range_radio.isChecked()
        self.range_start_edit.setEnabled(is_range)
        self.range_size_edit.setEnabled(is_range)
        self.auto_fill_btn.setEnabled(is_jlink and is_range)
        self.open_map_btn.setEnabled(is_address)
        self.search_map_btn.setEnabled(is_address and bool(self.map_file_path))

    def _on_map_path_changed(self, text):
        """Map文件路径变化"""
        self.map_file_path = text.strip()
        self.search_map_btn.setEnabled(self.address_radio.isChecked() and bool(self.map_file_path))
    
    def _on_auto_fill_range(self):
        """自动填充搜索范围"""
        device_name = self.device_combo.currentText().strip()
        if not device_name:
            if self.log_service:
                self.log_service.warning("自动填充失败: 未选择设备")
            QMessageBox.warning(self, "提示", "请先选择设备型号")
            return
        
        device_info = self._device_info_service.get_device_info(device_name)
        if device_info is None:
            if self.log_service:
                self.log_service.warning(f"自动填充失败: 设备 '{device_name}' 信息不存在")
            QMessageBox.warning(self, "提示", f"设备 '{device_name}' 的信息不存在")
            return
        
        ram_addr = device_info.extra_attrs.get("RAMAddr", "")
        ram_size = device_info.ram_size
        
        if not ram_addr or ram_addr == "0":
            if self.log_service:
                self.log_service.warning(f"自动填充失败: 设备 '{device_name}' 无有效RAMAddr")
            QMessageBox.warning(self, "提示", f"设备 '{device_name}' 无有效的RAM地址信息")
            return
        
        if ram_size <= 0:
            if self.log_service:
                self.log_service.warning(f"自动填充失败: 设备 '{device_name}' 无有效ram_size")
            QMessageBox.warning(self, "提示", f"设备 '{device_name}' 无有效的RAM大小信息")
            return
        
        try:
            addr_value = int(ram_addr, 16) if isinstance(ram_addr, str) else int(ram_addr)
            self.range_start_edit.setText(f"0x{addr_value:08X}")
            self.range_size_edit.setText(f"0x{ram_size:X}")
            
            if self.log_service:
                self.log_service.success(f"自动填充成功: RAMAddr=0x{addr_value:08X}, ram_size=0x{ram_size:X}")
        except Exception as e:
            if self.log_service:
                self.log_service.error(f"自动填充失败: 格式转换错误 - {e}")
            QMessageBox.warning(self, "错误", f"填充失败: {e}")
    
    def _on_open_map_file(self):
        """打开map文件选择对话框"""
        from PyQt5.QtWidgets import QFileDialog
        from ..utils.map_file_parser import MapFileParser
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择Map文件", self.map_file_path, "Map Files (*.map);;All Files (*)"
        )
        
        if file_path:
            self.map_file_path = file_path
            self.map_path_edit.setText(file_path)
            self.search_map_btn.setEnabled(True)
            if self.log_service:
                self.log_service.info(f"已选择map文件: {file_path}")
    
    def _on_search_map_file(self):
        """从map文件搜索_SEGGER_RTT地址"""
        from ..utils.map_file_parser import MapFileParser
        
        if not self.map_file_path:
            QMessageBox.warning(self, "提示", "请先选择map文件")
            return
        
        addr, error = MapFileParser.search_symbol(self.map_file_path, self.log_service)
        
        if addr:
            self.address_edit.setText(addr)
            if self.log_service:
                self.log_service.success(f"已填充地址: {addr}")
        else:
            QMessageBox.warning(self, "搜索失败", error or "未找到_SEGGER_RTT符号")
    
    def get_config(self):
        """获取配置信息"""
        speed_str = self.speed_combo.currentText()
        speed = int(speed_str.split()[0])

        selected_probe = None
        current_item = self.probe_list.currentItem()
        if current_item is not None:
            selected_probe = current_item.data(Qt.UserRole)
        debugger_type = "jlink"
        serial_number = None
        probe_name = ""
        probe_backend = ""
        probe_serial = ""
        if selected_probe and isinstance(selected_probe, dict):
            debugger_type = selected_probe.get('backend', 'jlink')
            serial_number = selected_probe.get('serial')
            probe_name = selected_probe.get('name', '')
            probe_backend = selected_probe.get('backend', 'jlink')
            probe_serial = selected_probe.get('serial', '')

        # 独立获取两个设备名，互不影响
        jlink_device = self.device_combo.currentText().strip()
        pyocd_target = self.pyocd_target_combo.currentText().strip()

        config = {
            "debugger_type": debugger_type,
            "connection_type": "USB" if self.usb_radio.isChecked() else "TCP",
            "serial_number": serial_number or (self.sn_edit.text() if self.sn_checkbox.isChecked() else None),
            "ip_address": self.ip_edit.text() if self.tcp_radio.isChecked() else None,
            "device": jlink_device,
            "pyocd_target": pyocd_target,
            "interface": self.interface_combo.currentText(),
            "speed": speed,
            "connect_mode": self.connect_mode_combo.currentText(),
            "rtt_mode": "auto" if self.auto_radio.isChecked() else
                       "address" if self.address_radio.isChecked() else "range",
            "rtt_address": self.address_edit.text() if self.address_radio.isChecked() else None,
            "rtt_range_start": self.range_start_edit.text() if self.range_radio.isChecked() else None,
            "rtt_range_size": self.range_size_edit.text() if self.range_radio.isChecked() else None,
            "map_file_path": self.map_file_path,
            "probe_name": probe_name,
            "probe_backend": probe_backend,
            "probe_serial": probe_serial,
        }

        return config
