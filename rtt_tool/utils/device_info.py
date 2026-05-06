#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
设备信息数据模型
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


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
