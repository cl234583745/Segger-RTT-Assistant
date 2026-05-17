import sys
import os
import glob as _glob
from typing import Optional
import logging

from ..runtime.path_config import (
    RUNTIME_DIR, RUNTIME_DLL_DIR, RUNTIME_PACKS_DIR,
    RUNTIME_CONFIG_DIR, RUNTIME_PYOCD_YAML, get_app_root,
)

logger = logging.getLogger(__name__)


def is_frozen() -> bool:
    return getattr(sys, 'frozen', False)


def get_base_dir() -> str:
    if is_frozen():
        try:
            return sys._MEIPASS
        except AttributeError:
            logger.warning("打包环境但sys._MEIPASS不存在，降级到exe所在目录")
            return os.path.dirname(sys.executable)
    else:
        return get_app_root()


def get_exe_dir() -> str:
    if is_frozen():
        return os.path.dirname(sys.executable)
    else:
        return get_app_root()


def get_runtime_dir() -> str:
    return RUNTIME_DIR


def get_external_file(filename: str) -> Optional[str]:
    search_dirs = [RUNTIME_DLL_DIR, get_exe_dir()]
    cwd = os.path.abspath(os.getcwd())
    if cwd not in search_dirs:
        search_dirs.append(cwd)

    for d in search_dirs:
        path = os.path.join(d, filename)
        if os.path.exists(path):
            logger.debug(f"外部文件找到: {filename} -> {path}")
            return path

    logger.warning(f"外部文件未找到: {filename} (搜索目录: {search_dirs})")
    return None


def sync_pyocd_yaml() -> tuple:
    packs_dir = RUNTIME_PACKS_DIR
    yaml_path = RUNTIME_PYOCD_YAML

    pack_files = sorted(_glob.glob(os.path.join(packs_dir, '*.pack'))) if os.path.isdir(packs_dir) else []

    lines = ['pack:']
    yaml_dir = os.path.dirname(os.path.abspath(yaml_path))
    for pf in pack_files:
        rel_path = os.path.relpath(os.path.abspath(pf), yaml_dir).replace('\\', '/')
        lines.append(f'  - {rel_path}')
    new_content = '\n'.join(lines) + '\n'

    old_content = ''
    if os.path.exists(yaml_path):
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                old_content = f.read()
        except Exception:
            pass

    if new_content != old_content:
        try:
            with open(yaml_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            logger.info(f"pyocd.yaml 已同步: {len(pack_files)} 个Pack")
            return (True, len(pack_files), yaml_path)
        except Exception as e:
            logger.warning(f"pyocd.yaml 同步失败: {e}")
            return (False, len(pack_files), yaml_path)

    return (False, len(pack_files), yaml_path)


def get_resource_path(relative_path: str) -> Optional[str]:
    base_dir = get_app_root()
    absolute_path = os.path.join(base_dir, relative_path)
    absolute_path = os.path.abspath(absolute_path)

    if os.path.exists(absolute_path):
        logger.debug(f"资源路径解析成功: {relative_path} -> {absolute_path}")
        return absolute_path
    else:
        logger.warning(f"资源文件不存在: {absolute_path} (base={base_dir}, relative={relative_path})")
        return None
