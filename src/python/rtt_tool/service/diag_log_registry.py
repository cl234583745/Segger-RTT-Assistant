#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
from dataclasses import dataclass
from ..runtime.path_config import RUNTIME_LOG_DIR

_LEVEL_MAP = {
    'DEBUG': logging.DEBUG, 'INFO': logging.INFO,
    'WARNING': logging.WARNING, 'ERROR': logging.ERROR,
}
_LEVEL_NAMES = {v: k for k, v in _LEVEL_MAP.items()}


@dataclass(frozen=True)
class DiagLogTarget:
    name: str
    file_name: str
    description: str
    logger_name: str


_DIAG_LOG_TARGETS = [
    DiagLogTarget(
        name='rtt_system', file_name='rtt_system.log',
        description='应用诊断日志', logger_name='rtt_system'),
    DiagLogTarget(
        name='pyocd_diag', file_name='pyocd_diag.log',
        description='PyOCD连接诊断', logger_name='pyocd_diag'),
    DiagLogTarget(
        name='rtt_debug', file_name='rtt_debug.log',
        description='PyOCD库内部诊断', logger_name='pyocd'),
]


class DiagLogRegistry:
    def __init__(self, config_service=None):
        self._config_service = config_service

    def get_all_targets(self):
        return list(_DIAG_LOG_TARGETS)

    def get_log_file_path(self, target):
        return os.path.join(RUNTIME_LOG_DIR, target.file_name)

    def get_file_size(self, target):
        path = self.get_log_file_path(target)
        try:
            return os.path.getsize(path) if os.path.exists(path) else 0
        except OSError:
            return 0

    def get_log_level(self, target):
        if target.name == 'pyocd_diag':
            if self._config_service:
                return self._config_service.get(f'log_level.{target.name}', 'INFO')
            return 'INFO'
        try:
            logger = logging.getLogger(target.logger_name)
            level = logger.level or logging.WARNING
            return _LEVEL_NAMES.get(level, 'WARNING')
        except Exception:
            return 'UNKNOWN'

    def clear_log_file(self, target):
        path = self.get_log_file_path(target)
        try:
            if os.path.exists(path):
                with open(path, 'w', encoding='utf-8') as f:
                    pass
            return True, ''
        except PermissionError as e:
            return False, f'权限不足: {e}'
        except OSError as e:
            return False, f'清空失败: {e}'

    @staticmethod
    def format_file_size(size_bytes):
        if size_bytes < 1024:
            return f'{size_bytes} B'
        elif size_bytes < 1024 * 1024:
            return f'{size_bytes / 1024:.1f} KB'
        elif size_bytes < 1024 * 1024 * 1024:
            return f'{size_bytes / (1024 * 1024):.1f} MB'
        else:
            return f'{size_bytes / (1024 * 1024 * 1024):.1f} GB'
