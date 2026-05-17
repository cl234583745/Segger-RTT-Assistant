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
设备信息数据模型
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


_JLINK_CORE_MAP = {
    0x060000FF: "Cortex-M0",   0x060100FF: "Cortex-M0+",
    0x030000FF: "Cortex-M1",
    0x070000FF: "Cortex-M3",   0x070001FF: "Cortex-M3",
    0x0E0000FF: "Cortex-M4",   0x0E0100FF: "Cortex-M7",
    0x0E0200FF: "Cortex-M33",  0x0E0300FF: "Cortex-M23",
    0x0E0400FF: "Cortex-M55",  0x0E0500FF: "Cortex-M85",
    0x0E0600FF: "Cortex-M35P", 0x0E0700FF: "Cortex-M52",
    0x0F0000FF: "Cortex-A5",   0x080000FF: "Cortex-A8",
    0x080800FF: "Cortex-A9",   0x080900FF: "Cortex-A9",
    0x080A00FF: "Cortex-A7",   0x080B00FF: "Cortex-A15",
    0x080C00FF: "Cortex-A12",  0x092000FF: "Cortex-A53",
    0x092601FF: "Cortex-A57",  0x094601FF: "Cortex-A53",
    0x096601FF: "Cortex-A72",  0x096801FF: "Cortex-A73",
    0x09FFFFFF: "Cortex-R4",   0x07B00053: "Cortex-R5",
    0x07C1C01D: "Cortex-R7",   0x07C2901D: "Cortex-R8",
    0x0D04FFFF: "RV32I",       0x0D03FFFF: "RV32IMC",
    0x0D30FFFF: "RV32IMAC",   0x0D0FFFFF: "RV64I",
    0x13FFFFFF: "N25 (Andes)", 0x11FFFFFF: "AndesCore",
    0x1100FFFF: "AndesCore",   0x1101FFFF: "AndesCore",
    0x1102FFFF: "AndesCore",   0x1200FFFF: "AndesCore",
    0x10FF00FF: "Cortex-M0",   0x10FF01FF: "Cortex-M0+",
}


_JLINK_COREID_MAP = {
    0x0BA01477: "Cortex-M4",   0x0BA04477: "Cortex-M4",
    0x0BB11477: "Cortex-M4",   0x0BC11477: "Cortex-M4",
    0x0BC12477: "Cortex-M4",   0x0BD11477: "Cortex-M4",
    0x05968489: "Cortex-M0+",  0x0596802B: "Cortex-M0+",
    0x05946041: "Cortex-M0",
    0x0BA00477: "Cortex-M3",   0x0B000477: "Cortex-M3",
    0x0B6D602F: "Cortex-M7",
    0x2BA01477: "Cortex-M4",
    0x6BA02477: "Cortex-M33",
}


def decode_jlink_core(core_str: str) -> str:
    if not core_str or not core_str.startswith('0x'):
        return core_str
    try:
        val = int(core_str, 16)
        name = _JLINK_CORE_MAP.get(val)
        if name:
            return name
        impl = (val >> 24) & 0xFF
        arch = (val >> 16) & 0xFF
        impl_names = {0x06: 'ARM', 0x0E: 'ARM', 0x03: 'ARM', 0x0D: 'RISC-V', 0x13: 'Andes', 0x14: 'RISC-V'}
        impl_name = impl_names.get(impl, f'0x{impl:02X}')
        return f"{impl_name} arch=0x{arch:02X}"
    except (ValueError, TypeError):
        return core_str


def decode_jlink_coreid(coreid_str: str) -> str:
    if not coreid_str or coreid_str == '0':
        return ''
    if not coreid_str.startswith('0x'):
        return coreid_str
    try:
        val = int(coreid_str, 16)
        name = _JLINK_COREID_MAP.get(val)
        if name:
            return name
        return coreid_str
    except (ValueError, TypeError):
        return coreid_str


@dataclass
class DeviceInfo:
    name: str
    family: str = ""
    core: str = ""
    flash_size: int = 0
    ram_size: int = 0
    extra_attrs: Dict[str, Any] = field(default_factory=dict)

    def to_file_line(self) -> str:
        parts = [self.name]
        if self.family:
            parts.append(f"family={self.family}")
        if self.core:
            parts.append(f"core={self.core}")
        if self.flash_size > 0:
            parts.append(f"flash_size={self.flash_size}")
        if self.ram_size > 0:
            parts.append(f"ram_size={self.ram_size}")
        for key, val in self.extra_attrs.items():
            if val is not None and val != "" and val != 0:
                parts.append(f"{key}={val}")
        return "|".join(parts)

    @classmethod
    def from_file_line(cls, line: str) -> Optional["DeviceInfo"]:
        if not line or line.startswith("#"):
            return None
        if "|" not in line:
            return cls(name=line.strip())
        parts = line.split("|")
        name = parts[0].strip()
        if not name:
            return None
        info = cls(name=name)
        for part in parts[1:]:
            if "=" in part:
                key, _, val = part.partition("=")
                key = key.strip()
                val = val.strip()
                info._set_attr(key, val)
        return info

    def _set_attr(self, key: str, val_str: str):
        typed_attrs = {
            "family": lambda v: v,
            "core": lambda v: v,
            "flash_size": lambda v: int(v) if v.isdigit() else 0,
            "ram_size": lambda v: int(v) if v.isdigit() else 0,
        }
        if key in typed_attrs:
            try:
                setattr(self, key, typed_attrs[key](val_str))
            except (ValueError, TypeError):
                pass
        else:
            self.extra_attrs[key] = val_str

    def to_log_string(self) -> str:
        parts = [f"name={self.name}"]
        if self.family:
            parts.append(f"family={self.family}")
        if self.core:
            parts.append(f"core={self.core}")
        if self.flash_size > 0:
            parts.append(f"flash_size={self.flash_size}")
        if self.ram_size > 0:
            parts.append(f"ram_size={self.ram_size}")
        for key, val in self.extra_attrs.items():
            if val is not None and val != "" and val != 0:
                parts.append(f"{key}={val}")
        return " | ".join(parts)
