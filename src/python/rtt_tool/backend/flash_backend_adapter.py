from typing import Optional
from .flash_base import BaseFlashBackend
from .jlink_flash_backend import JLinkFlashBackend
from .pyocd_flash_backend import PyocdFlashBackend
from ..models.flash_params import FlashParams
from ..models.flash_result import FlashResult


class FlashBackendAdapter:

    def __init__(self, log_service=None):
        self._log_service = log_service
        self._jlink_backend: Optional[JLinkFlashBackend] = None
        self._pyocd_backend: Optional[PyocdFlashBackend] = None

    def get_backend(self, debugger_type: str) -> Optional[BaseFlashBackend]:
        if debugger_type == 'jlink':
            if self._jlink_backend is None:
                self._jlink_backend = JLinkFlashBackend()
            return self._jlink_backend
        elif debugger_type in ('daplink', 'stlink', 'pyocd'):
            if self._pyocd_backend is None:
                self._pyocd_backend = PyocdFlashBackend()
            return self._pyocd_backend
        return None

    def execute(self, params: FlashParams, progress_callback=None) -> FlashResult:
        backend = self.get_backend(params.debugger_type)
        if backend is None:
            import time
            now = time.strftime('%Y-%m-%dT%H:%M:%S')
            return FlashResult(
                status='failure',
                firmware_path=params.firmware_path,
                debugger_type=params.debugger_type,
                chip_model=params.chip_model,
                start_time=now,
                end_time=now,
                error_message=f'不支持的调试器类型: {params.debugger_type}',
            )
        if progress_callback is None:
            progress_callback = lambda _: None
        return backend.flash(params, progress_callback)