import os
import sys
import time
import json
import glob as _glob
from dataclasses import dataclass, asdict
from typing import List, Optional

from .path_config import (
    RUNTIME_PYOCD_TARGETS_TXT, RUNTIME_VENV_SCRIPTS, RUNTIME_PACKS_DIR,
    RUNTIME_VENV_SITE_PACKAGES,
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


def _pack_cache_dir():
    d = os.path.join(os.path.dirname(RUNTIME_PYOCD_TARGETS_TXT), _PACK_CACHE_SUBDIR)
    os.makedirs(d, exist_ok=True)
    return d


def _pack_cache_path(pack_name: str) -> str:
    safe = pack_name.replace('.', '_').replace(' ', '_')
    return os.path.join(_pack_cache_dir(), safe + '.json')


def _pack_signature(pack_path: str) -> Optional[tuple]:
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


def _cpm_cache_dir():
    d = os.path.join(os.path.dirname(RUNTIME_PACKS_DIR), 'cpm_cache')
    os.makedirs(d, exist_ok=True)
    return d


def _get_cpm_cache(progress_callback=None):
    try:
        from cmsis_pack_manager.pack_manager import Cache
        cpm_dir = _cpm_cache_dir()
        cache = Cache(silent=True, __=None, json_path=cpm_dir, data_path=cpm_dir)
        if not cache.index:
            if progress_callback:
                progress_callback('正在下载 Pack 索引（需联网，约1-2分钟）...')
            import threading
            exc = [None]
            def _download():
                try:
                    cache.cache_descriptors()
                except Exception as e:
                    exc[0] = e
            t = threading.Thread(target=_download, daemon=True)
            t.start()
            t.join(timeout=180)
            if t.is_alive():
                if progress_callback:
                    progress_callback('下载索引超时（3分钟），请检查网络后重试')
                return None
            if exc[0] is not None:
                return None
            cache = Cache(silent=True, __=None, json_path=cpm_dir, data_path=cpm_dir)
        return cache
    except Exception:
        return None


def find_pack_for_target(target_name: str, log_service=None) -> tuple:
    cache = _get_cpm_cache()
    if cache is None:
        return False, 'cmsis_pack_manager 不可用（请检查网络连接或重试）'
    try:
        matches = {k: v for k, v in cache.index.items() if target_name.lower() in k.lower()}
        if not matches:
            return False, f'未找到 {target_name} 对应的 Pack'
        lines = []
        for name, info in sorted(matches.items()):
            fp = info.get('from_pack', {})
            vendor = fp.get('vendor', '')
            pack = fp.get('pack', '')
            version = fp.get('version', '')
            lines.append(f'{name}\t{vendor}\t{pack}\t{version}')
        return True, '\n'.join(lines)
    except Exception as e:
        return False, str(e)


def _download_pack_direct(vendor, pack, version, base_url, dest_dir, progress_callback=None):
    """直接用 urllib 下载 .pack 文件到指定目录，绕过 cpm 的 .pdsc 机制。"""
    import urllib.request
    import urllib.error
    pack_filename = f'{vendor}.{pack}.{version}.pack'
    dest_path = os.path.join(dest_dir, pack_filename)
    if os.path.isfile(dest_path):
        if progress_callback:
            progress_callback(f'  {pack_filename} 已存在，跳过')
        return True
    pack_url = base_url.rstrip('/') + '/' + pack_filename
    if progress_callback:
        progress_callback(f'  下载 {pack_url}')
    try:
        req = urllib.request.Request(pack_url, headers={
            'User-Agent': 'RTT-Assistant/1.0',
            'Accept': '*/*',
        })
        with urllib.request.urlopen(req, timeout=60) as resp:
            total = int(resp.headers.get('Content-Length', 0))
            if progress_callback and total:
                size_mb = total / 1024 / 1024
                progress_callback(f'  文件大小: {size_mb:.1f}MB，下载中请耐心等待...')
            downloaded = 0
            last_pct = -1
            with open(dest_path, 'wb') as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = downloaded * 100 // total
                        if pct != last_pct and pct % 10 == 0:
                            last_pct = pct
                            if progress_callback:
                                progress_callback(f'  下载进度: {pct}% ({downloaded/1024/1024:.1f}/{total/1024/1024:.1f}MB)')
        if os.path.isfile(dest_path) and os.path.getsize(dest_path) > 0:
            return True
        else:
            if os.path.isfile(dest_path):
                os.remove(dest_path)
            return False
    except Exception as e:
        if os.path.isfile(dest_path):
            os.remove(dest_path)
        if progress_callback:
            progress_callback(f'  下载失败: {e}')
        return False


def install_pack_for_target(target_name: str, progress_callback=None, url_callback=None) -> tuple:
    cache = _get_cpm_cache(progress_callback)
    if cache is None:
        return False, 'cmsis_pack_manager 不可用（请检查网络连接或重试）'
    try:
        if progress_callback:
            progress_callback(f'正在查找 {target_name} 的 Pack...')

        matches = {k: v for k, v in cache.index.items() if target_name.lower() in k.lower()}
        if not matches:
            return False, f'未找到 {target_name} 对应的 Pack'

        pack_info = {}
        for info in matches.values():
            fp = info.get('from_pack', {})
            vendor = fp.get('vendor', '')
            pack = fp.get('pack', '')
            version = fp.get('version', '')
            url = fp.get('url', '')
            if vendor and pack and version and url:
                key = f'{vendor}.{pack}.{version}'
                if key not in pack_info:
                    pack_info[key] = (vendor, pack, version, url)

        if not pack_info:
            return False, f'未找到 {target_name} 对应的 Pack 下载信息'

        os.makedirs(RUNTIME_PACKS_DIR, exist_ok=True)
        failed = []
        for key, (vendor, pack, version, url) in pack_info.items():
            pack_url = url.rstrip('/') + '/' + f'{vendor}.{pack}.{version}.pack'
            if url_callback:
                url_callback(pack_url)
            if progress_callback:
                progress_callback(f'正在下载 {vendor}.{pack} v{version}...')
            ok = _download_pack_direct(vendor, pack, version, url, RUNTIME_PACKS_DIR, progress_callback)
            if not ok:
                failed.append(key)

        if failed:
            return False, f'Pack 下载失败: {", ".join(failed)}（请检查网络连接，或手动下载到 {RUNTIME_PACKS_DIR}）'

        if progress_callback:
            progress_callback('Pack 下载完成，刷新目标索引...')

        refresh_index(log_service=None, progress_callback=progress_callback)

        names = [f'{v}.{p}' for v, p, _, _ in pack_info.values()]
        return True, f'已下载 {len(pack_info)} 个 Pack: {", ".join(names)}'
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
