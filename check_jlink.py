#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查JLink DLL路径"""

import os

# 常见JLink安装路径
possible_paths = [
    r"D:\Program Files\SEGGER\JLink_V930\JLinkARM.dll",
    r"C:\Program Files\SEGGER\JLink_V930\JLinkARM.dll",
    r"C:\Program Files (x86)\SEGGER\JLink_V930\JLinkARM.dll",
    r"D:\Program Files\SEGGER\JLink_V940\JLinkARM.dll",
    r"C:\Program Files\SEGGER\JLink_V940\JLinkARM.dll",
    r"C:\Program Files (x86)\SEGGER\JLink_V940\JLinkARM.dll",
    r"D:\Program Files\SEGGER\JLink_V950\JLinkARM.dll",
    r"C:\Program Files\SEGGER\JLink_V950\JLinkARM.dll",
    r"C:\Program Files (x86)\SEGGER\JLink_V950\JLinkARM.dll",
]

print("检查JLink DLL路径:")
print("-" * 60)

found = False
for path in possible_paths:
    exists = os.path.exists(path)
    status = "[OK] 存在" if exists else "[X] 不存在"
    print(f"{status}: {path}")
    if exists and not found:
        found = True
        print(f"\n找到JLink DLL: {path}\n")

# 检查PATH环境变量
print("\n检查PATH环境变量中的JLink:")
print("-" * 60)
path_env = os.environ.get('PATH', '')
for path_dir in path_env.split(os.pathsep):
    if 'SEGGER' in path_dir.upper() or 'JLINK' in path_dir.upper():
        dll_path = os.path.join(path_dir, 'JLinkARM.dll')
        exists = os.path.exists(dll_path)
        status = "[OK] 存在" if exists else "[X] 不存在"
        print(f"{status}: {dll_path}")
        if exists and not found:
            found = True
            print(f"\n找到JLink DLL: {dll_path}\n")

if not found:
    print("\n[ERROR] 未找到JLinkARM.dll!")
    print("\n请确保:")
    print("1. 已安装JLink软件 (https://www.segger.com/downloads/jlink/)")
    print("2. JLink版本为V930或更高")
    print("3. 或将JLinkARM.dll复制到程序目录")
