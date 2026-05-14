import time

from .jlink_backend import JLinkBackend
from .base import DebuggerBackend


class DebuggerManager:
    """管理所有调试器后端，实现自动探测和切换。"""

    CACHE_TTL = 5.0

    def __init__(self, log_service=None):
        self._log_service = log_service
        self._backends = {}
        self._current_backend = None
        self._probe_cache = None
        self._probe_cache_time = 0

        self._backends['jlink'] = JLinkBackend(log_service=log_service)
        self._log('info', '已注册 J-Link 后端')

        try:
            from .pyocd_backend import PyOCDBackend
            pyocd_backend = PyOCDBackend(log_service=log_service)
            if pyocd_backend._pyocd_available:
                self._backends['pyocd'] = pyocd_backend
                self._log('info', '已注册 PyOCD 后端')
            else:
                self._log('warning', 'PyOCD 未安装，DAP-Link/ST-Link 不可用')
        except Exception as e:
            self._log('warning', f'PyOCD 后端注册失败: {e}')

    def _log(self, level, msg):
        if self._log_service:
            getattr(self._log_service, level)(msg)

    def detect_all_probes(self, force=False) -> list:
        """探测所有已连接的调试器探针（带缓存）。

        Args:
            force: 强制刷新缓存

        Returns:
            探针信息列表
        """
        now = time.time()
        if not force and self._probe_cache is not None and (now - self._probe_cache_time) < self.CACHE_TTL:
            self._log('info', f'使用缓存的探针列表 ({len(self._probe_cache)} 个)')
            return self._probe_cache

        probes = []
        for name, backend in self._backends.items():
            try:
                backend_probes = backend.get_probe_list()
                probes.extend(backend_probes)
                self._log('info', f'{name} 后端探测到 {len(backend_probes)} 个探针')
            except Exception as e:
                self._log('error', f'探测 {name} 后端失败: {type(e).__name__}: {e}')

        # 按序列号去重：同一物理探针被多后端检测到时，保留 J-Link 后端（优先）
        seen = {}
        for p in probes:
            sn = p.get('serial', '')
            if not sn:
                continue
            if sn in seen:
                existing = seen[sn]
                if p.get('backend') == 'jlink' and existing.get('backend') != 'jlink':
                    seen[sn] = p  # J-Link 优先级更高
            else:
                seen[sn] = p
        # 去重（保留 seen 中的替换结果 + 无序列号的探针）
        deduped = list(seen.values())
        for p in probes:
            if not p.get('serial', ''):
                deduped.append(p)
        if len(deduped) != len(probes):
            self._log('info', f'去重后剩余 {len(deduped)} 个探针')
        probes = deduped

        self._probe_cache = probes
        self._probe_cache_time = now
        return probes

    def select_backend(self, backend_type: str) -> DebuggerBackend:
        """根据类型选择并切换当前后端。"""
        backend = self._backends.get(backend_type)
        if backend is None:
            available = ', '.join(self._backends.keys())
            raise ValueError(f"后端 '{backend_type}' 不可用，可用后端: {available}")
        self._current_backend = backend
        self._log('info', f'已切换到 {backend_type} 后端')
        return self._current_backend

    def get_backend(self, backend_type: str) -> DebuggerBackend:
        """获取后端实例（不切换当前后端）。"""
        backend = self._backends.get(backend_type)
        if backend is None:
            available = ', '.join(self._backends.keys())
            raise ValueError(f"后端 '{backend_type}' 不可用，可用后端: {available}")
        return backend

    @property
    def current_backend(self) -> DebuggerBackend:
        """当前活跃的后端实例。"""
        return self._current_backend

    @property
    def available_types(self) -> list:
        """可用的后端类型列表。"""
        return list(self._backends.keys())
