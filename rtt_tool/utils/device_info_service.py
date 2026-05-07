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
设备信息服务
负责设备完整信息的读取、解析、持久化
"""

import os
from typing import List, Dict, Tuple, Optional, Any, Callable

from .device_info import DeviceInfo
from .resource_utils import get_exe_dir, get_external_file


_CORE_ATTR_MAP = {
    "name": "name",
    "manufacturer": "family",
    "Core": "core",
    "FlashSize": "flash_size",
    "RAMSize": "ram_size",
}

_EXTRA_ATTRS = ["CoreId", "FlashAddr", "RAMAddr", "EndianMode"]

_SKIP_ATTRS = {
    "SizeofStruct", "sName", "sManu",
    "aFlashArea", "aRAMArea",
}

_DEFAULT_DEVICES = [
    "Cortex-M0", "Cortex-M0+", "Cortex-M1", "Cortex-M3",
    "Cortex-M4", "Cortex-M7",
    "STM32F103", "STM32F407", "STM32H743",
    "NRF52832", "NRF52840",
    "R9A07G084M04",
]


class DeviceInfoService:
    def __init__(self, log_service=None):
        self._log_service = log_service
        self._device_info_map: Dict[str, DeviceInfo] = {}
        self._cached_attr_names: Optional[List[str]] = None

    def _discover_device_attrs(self, sample_device_obj) -> List[str]:
        if self._cached_attr_names is not None:
            return self._cached_attr_names

        core_attrs = list(_CORE_ATTR_MAP.keys())
        extra_known = list(_EXTRA_ATTRS)

        dynamic_attrs = []
        for attr_name in dir(sample_device_obj):
            if attr_name.startswith("_"):
                continue
            if attr_name in core_attrs or attr_name in extra_known or attr_name in _SKIP_ATTRS:
                continue
            try:
                val = getattr(sample_device_obj, attr_name)
                if not callable(val):
                    dynamic_attrs.append(attr_name)
            except Exception:
                continue

        self._cached_attr_names = core_attrs + extra_known + sorted(dynamic_attrs)
        return self._cached_attr_names

    def _extract_device_info(self, device_obj, attr_names: List[str]) -> Optional[DeviceInfo]:
        info = DeviceInfo(name="")

        for attr_name in attr_names:
            try:
                val = getattr(device_obj, attr_name)
            except Exception:
                val = None

            mapped = _CORE_ATTR_MAP.get(attr_name)
            if mapped:
                if mapped == "name":
                    if not val:
                        return None
                    info.name = str(val)
                elif mapped == "family":
                    info.family = str(val) if val else ""
                elif mapped == "core":
                    try:
                        if isinstance(val, int):
                            info.core = f"0x{val:08X}" if val else ""
                        else:
                            info.core = str(val) if val else ""
                    except Exception:
                        info.core = ""
                elif mapped == "flash_size":
                    try:
                        info.flash_size = int(val) if val and isinstance(val, (int, float)) else 0
                    except Exception:
                        info.flash_size = 0
                elif mapped == "ram_size":
                    try:
                        info.ram_size = int(val) if val and isinstance(val, (int, float)) else 0
                    except Exception:
                        info.ram_size = 0
            else:
                if val is not None:
                    try:
                        if isinstance(val, bytes):
                            val = val.decode('utf-8', errors='replace')
                        elif isinstance(val, int) and attr_name in ("FlashAddr", "RAMAddr", "CoreId"):
                            val = f"0x{val:08X}" if val else "0"
                        str_val = str(val)
                        info.extra_attrs[attr_name] = str_val
                    except Exception:
                        pass

        if not info.name:
            return None
        return info

    def update_device_list(
        self, dll_path: str, progress_callback: Optional[Callable[[int, int], bool]] = None
    ) -> Tuple[List[str], Dict[str, DeviceInfo]]:
        import ctypes
        import pylink
        from pylink import library, structs

        try:
            jlink_lib = library.Library(dllpath=dll_path)
            dll = jlink_lib.dll()

            num_devices = int(dll.JLINKARM_DEVICE_GetInfo(-1, 0))

            if self._log_service:
                self._log_service.info(f"开始从DLL读取设备列表, 共{num_devices}个设备")

            if progress_callback:
                progress_callback(0, num_devices)

            attr_names = None
            device_info_list: List[DeviceInfo] = []

            for i in range(num_devices):
                if progress_callback and i % 200 == 0:
                    if progress_callback(i, num_devices):
                        break
                try:
                    dev_info = structs.JLinkDeviceInfo()
                    dll.JLINKARM_DEVICE_GetInfo(i, ctypes.byref(dev_info))
                    if attr_names is None:
                        attr_names = self._discover_device_attrs(dev_info)
                    info = self._extract_device_info(dev_info, attr_names)
                    if info:
                        device_info_list.append(info)
                except Exception:
                    pass

            device_info_list.sort(key=lambda x: x.name)

            self._write_devices_file(device_info_list)

            self._device_info_map = {info.name: info for info in device_info_list}
            device_names = [info.name for info in device_info_list]

            return device_names, self._device_info_map
        except Exception as e:
            raise RuntimeError(f"更新设备列表失败: {e}")

    def _write_devices_file(self, device_info_list: List[DeviceInfo]) -> bool:
        try:
            devices_file = os.path.join(get_exe_dir(), "devices.txt")
            with open(devices_file, "w", encoding="utf-8") as f:
                f.write("# format: v2\n")
                f.write("# RTT Assistant - 支持的设备型号列表\n")
                f.write(f"# 从J-Link DLL自动生成, 共{len(device_info_list)}个设备\n")
                f.write("#\n")
                for info in device_info_list:
                    f.write(info.to_file_line() + "\n")
            return True
        except Exception as e:
            if self._log_service:
                self._log_service.error(f"写入devices.txt失败: {e}")
            return False

    def _parse_devices_file(self) -> Tuple[List[str], Dict[str, DeviceInfo]]:
        ext_file = get_external_file("devices.txt")
        if not ext_file or not os.path.exists(ext_file):
            return [], {}

        try:
            device_names = []
            device_info_map = {}
            with open(ext_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    info = DeviceInfo.from_file_line(line)
                    if info and info.name:
                        device_names.append(info.name)
                        device_info_map[info.name] = info
            return device_names, device_info_map
        except Exception as e:
            if self._log_service:
                self._log_service.warning(f"解析devices.txt失败: {e}")
            return [], {}

    def load_device_list(self) -> Tuple[List[str], Dict[str, DeviceInfo]]:
        device_names, device_info_map = self._parse_devices_file()

        if not device_names:
            device_names = list(_DEFAULT_DEVICES)
            device_info_map = {name: DeviceInfo(name=name) for name in _DEFAULT_DEVICES}

        self._device_info_map = device_info_map
        return device_names, device_info_map

    def get_device_info(self, device_name: str) -> Optional[DeviceInfo]:
        if device_name in self._device_info_map:
            return self._device_info_map[device_name]
        self.load_device_list()
        return self._device_info_map.get(device_name)

    def format_device_log(self, device_info: Optional[DeviceInfo], device_name: str) -> str:
        if device_info is not None:
            return f"[设备信息] {device_info.to_log_string()}"
        return f"[设备信息] name={device_name} (完整信息不可用)"
