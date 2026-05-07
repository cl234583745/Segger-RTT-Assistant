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

"""检查JLink DLL路径"""

import os
import struct

python_bits = struct.calcsize('P') * 8
dll_name = "JLink_x64.dll" if python_bits == 64 else "JLinkARM.dll"

print("检查JLink DLL路径:")
print("-" * 60)

possible_paths = [
    os.path.join(os.getcwd(), dll_name),
]

found = False
for path in possible_paths:
    exists = os.path.exists(path)
    status = "[OK] 存在" if exists else "[X] 不存在"
    print(f"{status}: {path}")
    if exists and not found:
        found = True
        print(f"\n找到JLink DLL: {path}\n")

if not found:
    print(f"\n[ERROR] 未找到{dll_name}!")
    print(f"\n请将{dll_name}复制到程序目录")
