from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict

from ..i18n import _ as i18n


class DependencyType(Enum):
    PYTHON_PACKAGE = 'python_package'
    SYSTEM_PACKAGE = 'system_package'
    DLL = 'dll'
    PACK = 'pack'
    CONFIG = 'config'


class BackendType(Enum):
    JLINK = 'jlink'
    DAPLINK = 'daplink'
    STLINK = 'stlink'


@dataclass
class DependencyItem:
    name: str
    dep_type: DependencyType
    description: str = ''
    required: bool = True
    version_constraint: str = ''
    download_url: str = ''
    local_path: str = ''
    filename: str = ''
    backend: Optional[BackendType] = None
    size_mb: float = 0.0

    @property
    def display_name(self) -> str:
        return self.description or self.name


SYSTEM_DEPENDENCIES = []

_PACKED_IN_EXE = {'pylink', 'pefile', 'PyQt5', 'pyqtgraph', 'numpy'}

JLINK_DEPENDENCIES = [
    DependencyItem(
        name='JLink_x64.dll', dep_type=DependencyType.DLL,
        description=i18n("dep.jlink_dll_x64"), backend=BackendType.JLINK,
        required=False, filename='JLink_x64.dll', size_mb=24.5,
        download_url='https://www.segger.com/downloads/jlink/',
    ),
    DependencyItem(
        name='JLinkARM.dll', dep_type=DependencyType.DLL,
        description=i18n("dep.jlink_dll_x86"), backend=BackendType.JLINK,
        required=False, filename='JLinkARM.dll', size_mb=20.0,
        download_url='https://www.segger.com/downloads/jlink/',
    ),
]

PYOCD_CORE_DEPENDENCIES = [
    DependencyItem(
        name='pyocd', dep_type=DependencyType.PYTHON_PACKAGE,
        description=i18n("dep.pyocd_core"), backend=None,
        required=True, version_constraint='>=0.36.0',
        download_url='pip:pyocd>=0.36.0', size_mb=22.0,
    ),
    DependencyItem(
        name='usb1', dep_type=DependencyType.PYTHON_PACKAGE,
        description=i18n("dep.libusb1_binding"), backend=None,
        required=True, download_url='pip:libusb1', size_mb=0.5,
    ),
    DependencyItem(
        name='usb', dep_type=DependencyType.PYTHON_PACKAGE,
        description=i18n("dep.pyusb_enum"), backend=None,
        required=True, download_url='pip:pyusb', size_mb=0.4,
    ),
    DependencyItem(
        name='libusb-1.0.dll', dep_type=DependencyType.DLL,
        description=i18n("dep.libusb_dll"), backend=None,
        required=False, filename='libusb-1.0.dll', size_mb=0.1,
    ),
]

DAPLINK_PLUGIN_DEPENDENCIES = [
    DependencyItem(
        name='Renesas.RA_DFP', dep_type=DependencyType.PACK,
        description=i18n("dep.renesas_pack"), backend=BackendType.DAPLINK,
        required=False, filename='Renesas.RA_DFP.6.1.0.pack', size_mb=2.0,
        download_url='https://developer.arm.com/tools-and-software/open-source-software/developer-tools/cmsis-pack',
    ),
]

STLINK_PLUGIN_DEPENDENCIES = []

BACKEND_DEPENDENCIES: Dict[BackendType, List[DependencyItem]] = {
    BackendType.JLINK: JLINK_DEPENDENCIES,
    BackendType.DAPLINK: DAPLINK_PLUGIN_DEPENDENCIES,
    BackendType.STLINK: STLINK_PLUGIN_DEPENDENCIES,
}

BACKEND_INFO = {
    BackendType.JLINK: {
        'name': 'J-Link',
        'description': i18n("backend.jlink_desc"),
        'icon': 'J',
        'vendors': 'SEGGER',
        'needs_pyocd_core': False,
    },
    BackendType.DAPLINK: {
        'name': 'DAP-Link',
        'description': i18n("backend.daplink_desc"),
        'icon': 'D',
        'vendors': 'ARM/兼容',
        'needs_pyocd_core': True,
    },
    BackendType.STLINK: {
        'name': 'ST-Link',
        'description': i18n("backend.stlink_desc"),
        'icon': 'S',
        'vendors': 'ST',
        'needs_pyocd_core': True,
    },
}


def _needs_pyocd_core(selected_backends: List[BackendType]) -> bool:
    return any(BACKEND_INFO.get(bt, {}).get('needs_pyocd_core', False) for bt in selected_backends)


def get_all_dependencies(selected_backends: List[BackendType] = None) -> List[DependencyItem]:
    deps = list(SYSTEM_DEPENDENCIES)
    if selected_backends is None:
        selected_backends = list(BackendType)

    has_jlink = BackendType.JLINK in selected_backends
    has_pyocd_bt = _needs_pyocd_core(selected_backends)

    if has_jlink:
        deps.extend(JLINK_DEPENDENCIES)

    if has_pyocd_bt:
        deps.extend(PYOCD_CORE_DEPENDENCIES)

    for bt in selected_backends:
        for d in BACKEND_DEPENDENCIES.get(bt, []):
            if d.dep_type == DependencyType.PYTHON_PACKAGE and d.name in [x.name for x in deps]:
                continue
            if d.dep_type == DependencyType.DLL and d.filename in [x.filename for x in deps if hasattr(x, 'filename')]:
                continue
            deps.append(d)

    return deps


DEPENDENCY_LIST = get_all_dependencies()


def get_python_dependencies(selected_backends: List[BackendType] = None) -> List[DependencyItem]:
    return [d for d in get_all_dependencies(selected_backends) if d.dep_type == DependencyType.PYTHON_PACKAGE]


def get_dll_dependencies(selected_backends: List[BackendType] = None) -> List[DependencyItem]:
    return [d for d in get_all_dependencies(selected_backends) if d.dep_type == DependencyType.DLL]


def get_pack_dependencies(selected_backends: List[BackendType] = None) -> List[DependencyItem]:
    return [d for d in get_all_dependencies(selected_backends) if d.dep_type == DependencyType.PACK]


def get_pip_install_list(selected_backends: List[BackendType] = None) -> List[str]:
    packages = []
    for d in get_python_dependencies(selected_backends):
        if d.download_url.startswith('pip:'):
            pkg_spec = d.download_url[4:]
            if pkg_spec not in packages:
                packages.append(pkg_spec)
    return packages


def get_backend_size_mb(bt: BackendType, selected_backends: List[BackendType] = None) -> float:
    if selected_backends is None:
        selected_backends = [bt]
    total = 0.0
    if bt == BackendType.JLINK:
        total = sum(d.size_mb for d in JLINK_DEPENDENCIES)
    else:
        other_pyocd = any(b != bt and BACKEND_INFO.get(b, {}).get('needs_pyocd_core', False)
                          for b in (selected_backends or []))
        if not other_pyocd:
            total += sum(d.size_mb for d in PYOCD_CORE_DEPENDENCIES)
        total += sum(d.size_mb for d in BACKEND_DEPENDENCIES.get(bt, []))
    return total
