# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[
        ('JLink_x64.dll', '.'),
    ],
    datas=[
        ('README.md', '.'),
        ('更新说明.md', '.'),
        ('SEGGER_RTT移植指南.md', '.'),
        ('duokajiangfllpll.png', '.'),
        ('SEGGER_RTT.zip', '.'),
        ('icon.ico', '.'),
        ('config.json', '.'),
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
    name='Segger-RTT-Assistant v1.3',
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