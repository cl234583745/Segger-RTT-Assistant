#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
JLink DLL诊断工具
帮助排查JLink DLL加载问题
"""

import os
import sys
import struct

print("=" * 70)
print("JLink DLL 诊断工具")
print("=" * 70)

python_bits = struct.calcsize('P') * 8
dll_name = "JLink_x64.dll" if python_bits == 64 else "JLinkARM.dll"

# 1. 检查Python环境
print("\n[1] Python环境信息:")
print("-" * 70)
print(f"Python版本: {sys.version}")
print(f"Python路径: {sys.executable}")
print(f"Python位数: {python_bits}位")
print(f"Python架构: {'x64' if python_bits == 64 else 'x86'}")

# 2. 检查当前目录DLL
print(f"\n[2] {dll_name}检查:")
print("-" * 70)

dll_path = os.path.join(os.getcwd(), dll_name)
dll_files = []

if os.path.exists(dll_path):
    print(f"[OK] 找到DLL: {dll_path}")
    dll_files.append(dll_path)
    
    try:
        import pefile
        pe = pefile.PE(dll_path)
        dll_bits = 64 if pe.OPTIONAL_HEADER.Magic == 0x20b else 32
        print(f"    DLL位数: {dll_bits}位")
        
        if dll_bits != python_bits:
            print(f"    [ERROR] 位数不匹配! Python是{python_bits}位, DLL是{dll_bits}位")
        else:
            print(f"    [OK] 位数匹配")
    except ImportError:
        print(f"    [WARNING] pefile未安装,无法检查DLL位数")
    except Exception as e:
        print(f"    [ERROR] 检查DLL位数失败: {e}")
else:
    print(f"[--] 当前目录未找到: {dll_path}")

# 3. 检查环境变量
print("\n[3] 环境变量检查:")
print("-" * 70)
jlink_path_env = os.environ.get('JLINK_PATH', '')
if jlink_path_env:
    print(f"[OK] JLINK_PATH: {jlink_path_env}")
else:
    print("[--] JLINK_PATH未设置")

# 4. 测试pylink库
print("\n[4] pylink库测试:")
print("-" * 70)

try:
    import pylink
    print(f"[OK] pylink已安装")
    
    if dll_files:
        from pylink import library
        
        for dll in dll_files:
            print(f"\n    测试加载: {dll}")
            try:
                lib = library.Library(dllpath=dll)
                jlink = pylink.JLink(lib=lib)
                print(f"    [OK] 加载成功!")
                print(f"    JLink版本: {jlink.version}")
                break
            except Exception as e:
                print(f"    [ERROR] 加载失败: {e}")
    else:
        print(f"[WARNING] 未找到{dll_name},无法测试加载")
        
except ImportError as e:
    print(f"[ERROR] pylink未安装: {e}")
    print("[建议] 运行: pip install pylink-square")

# 5. 总结
print("\n" + "=" * 70)
print("诊断总结:")
print("=" * 70)

if not dll_files:
    print(f"\n[问题] 未找到{dll_name}")
    print(f"\n[解决方案]:")
    print(f"1. 将{dll_name}复制到程序目录")
    print(f"2. 确保DLL为{'64位' if python_bits == 64 else '32位'}版本")
else:
    print("\n[OK] JLink配置正常!")
    print("如果仍然无法连接,请检查:")
    print("1. JLink硬件是否正确连接")
    print("2. MCU是否已上电")
    print("3. 接口类型(SWD/JTAG)是否正确")

print("\n" + "=" * 70)
