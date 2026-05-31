#!/usr/bin/env python
"""构建独立pyocd.exe - 自包含的PyOCD烧录工具"""

import os
import sys
import subprocess
import shutil

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PYOCD_SPEC = os.path.join(ROOT_DIR, 'pyocd-standalone.spec')
OUTPUT_DIR = os.path.join(ROOT_DIR, 'runtime', 'pyocd')


def build_pyocd():
    print("=" * 50)
    print(" 构建独立 pyocd.exe")
    print("=" * 50)

    print("\n[1/2] PyInstaller 打包...")
    result = subprocess.run(
        [sys.executable, '-m', 'PyInstaller', '--clean', '--noconfirm', PYOCD_SPEC],
        cwd=ROOT_DIR,
    )
    if result.returncode != 0:
        print(f"\n打包失败! 返回码: {result.returncode}")
        sys.exit(1)

    print("\n[2/2] 复制到 runtime/pyocd/...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    src_exe = os.path.join(ROOT_DIR, 'dist', 'pyocd.exe')
    dst_exe = os.path.join(OUTPUT_DIR, 'pyocd.exe')

    if not os.path.isfile(src_exe):
        print(f"  错误: 未找到 {src_exe}")
        sys.exit(1)

    shutil.copy2(src_exe, dst_exe)
    size_mb = os.path.getsize(dst_exe) / 1024 / 1024
    print(f"  已复制: {dst_exe} ({size_mb:.1f}MB)")

    # 验证
    print("\n验证...")
    r = subprocess.run([dst_exe, '--version'], capture_output=True, text=True, timeout=10)
    if r.returncode == 0:
        print(f"  pyocd.exe --version: {r.stdout.strip()}")
    else:
        print(f"  警告: pyocd.exe --version 返回码 {r.returncode}")

    # 清理
    build_dir = os.path.join(ROOT_DIR, 'build')
    if os.path.isdir(build_dir):
        shutil.rmtree(build_dir, ignore_errors=True)
        print("  已清理 build/")

    print(f"\n完成! pyocd.exe 位于: {OUTPUT_DIR}")


if __name__ == '__main__':
    build_pyocd()