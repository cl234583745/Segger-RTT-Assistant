#!/usr/bin/env python
# -*- coding: utf-8 -*-
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
