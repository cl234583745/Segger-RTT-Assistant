import os
import sys
import struct


def get_app_root():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    _this_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_this_dir))))


RUNTIME_DIR = os.path.join(get_app_root(), 'runtime')
RUNTIME_VENV_DIR = os.path.join(RUNTIME_DIR, 'venv')
RUNTIME_VENV_SITE_PACKAGES = os.path.join(RUNTIME_VENV_DIR, 'Lib', 'site-packages')
RUNTIME_VENV_SCRIPTS = os.path.join(RUNTIME_VENV_DIR, 'Scripts')
RUNTIME_VENV_PIP = os.path.join(RUNTIME_VENV_SCRIPTS, 'pip.exe')
RUNTIME_VENV_PYTHON = os.path.join(RUNTIME_VENV_SCRIPTS, 'python.exe')

RUNTIME_DLL_DIR = os.path.join(RUNTIME_DIR, 'dll')
RUNTIME_PACKS_DIR = os.path.join(RUNTIME_DIR, 'packs')

_python_bits = struct.calcsize('P') * 8
JLINK_DLL_NAME = 'JLink_x64.dll' if _python_bits == 64 else 'JLinkARM.dll'

RUNTIME_JLINK_DLL_PATH = os.path.join(RUNTIME_DLL_DIR, JLINK_DLL_NAME)
RUNTIME_LIBUSB_DLL_PATH = os.path.join(RUNTIME_DLL_DIR, 'libusb-1.0.dll')

RUNTIME_CONFIG_DIR = os.path.join(get_app_root(), 'config')
RUNTIME_CONFIG_JSON = os.path.join(RUNTIME_CONFIG_DIR, 'config.json')
RUNTIME_PYOCD_YAML = os.path.join(RUNTIME_CONFIG_DIR, 'pyocd.yaml')
RUNTIME_DEVICES_TXT = os.path.join(RUNTIME_CONFIG_DIR, 'devices.txt')
RUNTIME_PYOCD_TARGETS_TXT = os.path.join(RUNTIME_CONFIG_DIR, 'pyocd_targets.txt')
RUNTIME_LOG_DIR = os.path.join(get_app_root(), 'log')
RUNTIME_DOC_DIR = os.path.join(get_app_root(), 'doc')
RUNTIME_RESOURCES_DIR = os.path.join(get_app_root(), 'resources')
RUNTIME_ICON_ICO = os.path.join(RUNTIME_RESOURCES_DIR, 'icon.ico')
RUNTIME_ICON_PNG = os.path.join(RUNTIME_RESOURCES_DIR, 'icon.png')


def ensure_runtime_dirs():
    for d in [RUNTIME_DIR, RUNTIME_DLL_DIR, RUNTIME_PACKS_DIR, RUNTIME_LOG_DIR]:
        os.makedirs(d, exist_ok=True)


def inject_python_path():
    ensure_runtime_dirs()
    if os.path.isdir(RUNTIME_VENV_SITE_PACKAGES):
        abs_path = os.path.abspath(RUNTIME_VENV_SITE_PACKAGES)
        if abs_path not in sys.path:
            sys.path.insert(0, abs_path)


def inject_dll_path():
    ensure_runtime_dirs()
    dll_dir = os.path.abspath(RUNTIME_DLL_DIR)
    try:
        os.add_dll_directory(dll_dir)
    except (OSError, FileNotFoundError, AttributeError):
        pass
    path_env = os.environ.get('PATH', '')
    if dll_dir not in path_env.split(os.pathsep):
        os.environ['PATH'] = dll_dir + os.pathsep + path_env
    venv_scripts = os.path.abspath(RUNTIME_VENV_SCRIPTS)
    if os.path.isdir(venv_scripts) and venv_scripts not in path_env.split(os.pathsep):
        os.environ['PATH'] = venv_scripts + os.pathsep + os.environ.get('PATH', '')


def find_jlink_dll():
    if os.path.isfile(RUNTIME_JLINK_DLL_PATH):
        return RUNTIME_JLINK_DLL_PATH
    exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else get_app_root()
    candidate = os.path.join(exe_dir, JLINK_DLL_NAME)
    if os.path.isfile(candidate):
        return candidate
    return None


def find_libusb_dll():
    if os.path.isfile(RUNTIME_LIBUSB_DLL_PATH):
        return RUNTIME_LIBUSB_DLL_PATH
    try:
        import usb1
        candidate = os.path.join(os.path.dirname(usb1.__file__), 'libusb-1.0.dll')
        if os.path.isfile(candidate):
            return candidate
    except ImportError:
        pass
    return None
