# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('README.md', '.'),
        ('更新说明.md', '.'),
        ('SEGGER_RTT移植指南.md', '.'),
        ('duokajiangfllpll.png', '.'),
        ('SEGGER_RTT.zip', '.'),
        ('icon.ico', '.'),
    ],
    hiddenimports=['pylink', 'pefile', 'psutil'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Segger-RTT-Assistant v1.4',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
)

import shutil
import glob

dist_dir = os.path.join(SPECPATH, 'dist')
os.makedirs(dist_dir, exist_ok=True)

for f in ['config.json', 'devices.txt']:
    src = os.path.join(SPECPATH, f)
    if os.path.exists(src):
        shutil.copy2(src, dist_dir)

for dll in glob.glob(os.path.join(SPECPATH, 'JLink*.dll')):
    shutil.copy2(dll, dist_dir)