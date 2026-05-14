import os
import sys

if getattr(sys, 'frozen', False):
    base = sys._MEIPASS
    dirs = [base]
    usb1_dir = os.path.join(base, 'usb1')
    if os.path.isdir(usb1_dir):
        dirs.append(usb1_dir)
    for d in dirs:
        try:
            os.add_dll_directory(d)
        except (OSError, FileNotFoundError, AttributeError):
            pass
        path_env = os.environ.get('PATH', '')
        norm_d = os.path.normcase(os.path.normpath(d))
        already = any(os.path.normcase(os.path.normpath(p)) == norm_d for p in path_env.split(os.pathsep) if p)
        if not already:
            os.environ['PATH'] = d + os.pathsep + path_env

os.environ['PYUSB_BACKEND'] = 'libusb1'

_libusb_dll_path = None
try:
    import usb1
    _candidate = os.path.join(os.path.dirname(usb1.__file__), 'libusb-1.0.dll')
    if os.path.isfile(_candidate):
        _libusb_dll_path = _candidate
except Exception:
    pass

if _libusb_dll_path:
    try:
        import ctypes
        ctypes.CDLL(_libusb_dll_path)
    except Exception:
        pass

    try:
        import usb.backend.libusb1 as _libusb1_backend
        _orig_get_backend = _libusb1_backend.get_backend
        def _patched_get_backend(find_library=None, **kwargs):
            return _orig_get_backend(find_library=lambda x: _libusb_dll_path)
        _libusb1_backend.get_backend = _patched_get_backend
    except Exception:
        pass

    try:
        import libusb_package as _lp
        _orig_lp_backend = getattr(_lp, 'get_libusb1_backend', None)
        if _orig_lp_backend:
            def _patched_lp_backend():
                return _orig_get_backend(find_library=lambda x: _libusb_dll_path)
            _lp.get_libusb1_backend = _patched_lp_backend
    except ImportError:
        pass

try:
    import usb.util as _usb_util
    _orig_get_string = _usb_util.get_string
    def _safe_get_string(dev, desc, default=None):
        try:
            return _orig_get_string(dev, desc)
        except (NotImplementedError, ValueError, UnicodeDecodeError):
            return default if default is not None else ''
    _usb_util.get_string = _safe_get_string
except Exception:
    pass
