import sys
import os
import importlib
import importlib.machinery
import importlib.util

exe_dir = os.path.dirname(sys.executable)
venv_site = os.path.join(exe_dir, 'runtime', 'venv', 'Lib', 'site-packages')
abs_venv = os.path.abspath(venv_site) if os.path.isdir(venv_site) else None

dll_dir = os.path.join(exe_dir, 'runtime', 'dll')
if os.path.isdir(dll_dir):
    abs_dll = os.path.abspath(dll_dir)
    try:
        os.add_dll_directory(abs_dll)
    except Exception:
        pass
    path_env = os.environ.get('PATH', '')
    if abs_dll not in path_env.split(os.pathsep):
        os.environ['PATH'] = abs_dll + os.pathsep + path_env

venv_scripts = os.path.join(exe_dir, 'runtime', 'venv', 'Scripts')
if os.path.isdir(venv_scripts):
    abs_scripts = os.path.abspath(venv_scripts)
    if abs_scripts not in os.environ.get('PATH', '').split(os.pathsep):
        os.environ['PATH'] = abs_scripts + os.pathsep + os.environ.get('PATH', '')

os.environ['PYUSB_BACKEND'] = 'libusb1'


def _find_spec_in_venv(fullname, venv_site):
    parts = fullname.split('.')
    search_dir = venv_site
    for i, part in enumerate(parts):
        pkg_dir = os.path.join(search_dir, part)
        init_py = os.path.join(pkg_dir, '__init__.py')
        if os.path.isfile(init_py) and os.path.isdir(pkg_dir):
            if i == len(parts) - 1:
                return importlib.util.spec_from_file_location(
                    fullname, init_py,
                    submodule_search_locations=[pkg_dir])
            search_dir = pkg_dir
            continue
        for ext in importlib.machinery.SOURCE_SUFFIXES:
            mod_file = os.path.join(search_dir, part + ext)
            if os.path.isfile(mod_file):
                return importlib.util.spec_from_file_location(fullname, mod_file)
        for ext in importlib.machinery.EXTENSION_SUFFIXES:
            mod_file = os.path.join(search_dir, part + ext)
            if os.path.isfile(mod_file):
                return importlib.util.spec_from_file_location(fullname, mod_file)
        return None
    return None


if abs_venv and os.path.isdir(abs_venv):
    _VENV_PRIORITY_MODULES = (
        'usb', 'usb1', 'pyocd', 'hid', 'hidapi',
        'intelhex', 'pyelftools', 'yaml', 'intervaltree',
        'cmsis_pack_manager', 'pefile',
    )

    class _VenvPriorityFinder:
        @staticmethod
        def find_spec(fullname, path=None, target=None):
            for prefix in _VENV_PRIORITY_MODULES:
                if fullname == prefix or fullname.startswith(prefix + '.'):
                    spec = _find_spec_in_venv(fullname, abs_venv)
                    if spec is not None:
                        return spec
                    return None
            return None

    sys.meta_path.insert(0, _VenvPriorityFinder())
