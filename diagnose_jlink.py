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

# 1. 检查Python环境
print("\n[1] Python环境信息:")
print("-" * 70)
print(f"Python版本: {sys.version}")
print(f"Python路径: {sys.executable}")
python_bits = struct.calcsize('P') * 8
print(f"Python位数: {python_bits}位")
print(f"Python架构: {'x64' if python_bits == 64 else 'x86'}")

# 2. 检查JLink安装路径
print("\n[2] JLink安装路径检查:")
print("-" * 70)

# 常见JLink安装路径
possible_paths = [
    r"D:\Program Files\SEGGER\JLink_V938a",
    r"C:\Program Files\SEGGER\JLink_V938a",
    r"D:\Program Files\SEGGER\JLink_V930",
    r"C:\Program Files\SEGGER\JLink_V930",
    r"C:\Program Files (x86)\SEGGER\JLink_V930",
    r"D:\Program Files\SEGGER\JLink_V940",
    r"C:\Program Files\SEGGER\JLink_V940",
    r"C:\Program Files (x86)\SEGGER\JLink_V940",
    r"D:\Program Files\SEGGER\JLink_V950",
    r"C:\Program Files\SEGGER\JLink_V950",
    r"C:\Program Files (x86)\SEGGER\JLink_V950",
]

jlink_dirs = []
for path in possible_paths:
    if os.path.exists(path):
        print(f"[OK] 找到: {path}")
        jlink_dirs.append(path)
    else:
        print(f"[--] 不存在: {path}")

# 3. 检查JLinkARM.dll
print("\n[3] JLink DLL检查:")
print("-" * 70)

# 根据Python位数选择DLL名称
dll_name = "JLink_x64.dll" if python_bits == 64 else "JLinkARM.dll"
print(f"目标DLL: {dll_name} (根据Python {python_bits}位自动选择)")

dll_files = []
for jlink_dir in jlink_dirs:
    dll_path = os.path.join(jlink_dir, dll_name)
    if os.path.exists(dll_path):
        print(f"[OK] 找到DLL: {dll_path}")
        dll_files.append(dll_path)
        
        # 检查DLL位数
        try:
            import pefile
            pe = pefile.PE(dll_path)
            dll_bits = 64 if pe.OPTIONAL_HEADER.Magic == 0x20b else 32
            print(f"    DLL位数: {dll_bits}位")
            
            if dll_bits != python_bits:
                print(f"    [ERROR] 位数不匹配! Python是{python_bits}位, DLL是{dll_bits}位")
                print(f"    [建议] 请安装{'64位' if python_bits == 64 else '32位'}版本的JLink")
            else:
                print(f"    [OK] 位数匹配")
        except ImportError:
            print(f"    [WARNING] pefile未安装,无法检查DLL位数")
            print(f"    [建议] 运行: pip install pefile")
        except Exception as e:
            print(f"    [ERROR] 检查DLL位数失败: {e}")
    else:
        print(f"[--] DLL不存在: {dll_path}")

# 4. 检查环境变量
print("\n[4] 环境变量检查:")
print("-" * 70)
jlink_path_env = os.environ.get('JLINK_PATH', '')
if jlink_path_env:
    print(f"[OK] JLINK_PATH: {jlink_path_env}")
else:
    print("[--] JLINK_PATH未设置")

path_env = os.environ.get('PATH', '')
jlink_in_path = False
for path_dir in path_env.split(os.pathsep):
    if 'SEGGER' in path_dir.upper() or 'JLINK' in path_dir.upper():
        print(f"[OK] PATH中找到JLink: {path_dir}")
        jlink_in_path = True

if not jlink_in_path:
    print("[--] PATH中未找到JLink路径")

# 5. 测试pylink库
print("\n[5] pylink库测试:")
print("-" * 70)

try:
    import pylink
    print(f"[OK] pylink已安装")
    print(f"    版本: {pylink.__version__ if hasattr(pylink, '__version__') else '未知'}")
    
    # 测试加载DLL
    if dll_files:
        from pylink import library
        
        for dll_path in dll_files:
            print(f"\n    测试加载: {dll_path}")
            try:
                lib = library.Library(dllpath=dll_path)
                jlink = pylink.JLink(lib=lib)
                print(f"    [OK] 加载成功!")
                print(f"    JLink版本: {jlink.version}")
                break
            except Exception as e:
                print(f"    [ERROR] 加载失败: {e}")
    else:
        print("[WARNING] 未找到JLinkARM.dll,无法测试加载")
        
except ImportError as e:
    print(f"[ERROR] pylink未安装: {e}")
    print("[建议] 运行: pip install pylink-square")
except Exception as e:
    print(f"[ERROR] pylink测试失败: {e}")

# 6. 总结和建议
print("\n" + "=" * 70)
print("诊断总结:")
print("=" * 70)

if not dll_files:
    print("\n[问题] 未找到JLinkARM.dll")
    print("\n[解决方案]:")
    print("1. 下载并安装JLink软件: https://www.segger.com/downloads/jlink/")
    print(f"2. 确保安装{'64位' if python_bits == 64 else '32位'}版本")
    print("3. 安装后重新运行此诊断工具")
else:
    # 检查是否有位数匹配的DLL
    matched = False
    try:
        import pefile
        for dll_path in dll_files:
            pe = pefile.PE(dll_path)
            dll_bits = 64 if pe.OPTIONAL_HEADER.Magic == 0x20b else 32
            if dll_bits == python_bits:
                matched = True
                break
    except:
        pass
    
    if not matched:
        print(f"\n[问题] JLink DLL位数与Python不匹配")
        print(f"  Python: {python_bits}位")
        print(f"  JLink DLL: {dll_bits}位")
        print("\n[解决方案]:")
        print(f"1. 卸载当前JLink软件")
        print(f"2. 下载并安装{'64位' if python_bits == 64 else '32位'}版本的JLink")
        print("   下载地址: https://www.segger.com/downloads/jlink/")
        print("3. 安装后重新运行此诊断工具")
    else:
        print("\n[OK] JLink配置正常!")
        print("如果仍然无法连接,请检查:")
        print("1. JLink硬件是否正确连接")
        print("2. MCU是否已上电")
        print("3. 接口类型(SWD/JTAG)是否正确")

print("\n" + "=" * 70)
