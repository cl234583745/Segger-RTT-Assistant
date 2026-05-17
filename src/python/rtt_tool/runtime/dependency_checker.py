import os
import importlib
from dataclasses import dataclass, field
from typing import List, Dict, Optional

from .path_config import (
    RUNTIME_VENV_SITE_PACKAGES, RUNTIME_DLL_DIR, RUNTIME_PACKS_DIR,
    find_jlink_dll, find_libusb_dll,
)
from .dependency_manifest import (
    DependencyItem, DependencyType, BackendType,
    get_all_dependencies, BACKEND_INFO,
)


@dataclass
class DependencyStatus:
    name: str
    dep_type: DependencyType
    is_available: bool
    detail: str = ''
    required: bool = True


@dataclass
class DependencyCheckReport:
    items: List[DependencyStatus] = field(default_factory=list)

    @property
    def all_required_ok(self) -> bool:
        return all(s.is_available for s in self.items if s.required)

    @property
    def missing_required(self) -> List[DependencyStatus]:
        return [s for s in self.items if s.required and not s.is_available]

    @property
    def missing_optional(self) -> List[DependencyStatus]:
        return [s for s in self.items if not s.required and not s.is_available]

    @property
    def available_count(self) -> int:
        return sum(1 for s in self.items if s.is_available)

    @property
    def total_count(self) -> int:
        return len(self.items)

    def to_summary(self) -> str:
        lines = []
        for s in self.items:
            tag = '✓' if s.is_available else '✗'
            req = '[必需]' if s.required else '[可选]'
            lines.append(f"  {tag} {req} {s.name}: {s.detail}")
        return '\n'.join(lines)


class DependencyChecker:

    @staticmethod
    def check_runtime_python_package(name: str) -> tuple:
        pkg_dir = os.path.join(RUNTIME_VENV_SITE_PACKAGES, name)
        if os.path.isdir(pkg_dir):
            return True, 'runtime venv中存在'
        init_file = os.path.join(RUNTIME_VENV_SITE_PACKAGES, name + '.py')
        if os.path.isfile(init_file):
            return True, 'runtime venv中存在'
        return False, 'runtime venv中不存在'

    @staticmethod
    def check_runtime_dll(filename: str) -> tuple:
        dll_path = os.path.join(RUNTIME_DLL_DIR, filename)
        if os.path.isfile(dll_path):
            size_kb = os.path.getsize(dll_path) / 1024
            return True, f'runtime中存在 ({size_kb:.0f}KB)'
        return False, 'runtime中不存在'

    @staticmethod
    def check_runtime_packs() -> tuple:
        if not os.path.isdir(RUNTIME_PACKS_DIR):
            return False, 'runtime/packs目录不存在'
        packs = [f for f in os.listdir(RUNTIME_PACKS_DIR) if f.endswith('.pack')]
        if packs:
            return True, f'runtime中{len(packs)}个Pack文件'
        return False, 'runtime中无Pack文件'

    @classmethod
    def check_all(cls, selected_backends: List[BackendType] = None) -> DependencyCheckReport:
        report = DependencyCheckReport()
        deps = get_all_dependencies(selected_backends)

        for dep in deps:
            if dep.dep_type in (DependencyType.SYSTEM_PACKAGE, DependencyType.PYTHON_PACKAGE):
                ok, detail = cls.check_runtime_python_package(dep.name)
            elif dep.dep_type == DependencyType.DLL:
                ok, detail = cls.check_runtime_dll(dep.filename or dep.name)
            elif dep.dep_type == DependencyType.PACK:
                ok, detail = cls.check_runtime_packs()
            else:
                ok, detail = True, '未知类型'

            report.items.append(DependencyStatus(
                name=dep.name, dep_type=dep.dep_type,
                is_available=ok, detail=detail, required=dep.required,
            ))

        return report
