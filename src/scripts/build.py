#!/usr/bin/env python
"""打包脚本 - 生成独立exe（包含pyocd和packs）"""

import os
import sys
import shutil
import subprocess
import glob

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


def check_dependencies():
    """检查打包依赖"""
    required = {
        'PyInstaller': 'PyInstaller',
        'pyocd': 'pyocd',
        'usb1': 'usb1',
        'PyQt5': 'PyQt5',
        'pyqtgraph': 'pyqtgraph',
    }
    missing = []
    for pkg_name, import_name in required.items():
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pkg_name)
    if missing:
        print(f"缺少依赖: {', '.join(missing)}")
        print(f"请执行: pip install {' '.join(missing)}")
        sys.exit(1)


def ensure_packs_dir():
    """确保 packs 目录存在"""
    packs_dir = os.path.join(ROOT_DIR, 'packs')
    os.makedirs(packs_dir, exist_ok=True)
    pack_count = len([f for f in os.listdir(packs_dir) if f.endswith('.pack')])
    if pack_count == 0:
        print(f"\n提示: packs 目录为空，PyOCD连接需要CMSIS Pack文件。")
        print(f"  请将 .pack 文件复制到: {packs_dir}")
        print(f"  或从已安装的 e2_studio/Renesas IDE 环境中复制 packs 目录")
        print(f"  Pack下载地址: https://developer.arm.com/tools-and-software/open-source-software/developer-tools/cmsis-pack")
    else:
        print(f"已发现 {pack_count} 个 CMSIS Pack 文件")
    return pack_count


def generate_pyocd_yaml(packs_dir):
    """根据 packs 目录内容生成 pyocd.yaml"""
    pack_files = sorted(glob.glob(os.path.join(packs_dir, '*.pack')))
    lines = ['pack:']
    for pf in pack_files:
        pack_name = os.path.basename(pf)
        lines.append(f'  - ./packs/{pack_name}')
    content = '\n'.join(lines) + '\n'
    return content


def copy_runtime_files(dist_dir):
    """复制运行时外部文件到 dist 目录"""
    packs_src = os.path.join(ROOT_DIR, 'packs')
    packs_dst = os.path.join(dist_dir, 'packs')
    os.makedirs(packs_dst, exist_ok=True)
    if os.path.isdir(packs_src):
        for f in os.listdir(packs_src):
            if f.endswith('.pack'):
                shutil.copy2(os.path.join(packs_src, f), os.path.join(packs_dst, f))
        pack_count = len([f for f in os.listdir(packs_dst) if f.endswith('.pack')])
        print(f"  已复制 {pack_count} 个 Pack 文件到 dist/packs/")

    yaml_content = generate_pyocd_yaml(packs_dst)
    yaml_dst = os.path.join(dist_dir, 'pyocd.yaml')
    with open(yaml_dst, 'w', encoding='utf-8') as f:
        f.write(yaml_content)
    print(f"  已生成 pyocd.yaml (引用 {len(glob.glob(os.path.join(packs_dst, '*.pack')))} 个Pack)")

    for f in ['pyocd_targets.txt']:
        src = os.path.join(ROOT_DIR, f)
        dst = os.path.join(dist_dir, f)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"  已复制 {f}")
        else:
            with open(dst, 'w', encoding='utf-8') as fh:
                fh.write('')
            print(f"  已创建空 {f}")

    config_dir = os.path.join(ROOT_DIR, 'config')
    dist_config_dir = os.path.join(dist_dir, 'config')
    os.makedirs(dist_config_dir, exist_ok=True)
    for f in ['config.json', 'devices.txt', 'pyocd.yaml', 'pyocd_targets.txt']:
        src = os.path.join(config_dir, f)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(dist_config_dir, f))
            print(f"  已复制 config/{f}")

    resources_dir = os.path.join(ROOT_DIR, 'resources')
    dist_resources_dir = os.path.join(dist_dir, 'resources')
    if os.path.isdir(resources_dir):
        os.makedirs(dist_resources_dir, exist_ok=True)
        for f in os.listdir(resources_dir):
            shutil.copy2(os.path.join(resources_dir, f), os.path.join(dist_resources_dir, f))
            print(f"  已复制 resources/{f}")

    for dll in glob.glob(os.path.join(ROOT_DIR, 'JLink*.dll')):
        shutil.copy2(dll, dist_dir)
        print(f"  已复制 {os.path.basename(dll)}")

    try:
        import usb1
        dll_candidate = os.path.join(os.path.dirname(usb1.__file__), 'libusb-1.0.dll')
        if os.path.isfile(dll_candidate):
            shutil.copy2(dll_candidate, dist_dir)
            print(f"  已复制 libusb-1.0.dll")
    except ImportError:
        pass


def build():
    """执行打包"""
    check_dependencies()
    pack_count = ensure_packs_dir()

    print("\n开始打包...")
    spec_file = os.path.join(ROOT_DIR, 'RTT-Assistant.spec')

    result = subprocess.run(
        [sys.executable, '-m', 'PyInstaller', '--clean', '--noconfirm', spec_file],
        cwd=ROOT_DIR,
    )

    if result.returncode == 0:
        print("\n打包成功!")
        dist_dir = os.path.join(ROOT_DIR, 'dist')

        print("\n复制运行时文件到 dist 目录...")
        copy_runtime_files(dist_dir)

        print(f"\n输出目录: {dist_dir}")
        print(f"\n分发时需包含:")
        print(f"  - exe 文件")
        print(f"  - packs/ 目录 (CMSIS Pack文件)")
        print(f"  - pyocd.yaml (Pack配置，自动生成)")
        print(f"  - pyocd_targets.txt (目标列表缓存)")
        print(f"  - libusb-1.0.dll (USB驱动库)")
        print(f"  - JLink_x64.dll (J-Link驱动，可选)")
    else:
        print(f"\n打包失败! 返回码: {result.returncode}")
        sys.exit(1)


if __name__ == '__main__':
    build()
