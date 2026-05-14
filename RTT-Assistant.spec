# -*- mode: python ; coding: utf-8 -*-

import sys
sys.path.insert(0, '.')
from rtt_tool import __version__
import glob
import os
import shutil

from PyInstaller.utils.hooks import collect_data_files, collect_submodules
pyocd_datas = collect_data_files('pyocd')
pyocd_hidden = collect_submodules('pyocd')

libusb_dll = None
try:
    import usb1
    dll_candidate = os.path.join(os.path.dirname(usb1.__file__), 'libusb-1.0.dll')
    if os.path.isfile(dll_candidate):
        libusb_dll = dll_candidate
except ImportError:
    pass

extra_hidden = [
    'pylink', 'pefile', 'psutil',
    'pyocd', 'usb1', 'usb', 'usb.core', 'usb.backend', 'usb.backend.libusb1',
    'intelhex', 'pyelftools', 'pyelftools.elf.elffile', 'pyelftools.elf.sections',
    'yaml', 'hid', 'hidapi', 'intervaltree',
    'rtt_tool.backend', 'rtt_tool.backend.base', 'rtt_tool.backend.jlink_backend',
    'rtt_tool.backend.pyocd_backend', 'rtt_tool.backend.manager',
    'rtt_tool.processors', 'rtt_tool.processors.base', 'rtt_tool.processors.log_processor',
    'rtt_tool.processors.waveform_processor', 'rtt_tool.processors.variable_monitor',
    'rtt_tool.plugins', 'rtt_tool.plugins.plugin_base', 'rtt_tool.plugins.plugin_manager',
    'rtt_tool.utils.data_export_service', 'rtt_tool.utils.data_replay_service',
]

extra_binaries = []
if libusb_dll:
    extra_binaries.append((libusb_dll, 'usb1'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=extra_binaries,
    datas=[
        ('icon.ico', '.'),
    ] + pyocd_datas,
    hiddenimports=extra_hidden + pyocd_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['rth_libusb.py'],
    excludes=[
        'numba', 'llvmlite', 'scipy', 'pandas', 'matplotlib',
        'PIL', 'Pillow', 'tkinter', 'tcl', 'tk',
        'IPython', 'jupyter', 'notebook',
        'sphinx', 'docutils', 'pytest',
        'cv2', 'opencv',
        'sqlalchemy', 'django', 'flask',
        'zmq', 'tornado',
        'lxml', 'html5lib', 'beautifulsoup4', 'bs4',
        'pyarrow', 'h5py',
        'sympy', 'networkx',
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
    name=f'RTT-Assistant v{__version__}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=['libusb-1.0.dll', 'JLink_x64.dll', 'JLinkARM.dll'],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
)
