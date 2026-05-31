# -*- mode: python ; coding: utf-8 -*-
# PyOCD standalone exe - self-contained flash tool
# Usage: pyocd.exe flash --target TARGET --erase auto --frequency HZ firmware.elf

import os
from PyInstaller.utils.hooks import collect_all

_pyocd_datas, _pyocd_binaries, _pyocd_hiddenimports = collect_all('pyocd')
_usb_datas, _usb_binaries, _usb_hiddenimports = collect_all('usb')
_usb1_datas, _usb1_binaries, _usb1_hiddenimports = collect_all('usb1')

a = Analysis(
    ['runtime/pyocd_entry.py'],
    pathex=['runtime/venv/Lib/site-packages'],
    binaries=_pyocd_binaries + _usb_binaries + _usb1_binaries,
    datas=_pyocd_datas + _usb_datas + _usb1_datas,
    hiddenimports=[
        'pyocd', 'pyocd.core', 'pyocd.core.helpers', 'pyocd.core.session',
        'pyocd.flash', 'pyocd.flash.loader',
        'pyocd.probe', 'pyocd.probe.aggregator',
        'pyocd.utility', 'pyocd.utility.progress',
        'pyocd.board', 'pyocd.target', 'pyocd.debug',
        'pyocd.coresight', 'pyocd.gdbserver',
        'usb', 'usb1',
        'intelhex', 'colorama', 'yaml',
        'capstone', 'intervaltree', 'lark', 'natsort',
        'prettytable', 'pyelftools',
        'importlib_metadata', 'importlib_resources',
        'typing_extensions', 'libusb_package',
    ] + _pyocd_hiddenimports + _usb_hiddenimports + _usb1_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['src/scripts/runtime_hook_usb.py'],
    excludes=[
        'PyQt5', 'pyqtgraph', 'numpy',
        'tkinter', 'tcl', 'tk',
        'cmsis_pack_manager',
    ],
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
    name='pyocd',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)