import os
import sys

from .path_config import (
    RUNTIME_DIR, inject_python_path, inject_dll_path, ensure_runtime_dirs,
    fix_pyvenv_cfg, find_libusb_dll, RUNTIME_PYOCD_YAML, RUNTIME_PACKS_DIR,
)


class RuntimeGuard:

    @classmethod
    def setup(cls):
        ensure_runtime_dirs()
        fix_pyvenv_cfg()
        inject_python_path()
        inject_dll_path()
        cls._setup_pyocd_config()
        cls._setup_libusb()
        cls._ensure_target_index()
        return True

    @classmethod
    def _ensure_target_index(cls):
        try:
            from .pyocd_target_index import ensure_index
            ensure_index()
        except Exception:
            pass

    @classmethod
    def _setup_pyocd_config(cls):
        try:
            from ..utils.resource_utils import sync_pyocd_yaml
            sync_pyocd_yaml()
        except Exception:
            pass
        if os.path.isfile(RUNTIME_PYOCD_YAML):
            os.environ['PYOCD_CONFIG'] = RUNTIME_PYOCD_YAML

    @classmethod
    def _setup_libusb(cls):
        dll_path = find_libusb_dll()
        if dll_path and os.path.isfile(dll_path):
            try:
                import ctypes
                ctypes.CDLL(dll_path)
            except Exception:
                pass
            try:
                os.add_dll_directory(os.path.dirname(dll_path))
            except Exception:
                pass
            try:
                for mod_name in ('usb', 'usb.backend', 'usb.backend.libusb1', 'usb1'):
                    if mod_name in sys.modules:
                        del sys.modules[mod_name]
                import usb.backend.libusb1 as _libusb1_backend
                _orig = _libusb1_backend.get_backend
                def _patched(find_library=None, **kwargs):
                    return _orig(find_library=lambda x: dll_path)
                _libusb1_backend.get_backend = _patched
            except Exception:
                pass
        os.environ['PYUSB_BACKEND'] = 'libusb1'
