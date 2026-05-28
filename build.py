#!/usr/bin/env python
"""打包脚本 - 打包 src/ 为 exe，config/doc/resources/runtime 放到 exe 平级"""

import os
import sys
import subprocess
import shutil
import glob

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


def check_build_deps():
    required = {'PyInstaller': 'PyInstaller', 'PyQt5': 'PyQt5'}
    missing = []
    for pkg_name, import_name in required.items():
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pkg_name)
    if missing:
        print(f"缺少打包依赖: {', '.join(missing)}")
        print(f"请执行: pip install {' '.join(missing)}")
        sys.exit(1)


def build():
    check_build_deps()

    dist_dir = os.path.join(ROOT_DIR, 'dist')
    if os.path.isdir(dist_dir):
        print("\n清空 dist/ 目录...")
        try:
            shutil.rmtree(dist_dir)
        except PermissionError:
            import stat
            def _remove_readonly(func, path, exc_info):
                try:
                    os.chmod(path, stat.S_IWRITE)
                    func(path)
                except Exception:
                    pass
            shutil.rmtree(dist_dir, onexc=_remove_readonly)

    print("\n开始打包...")
    spec_file = os.path.join(ROOT_DIR, 'RTT-Assistant.spec')

    result = subprocess.run(
        [sys.executable, '-m', 'PyInstaller', '--clean', '--noconfirm', spec_file],
        cwd=ROOT_DIR,
    )

    if result.returncode != 0:
        print(f"\n打包失败! 返回码: {result.returncode}")
        sys.exit(1)

    print("\nPyInstaller 打包成功，正在复制外部文件...")

    from src.python.rtt_tool import __version__
    exe_name = f'RTT-Assistant v{__version__}'
    dist_dir = os.path.join(ROOT_DIR, 'dist', exe_name)
    exe_file = os.path.join(ROOT_DIR, 'dist', exe_name + '.exe')

    os.makedirs(dist_dir, exist_ok=True)

    dest_exe = os.path.join(dist_dir, exe_name + '.exe')
    for _ in range(3):
        try:
            if os.path.isfile(dest_exe):
                os.remove(dest_exe)
            break
        except PermissionError:
            print(f"  旧exe被占用，尝试终止进程...")
            subprocess.run(['taskkill', '/F', '/IM', exe_name + '.exe'],
                           capture_output=True, timeout=5)
            import time; time.sleep(2)
    if os.path.isfile(exe_file):
        try:
            shutil.move(exe_file, dest_exe)
            print(f"  已移动 exe 到输出目录")
        except (PermissionError, FileExistsError):
            try:
                if os.path.isfile(dest_exe):
                    os.remove(dest_exe)
            except Exception:
                pass
            shutil.copy2(exe_file, dest_exe)
            print(f"  已复制 exe 到输出目录(原文件被占用)")
    else:
        print(f"  警告: 未找到 {exe_file}，请检查 PyInstaller 输出")

    print(f"输出目录: {dist_dir}")

    # Copy config/ (only pyocd.yaml, rest auto-generated)
    config_src = os.path.join(ROOT_DIR, 'config')
    config_dst = os.path.join(dist_dir, 'config')
    if os.path.isdir(config_src):
        os.makedirs(config_dst, exist_ok=True)
        for f in ['pyocd.yaml']:
            src = os.path.join(config_src, f)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(config_dst, f))
                print(f"  已复制 config/{f}")
        print(f"  已复制 config/ (仅 {', '.join(os.listdir(config_dst))})")

    # Copy doc/ (convert .md to .html, copy .pdf and images/)
    doc_src = os.path.join(ROOT_DIR, 'doc')
    doc_dst = os.path.join(dist_dir, 'doc')
    if os.path.isdir(doc_src):
        if os.path.isdir(doc_dst):
            shutil.rmtree(doc_dst)
        os.makedirs(doc_dst, exist_ok=True)
        from markdown import markdown
        _CSS = "<meta charset='utf-8'><style>body{font-family:'Microsoft YaHei',sans-serif;max-width:900px;margin:0 auto;padding:20px;line-height:1.8}pre{background:#f5f5f5;padding:10px;border-radius:4px;overflow-x:auto}code{background:#f0f0f0;padding:2px 4px;border-radius:2px}table{border-collapse:collapse;width:100%}th,td{border:1px solid #ccc;padding:6px 10px;text-align:left}th{background:#eee}</style>"
        for item in os.listdir(doc_src):
            src_item = os.path.join(doc_src, item)
            name, ext = os.path.splitext(item)
            if ext == '.md':
                with open(src_item, encoding='utf-8') as f:
                    html = _CSS + markdown(f.read(), extensions=['fenced_code', 'tables', 'codehilite'])
                dst_path = os.path.join(doc_dst, name + '.html')
                with open(dst_path, 'w', encoding='utf-8') as f:
                    f.write(html)
                print(f"  已转换 doc/{item} -> doc/{name}.html")
            elif ext == '.html':
                shutil.copy2(src_item, os.path.join(doc_dst, item))
            elif item == 'images' and os.path.isdir(src_item) and os.listdir(src_item):
                shutil.copytree(src_item, os.path.join(doc_dst, 'images'))
        print(f"  已复制 doc/ (md→html + images)")

    # Copy images/ (if exists at root level)
    images_src = os.path.join(ROOT_DIR, 'images')
    images_dst = os.path.join(dist_dir, 'images')
    if os.path.isdir(images_src):
        if os.path.isdir(images_dst):
            shutil.rmtree(images_dst)
        shutil.copytree(images_src, images_dst)
        print(f"  已复制 images/")

    # Copy resources/ (only RTT.zip, icons, png)
    res_src = os.path.join(ROOT_DIR, 'resources')
    res_dst = os.path.join(dist_dir, 'resources')
    if os.path.isdir(res_src):
        os.makedirs(res_dst, exist_ok=True)
        for f in ['RTT.zip', 'icon.ico', 'duokajiangfllpll.png']:
            src = os.path.join(res_src, f)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(res_dst, f))
                print(f"  已复制 resources/{f}")
        print(f"  已复制 resources/ ({', '.join(os.listdir(res_dst))})")

    # Copy runtime/ structure (dll, packs, venv)
    runtime_src = os.path.join(ROOT_DIR, 'runtime')
    runtime_dst = os.path.join(dist_dir, 'runtime')
    for sub in ['dll', 'packs']:
        os.makedirs(os.path.join(runtime_dst, sub), exist_ok=True)
    print(f"  已创建 runtime/dll/ runtime/packs/")

    venv_src = os.path.join(runtime_src, 'venv')
    venv_dst = os.path.join(runtime_dst, 'venv')
    if os.path.isdir(venv_src):
        if os.path.isdir(venv_dst):
            shutil.rmtree(venv_dst)

        _CRITICAL_VENV_PACKAGES = ['pyocd', 'usb', 'usb1']
        _EXCLUDED_VENV_PACKAGES = [
            'PyQt5', 'PyQt5-*', 'pyqt5_*', 'pyqtgraph', 'pyqtgraph-*',
            'numpy', 'numpy-*', 'numpy.libs',
        ]

        _excluded_patterns = ['*.pyc', '__pycache__'] + _EXCLUDED_VENV_PACKAGES

        def _copy_venv_with_retry(src, dst, max_retries=3):
            import stat
            for attempt in range(1, max_retries + 1):
                if os.path.isdir(dst):
                    shutil.rmtree(dst, onexc=lambda func, path, exc_info: (
                        os.chmod(path, stat.S_IWRITE), func(path)
                    ) if isinstance(exc_info[1], PermissionError) else None)
                try:
                    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*_excluded_patterns))
                except Exception as e:
                    print(f"    第{attempt}次复制失败: {e}")
                    if attempt < max_retries:
                        import time; time.sleep(2)
                        continue
                    raise

                site_dst = os.path.join(dst, 'Lib', 'site-packages')
                missing = []
                for pkg in _CRITICAL_VENV_PACKAGES:
                    pkg_path = os.path.join(site_dst, pkg)
                    pkg_pyd = os.path.join(site_dst, pkg + '.cp313-win_amd64.pyd')
                    if not os.path.exists(pkg_path) and not os.path.exists(pkg_pyd):
                        missing.append(pkg)
                if missing:
                    print(f"    警告: 第{attempt}次复制后缺少关键包: {', '.join(missing)}")
                    if attempt < max_retries:
                        print(f"    重试复制...")
                        import time; time.sleep(2)
                        continue
                else:
                    return True
            return False

        print("  正在复制 runtime/venv/ (可能较大，请稍候)...")
        _copy_venv_with_retry(venv_src, venv_dst)
        size_mb = 0
        for dirpath, _, filenames in os.walk(venv_dst):
            for f in filenames:
                size_mb += os.path.getsize(os.path.join(dirpath, f))
        src_count = sum(1 for _ in os.walk(os.path.join(venv_src, 'Lib', 'site-packages')))
        dst_count = sum(1 for _ in os.walk(os.path.join(venv_dst, 'Lib', 'site-packages')))
        print(f"  已复制 runtime/venv/ ({size_mb / 1024 / 1024:.0f}MB, site-packages: {dst_count}/{src_count} 目录)")

        # Fix shebang lines in venv Scripts (intelhex etc.)
        scripts_dst = os.path.join(venv_dst, 'Scripts')
        if os.path.isdir(scripts_dst):
            fixed = 0
            for f in os.listdir(scripts_dst):
                if f.endswith('.py'):
                    fp = os.path.join(scripts_dst, f)
                    try:
                        with open(fp, 'r', encoding='utf-8') as fh:
                            first_line = fh.readline()
                        if first_line.startswith('#!') and 'venv' in first_line:
                            with open(fp, 'r', encoding='utf-8') as fh:
                                rest = fh.read()
                            with open(fp, 'w', encoding='utf-8') as fh:
                                fh.write('#!/usr/bin/env python3\n')
                                fh.write(rest)
                            fixed += 1
                    except Exception:
                        pass
            if fixed:
                print(f"  已修复 {fixed} 个 venv Scripts 的 shebang 路径")

        # Fix pyvenv.cfg in venv
        pyvenv_cfg = os.path.join(venv_dst, 'pyvenv.cfg')
        if os.path.isfile(pyvenv_cfg):
            try:
                with open(pyvenv_cfg, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                version_line = ''
                for line in lines:
                    if line.strip().startswith('version ='):
                        version_line = line if line.endswith('\n') else line + '\n'
                with open(pyvenv_cfg, 'w', encoding='utf-8') as f:
                    f.write(f'home = {os.path.dirname(sys.executable)}\n')
                    f.write('include-system-site-packages = false\n')
                    if version_line:
                        f.write(version_line)
                    f.write(f'executable = {sys.executable}\n')
                    f.write(f'command = {sys.executable} -m venv {venv_dst}\n')
                print(f"  已修复 venv/pyvenv.cfg 路径")
            except Exception as e:
                print(f"  修复 pyvenv.cfg 失败: {e}")
    else:
        print(f"  注意: runtime/venv/ 不存在，用户需自行安装Python依赖")

    # Copy log/ dir
    os.makedirs(os.path.join(dist_dir, 'log'), exist_ok=True)
    print(f"  已创建 log/")

    # Copy DLLs from runtime/dll/
    dll_src = os.path.join(runtime_src, 'dll')
    if os.path.isdir(dll_src):
        for f in os.listdir(dll_src):
            if f.endswith('.dll'):
                shutil.copy2(os.path.join(dll_src, f), os.path.join(runtime_dst, 'dll', f))
                print(f"  已复制 runtime/dll/{f}")

    # Copy runtime/cpm_cache/ (index.json + aliases.json for Pack search)
    cpm_src = os.path.join(runtime_src, 'cpm_cache')
    cpm_dst = os.path.join(runtime_dst, 'cpm_cache')
    if os.path.isdir(cpm_src):
        os.makedirs(cpm_dst, exist_ok=True)
        for f in ['index.json', 'aliases.json']:
            src_f = os.path.join(cpm_src, f)
            if os.path.isfile(src_f):
                shutil.copy2(src_f, os.path.join(cpm_dst, f))
        copied = [f for f in ['index.json', 'aliases.json'] if os.path.isfile(os.path.join(cpm_dst, f))]
        if copied:
            print(f"  已复制 runtime/cpm_cache/ ({', '.join(copied)})")

    print(f"\n打包完成! 输出: {dist_dir}")
    print(f"\n分发时复制整个 {os.path.basename(dist_dir)} 文件夹到目标电脑即可运行")
    print(f"用户需在 runtime/venv/ 安装 Python 依赖（或使用帮助菜单的依赖管理）")


if __name__ == '__main__':
    build()
