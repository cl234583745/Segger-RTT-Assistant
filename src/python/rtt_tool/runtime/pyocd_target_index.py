import os
import subprocess
import time
import json
import glob as _glob
from dataclasses import dataclass, asdict
from typing import List, Optional

from .path_config import (
    RUNTIME_PYOCD_TARGETS_TXT, RUNTIME_VENV_SCRIPTS, RUNTIME_PACKS_DIR,
)

_PACK_CACHE_SUBDIR = '_pack_cache'


@dataclass
class PyOCDTargetEntry:
    name: str
    vendor: str
    part_number: str
    families: str
    source: str
    pack: str

    def to_line(self) -> str:
        return '\t'.join([self.name, self.vendor, self.part_number, self.families, self.source, self.pack])

    @staticmethod
    def from_line(line: str) -> Optional['PyOCDTargetEntry']:
        parts = line.split('\t')
        if len(parts) >= 6 and parts[0].strip():
            return PyOCDTargetEntry(
                name=parts[0].strip(),
                vendor=parts[1].strip(),
                part_number=parts[2].strip(),
                families=parts[3].strip(),
                source=parts[4].strip(),
                pack=parts[5].strip(),
            )
        return None


def _get_pyocd_exe() -> str:
    """返回 venv 的 python.exe，调用方用 -m pyocd 代替直接运行 pyocd.exe 启动器。"""
    py_exe = os.path.join(RUNTIME_VENV_SCRIPTS, 'python.exe')
    if os.path.isfile(py_exe):
        return py_exe
    return None


def _subprocess_flags():
    return getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def _parse_targets_output(output: str) -> List[PyOCDTargetEntry]:
    entries = []
    for line in output.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('#') or line.startswith('-'):
            continue
        if line.lower().startswith('name'):
            continue
        parts = line.split()
        if len(parts) < 3:
            continue
        name = parts[0]
        vendor = parts[1] if len(parts) > 1 else ''
        part_number = ''
        families = ''
        source = 'builtin'
        source_idx = -1
        for i, p in enumerate(parts):
            if p in ('builtin', 'pack'):
                source = p
                source_idx = i
                break
        if source_idx == 2:
            pass
        elif source_idx == 3:
            part_number = parts[2]
        elif source_idx >= 4:
            part_number = parts[2]
            families = ' '.join(parts[3:source_idx])
        entries.append(PyOCDTargetEntry(
            name=name, vendor=vendor, part_number=part_number,
            families=families, source=source, pack='-',
        ))
    return entries


def _pack_cache_dir():
    d = os.path.join(os.path.dirname(RUNTIME_PYOCD_TARGETS_TXT), _PACK_CACHE_SUBDIR)
    os.makedirs(d, exist_ok=True)
    return d


def _pack_cache_path(pack_name: str) -> str:
    safe = pack_name.replace('.', '_').replace(' ', '_')
    return os.path.join(_pack_cache_dir(), safe + '.json')


def _pack_signature(pack_path: str) -> tuple:
    try:
        st = os.stat(pack_path)
        return (st.st_mtime, st.st_size)
    except OSError:
        return None


def _load_pack_cache(pack_name: str, pack_path: str) -> Optional[List[PyOCDTargetEntry]]:
    cache_file = _pack_cache_path(pack_name)
    if not os.path.isfile(cache_file):
        return None
    current_sig = _pack_signature(pack_path)
    if current_sig is None:
        return None
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        cached_sig = tuple(data.get('signature', (0, 0)))
        if cached_sig != current_sig:
            return None
        entries = []
        for raw in data.get('targets', []):
            entries.append(PyOCDTargetEntry(**raw))
        return entries
    except Exception:
        return None


def _save_pack_cache(pack_name: str, pack_path: str, entries: List[PyOCDTargetEntry]):
    cache_file = _pack_cache_path(pack_name)
    sig = _pack_signature(pack_path)
    if sig is None:
        return
    data = {
        'pack_name': pack_name,
        'signature': list(sig),
        'targets': [asdict(e) for e in entries],
    }
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


def _get_builtin_targets() -> List[PyOCDTargetEntry]:
    """从 PyOCD 内置注册表获取目标列表（使用 Python API，不启动子进程）。"""
    entries = []
    try:
        import pyocd.target as _pyocd_target
        for tname, tcls in _pyocd_target.TARGET.items():
            try:
                vendor = getattr(tcls, 'vendor', '') or ''
                part_number = getattr(tcls, 'part_number', '') or ''
                families = ''
                if hasattr(tcls, 'family'):
                    fam = getattr(tcls, 'family')
                    if fam and isinstance(fam, list):
                        families = ', '.join(str(f) for f in fam)
                    elif fam:
                        families = str(fam)
            except Exception:
                vendor, part_number, families = '', '', ''
            entries.append(PyOCDTargetEntry(
                name=tname, vendor=vendor, part_number=part_number,
                families=families, source='builtin', pack='-',
            ))
    except Exception:
        pass
    return entries


def _load_pack_targets_from_zip(pack_file: str, progress_callback=None) -> List[PyOCDTargetEntry]:
    """直接解析 .pack (ZIP) 中的 .pdsc (XML) 获取目标列表，归属100%准确。"""
    import zipfile
    import xml.etree.ElementTree as ET
    pname = os.path.basename(pack_file)
    if progress_callback:
        progress_callback(f'解析 {pname}...')
    entries = []
    try:
        with zipfile.ZipFile(pack_file) as z:
            pdsc_files = [n for n in z.namelist() if n.endswith('.pdsc')]
            for pdsc in pdsc_files:
                with z.open(pdsc) as f:
                    tree = ET.parse(f)
                    root = tree.getroot()
                    vendor = ''
                    el = root.find('.//vendor')
                    if el is not None:
                        vendor = (el.text or '').strip()
                    for dev in root.findall('.//device'):
                        dname = dev.get('Dname', '')
                        if not dname:
                            continue
                        family_el = dev.find('family')
                        families = ''
                        if family_el is not None:
                            families = (family_el.text or '').strip()
                        entries.append(PyOCDTargetEntry(
                            name=dname.lower(),
                            vendor=vendor,
                            part_number=dname,
                            families=families,
                            source='pack',
                            pack=pname,
                        ))
                        for var in dev.findall('.//variant'):
                            vname = var.get('Dvariant', '')
                            if vname:
                                entries.append(PyOCDTargetEntry(
                                    name=vname.lower(),
                                    vendor=vendor,
                                    part_number=vname,
                                    families=families,
                                    source='pack',
                                    pack=pname,
                                ))
    except Exception:
        pass
    return entries


def _load_pack_targets_pyapi(pack_file: str, builtin_names: set, progress_callback=None) -> List[PyOCDTargetEntry]:
    """通过 Python API 加载 pack 目标（子进程失败时的回退）。"""
    import pyocd.target as _pyocd_target
    pname = os.path.basename(pack_file)
    if progress_callback:
        progress_callback(f'解析 {pname} (Python API)...')
    before = set(_pyocd_target.TARGET.keys())
    try:
        from pyocd.core.pack import PackTarget
        PackTarget._load_pack(pack_file)
    except Exception:
        try:
            from pyocd.core.session import Session
            s = Session(None, options={'pack': [pack_file], 'enable_svd': False, 'no_probe': True})
            s.board
        except Exception:
            pass
    current_names = set(_pyocd_target.TARGET.keys())
    new_names = current_names - builtin_names - before
    entries = []
    for tname in new_names:
        try:
            tcls = _pyocd_target.TARGET[tname]
            vendor = getattr(tcls, 'vendor', '') or ''
            part_number = getattr(tcls, 'part_number', '') or ''
            families = ''
            if hasattr(tcls, 'family'):
                fam = getattr(tcls, 'family')
                if fam and isinstance(fam, list):
                    families = ', '.join(str(f) for f in fam)
                elif fam:
                    families = str(fam)
        except Exception:
            vendor, part_number, families = '', '', ''
        entries.append(PyOCDTargetEntry(
            name=tname, vendor=vendor, part_number=part_number,
            families=families, source='pack', pack=pname,
        ))
    for tname in (current_names - before - builtin_names):
        _pyocd_target.TARGET.pop(tname, None)
    return entries


def generate_index(progress_callback=None) -> List[PyOCDTargetEntry]:
    pyocd_exe = _get_pyocd_exe()
    if not pyocd_exe:
        return []

    entries = []
    seen_targets = set()

    t0 = time.time()

    pack_files = sorted(_glob.glob(os.path.join(RUNTIME_PACKS_DIR, '*.pack'))) if os.path.isdir(RUNTIME_PACKS_DIR) else []

    if pack_files:
        if progress_callback:
            progress_callback(f'解析 {len(pack_files)} 个 Pack...')
        for pf in pack_files:
            pname = os.path.basename(pf)
            t1 = time.time()
            pack_entries = _load_pack_targets_from_zip(pf, progress_callback)
            for e in pack_entries:
                if e.name.lower() not in seen_targets:
                    entries.append(e)
                    seen_targets.add(e.name.lower())
            elapsed = (time.time() - t1) * 1000
            if progress_callback:
                progress_callback(f'  {pname}: {len(pack_entries)} 个目标 ({elapsed:.0f}ms)')

    builtin_entries = []
    if progress_callback:
        progress_callback('获取内置目标列表...')
    builtin_entries = _get_builtin_targets()
    for e in builtin_entries:
        if e.name.lower() not in seen_targets:
            entries.append(e)
            seen_targets.add(e.name.lower())

    builtin_names = set(e.name.lower() for e in builtin_entries)
    bt_elapsed = (time.time() - t0) * 1000
    if progress_callback and builtin_entries:
        progress_callback(f'内置目标: {len(builtin_entries)} 个 ({bt_elapsed:.0f}ms)')

    if progress_callback:
        progress_callback(f'索引完成: {len(entries)} 个目标 ({(time.time()-t0)*1000:.0f}ms)')

    return entries


def save_index(entries: List[PyOCDTargetEntry], path: str = None) -> str:
    filepath = path or RUNTIME_PYOCD_TARGETS_TXT
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('# Name\tVendor\tPartNumber\tFamilies\tSource\tPack\n')
        f.write('#' + '-' * 80 + '\n')
        for e in entries:
            f.write(e.to_line() + '\n')
    return filepath


def load_index(path: str = None) -> List[PyOCDTargetEntry]:
    filepath = path or RUNTIME_PYOCD_TARGETS_TXT
    if not os.path.isfile(filepath):
        return []
    entries = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            e = PyOCDTargetEntry.from_line(line)
            if e:
                entries.append(e)
    return entries


def ensure_index(log_service=None) -> List[PyOCDTargetEntry]:
    entries = load_index()
    has_pack_files = os.path.isdir(RUNTIME_PACKS_DIR) and bool(_glob.glob(os.path.join(RUNTIME_PACKS_DIR, '*.pack')))
    has_pack_entries = any(e.source == 'pack' for e in entries)
    if entries and (not has_pack_files or has_pack_entries):
        return entries
    if has_pack_files and not has_pack_entries and entries:
        if log_service:
            log_service.info('检测到新 Pack 文件，重新生成目标索引...')
    elif not entries:
        if log_service:
            log_service.info('首次使用，生成 PyOCD 目标索引...')
    entries = generate_index()
    if entries:
        save_index(entries)
        if log_service:
            log_service.info(f'已生成 {len(entries)} 个目标的索引')
    return entries


def refresh_index(log_service=None, progress_callback=None) -> List[PyOCDTargetEntry]:
    try:
        with open(RUNTIME_PYOCD_TARGETS_TXT, 'w', encoding='utf-8') as f:
            f.write('')
    except Exception:
        pass
    if log_service:
        log_service.info('刷新 PyOCD 目标索引...')
    entries = generate_index(progress_callback)
    if entries:
        save_index(entries)
        if log_service:
            log_service.info(f'已更新 {len(entries)} 个目标的索引')
    return entries


def find_pack_for_target(target_name: str, log_service=None) -> tuple:
    pyocd_exe = _get_pyocd_exe()
    if not pyocd_exe:
        return False, 'pyocd 未找到'
    try:
        result = subprocess.run(
            [pyocd_exe, '-m', 'pyocd', 'pack', 'find', target_name],
            capture_output=True, text=True, timeout=30,
            creationflags=_subprocess_flags(),
        )
        output = result.stdout + result.stderr
        if result.returncode == 0 and target_name.lower() in output.lower():
            lines = [l.strip() for l in output.strip().split('\n') if l.strip() and not l.strip().startswith('#')]
            return True, '\n'.join(lines) if lines else output.strip()
        return False, output.strip() if output.strip() else f'未找到 {target_name} 对应的 Pack'
    except Exception as e:
        return False, str(e)


def install_pack_for_target(target_name: str, progress_callback=None) -> tuple:
    pyocd_exe = _get_pyocd_exe()
    if not pyocd_exe:
        return False, 'pyocd 未找到'
    try:
        if progress_callback:
            progress_callback(f'正在查找 {target_name} 的 Pack...')

        find_result = subprocess.run(
            [pyocd_exe, '-m', 'pyocd', 'pack', 'find', target_name],
            capture_output=True, text=True, timeout=30,
            creationflags=_subprocess_flags(),
        )

        pack_dfp_names = set()
        for line in (find_result.stdout + find_result.stderr).strip().split('\n'):
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('-') or line.lower().startswith('part'):
                continue
            parts = line.split()
            if len(parts) >= 3:
                pack_dfp_names.add(parts[2])

        if progress_callback:
            progress_callback(f'正在下载 {target_name} 的 Pack...')

        result = subprocess.run(
            [pyocd_exe, '-m', 'pyocd', 'pack', 'install', target_name],
            capture_output=True, text=True, timeout=300,
            creationflags=_subprocess_flags(),
        )
        output = result.stdout + result.stderr

        if progress_callback:
            progress_callback('Pack 下载完成，正在复制到 runtime/packs/...')

        _copy_packs_to_runtime(pack_dfp_names)

        refresh_index(log_service=None, progress_callback=progress_callback)

        return result.returncode == 0, output.strip()
    except subprocess.TimeoutExpired:
        return False, 'Pack 下载超时(300秒)'
    except Exception as e:
        return False, str(e)


def _copy_packs_to_runtime(pack_dfp_names: set = None):
    import shutil
    os.makedirs(RUNTIME_PACKS_DIR, exist_ok=True)
    pack_cache_dirs = []
    local_app_data = os.environ.get('LOCALAPPDATA', '')
    if local_app_data:
        for sub in ['cmsis-pack-manager', 'cmsis-pack-manager/cmsis-pack-manager']:
            d = os.path.join(local_app_data, sub)
            if os.path.isdir(d):
                pack_cache_dirs.append(d)
    user_profile = os.environ.get('USERPROFILE', '')
    if user_profile:
        for rel in ['AppData/Local/cmsis-pack-manager', 'AppData/Local/cmsis-pack-manager/cmsis-pack-manager']:
            d = os.path.join(user_profile, rel)
            if os.path.isdir(d):
                pack_cache_dirs.append(d)
    existing = set(os.listdir(RUNTIME_PACKS_DIR)) if os.path.isdir(RUNTIME_PACKS_DIR) else set()
    skip_dirs = {'cmsis-pack-manager', 'Web', 'Downloads'}
    copied = 0
    for cache_dir in pack_cache_dirs:
        for pack_file in _glob.glob(os.path.join(cache_dir, '**', '*.pack'), recursive=True):
            rel_path = os.path.relpath(pack_file, cache_dir)
            parts = [p for p in rel_path.replace('\\', '/').split('/') if p not in skip_dirs]
            new_name = '_'.join(parts)

            if pack_dfp_names is not None:
                matched = False
                for dfp in pack_dfp_names:
                    dfp_parts = dfp.replace('.', '/')
                    if dfp.replace('.', '_') in new_name or dfp_parts in rel_path.replace('\\', '/'):
                        matched = True
                        break
                if not matched:
                    continue

            dest = os.path.join(RUNTIME_PACKS_DIR, new_name)
            if new_name in existing and os.path.isfile(dest) and os.path.getsize(pack_file) == os.path.getsize(dest):
                continue
            shutil.copy2(pack_file, dest)
            existing.add(new_name)
            copied += 1
    return copied
