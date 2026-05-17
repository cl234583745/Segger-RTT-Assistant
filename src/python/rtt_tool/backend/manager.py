import time

from .base import DebuggerBackend


class DebuggerManager:
    CACHE_TTL = 5.0

    def __init__(self, log_service=None, enabled_backends=None):
        self._log_service = log_service
        self._backends = {}
        self._current_backend = None
        self._probe_cache = None
        self._probe_cache_time = 0

        if enabled_backends is None:
            enabled_backends = ['jlink', 'pyocd']

        if 'jlink' in enabled_backends:
            try:
                from .jlink_backend import JLinkBackend
                self._backends['jlink'] = JLinkBackend(log_service=log_service)
                self._log('info', '已注册 J-Link 后端')
            except Exception as e:
                self._log('warning', f'J-Link 后端注册失败: {e}')

        if 'pyocd' in enabled_backends or 'stlink' in enabled_backends:
            try:
                from .pyocd_backend import PyOCDBackend
                pyocd_backend = PyOCDBackend(log_service=log_service)
                if pyocd_backend._pyocd_available:
                    self._backends['pyocd'] = pyocd_backend
                    self._log('info', '已注册 PyOCD 后端 (DAP-Link/ST-Link)')
                else:
                    self._log('warning', 'PyOCD 未安装，DAP-Link/ST-Link 不可用')
            except Exception as e:
                self._log('warning', f'PyOCD 后端注册失败: {e}')

    def _log(self, level, msg):
        if self._log_service:
            getattr(self._log_service, level)(msg)

    def _clear_backend_caches(self):
        for name, backend in self._backends.items():
            try:
                if hasattr(backend, '_probe_cache'):
                    backend._probe_cache = None
                    backend._probe_cache_time = 0
            except Exception:
                pass

    def detect_all_probes(self, force=False) -> list:
        now = time.time()
        if not force and self._probe_cache is not None and (now - self._probe_cache_time) < self.CACHE_TTL:
            self._log('info', f'使用缓存的探针列表 ({len(self._probe_cache)} 个)')
            return self._probe_cache

        if force:
            self._clear_backend_caches()

        probes = []
        for name, backend in self._backends.items():
            try:
                backend_probes = backend.get_probe_list(force=force)
                probes.extend(backend_probes)
                self._log('info', f'{name} 后端探测到 {len(backend_probes)} 个探针')
            except Exception as e:
                self._log('error', f'探测 {name} 后端失败: {type(e).__name__}: {e}')

        if not probes and not force:
            import time as _time
            self._log('info', '初次探测未发现探针，500ms后重试...')
            _time.sleep(0.5)
            self._clear_backend_caches()
            for name, backend in self._backends.items():
                try:
                    backend_probes = backend.get_probe_list(force=True)
                    probes.extend(backend_probes)
                    self._log('info', f'{name} 后端重探测到 {len(backend_probes)} 个探针')
                except Exception as e:
                    self._log('error', f'重探测 {name} 后端失败: {type(e).__name__}: {e}')

        seen = {}
        for p in probes:
            sn = p.get('serial', '')
            if not sn:
                continue
            if sn in seen:
                existing = seen[sn]
                if p.get('backend') == 'jlink' and existing.get('backend') != 'jlink':
                    seen[sn] = p
            else:
                seen[sn] = p
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
        backend = self._backends.get(backend_type)
        if backend is None:
            available = ', '.join(self._backends.keys())
            raise ValueError(f"后端 '{backend_type}' 不可用，可用后端: {available}")
        self._current_backend = backend
        self._log('info', f'已切换到 {backend_type} 后端')
        return self._current_backend

    def get_backend(self, backend_type: str) -> DebuggerBackend:
        backend = self._backends.get(backend_type)
        if backend is None:
            available = ', '.join(self._backends.keys())
            raise ValueError(f"后端 '{backend_type}' 不可用，可用后端: {available}")
        return backend

    @property
    def current_backend(self) -> DebuggerBackend:
        return self._current_backend

    @property
    def available_types(self) -> list:
        return list(self._backends.keys())
