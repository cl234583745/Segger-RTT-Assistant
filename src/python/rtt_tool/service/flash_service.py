from PyQt5.QtCore import QObject, QThread, pyqtSignal, QTimer
from datetime import datetime
import time

from ..backend.flash_backend_adapter import FlashBackendAdapter
from ..models.flash_params import FlashParams
from ..models.flash_result import FlashResult


class _FlashWorker(QThread):
    progress = pyqtSignal(str)
    completed = pyqtSignal(object)

    def __init__(self, flash_adapter: FlashBackendAdapter, params: FlashParams, parent=None):
        super().__init__(parent)
        self._adapter = flash_adapter
        self._params = params
        self._aborted = False

    def run(self):
        try:
            result = self._adapter.execute(
                self._params,
                progress_callback=self._on_progress,
            )
            if not self._aborted:
                self.completed.emit(result)
        except Exception as e:
            if not self._aborted:
                result = FlashResult(
                    status='failure',
                    firmware_path=self._params.firmware_path,
                    debugger_type=self._params.debugger_type,
                    chip_model=self._params.chip_model,
                    start_time='', end_time='',
                    error_message=str(e),
                )
                self.completed.emit(result)

    def _on_progress(self, text: str):
        if not self._aborted:
            self.progress.emit(text)

    def abort(self):
        self._aborted = True


class FlashService(QObject):
    flash_progress = pyqtSignal(str)
    flash_completed = pyqtSignal(object)
    flash_error = pyqtSignal(str)

    def __init__(self, log_service=None):
        super().__init__()
        self._log_service = log_service
        self._adapter = FlashBackendAdapter(log_service=log_service)
        self._worker: _FlashWorker = None
        self._timeout_timer: QTimer = None
        self._start_time: str = ''

    def start_flash(self, firmware_path: str, debugger_type: str, chip_model: str,
                    interface: str, speed: int, serial_number: str = '',
                    pyocd_target: str = '', timeout: int = 120,
                    jlink_path: str = '') -> bool:
        if self.is_flashing():
            return False

        params = FlashParams(
            firmware_path=firmware_path,
            debugger_type=debugger_type,
            chip_model=chip_model,
            interface=interface,
            speed=speed,
            serial_number=serial_number,
            pyocd_target=pyocd_target,
            jlink_path=jlink_path,
            timeout=timeout,
        )

        self._start_time = datetime.now().isoformat()
        self._log('info', f"开始烧录: 固件=[{firmware_path}], 调试器=[{debugger_type}], 芯片=[{chip_model}]")

        self._worker = _FlashWorker(self._adapter, params)
        self._worker.progress.connect(self._on_worker_progress)
        self._worker.completed.connect(self._on_worker_completed)

        self._timeout_timer = QTimer()
        self._timeout_timer.setSingleShot(True)
        self._timeout_timer.timeout.connect(self._on_flash_timeout)
        self._timeout_timer.start(timeout * 1000)

        self._worker.start()
        return True

    def is_flashing(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    def cancel_flash(self):
        if self._worker and self._worker.isRunning():
            self._worker.abort()
            self._log('warning', "烧录已取消")
        self._cleanup()

    def _on_worker_progress(self, text: str):
        self._log('debug', text)
        self.flash_progress.emit(text)

    def _on_worker_completed(self, result: FlashResult):
        self._cleanup()

        if not result.start_time:
            result.start_time = self._start_time
        if not result.end_time:
            result.end_time = datetime.now().isoformat()

        if result.status == 'success':
            elapsed = ''
            try:
                t1 = datetime.fromisoformat(result.start_time)
                t2 = datetime.fromisoformat(result.end_time)
                elapsed = f"{(t2 - t1).total_seconds():.1f}s"
            except Exception:
                pass
            self._log('info', f"烧录成功: 固件=[{result.firmware_path}], 耗时=[{elapsed}]")
        elif result.status == 'failure':
            self._log('error', f"烧录失败: 固件=[{result.firmware_path}], 错误=[{result.error_message}]")

        self.flash_completed.emit(result)

    def _on_flash_timeout(self):
        if self._worker and self._worker.isRunning():
            self._worker.abort()
            self._log('error', f"烧录超时: 固件=[{self._worker._params.firmware_path}], 超时=[{self._worker._params.timeout}]s")
            result = FlashResult(
                status='timeout',
                firmware_path=self._worker._params.firmware_path,
                debugger_type=self._worker._params.debugger_type,
                chip_model=self._worker._params.chip_model,
                start_time=self._start_time,
                end_time=datetime.now().isoformat(),
                error_message='烧录超时',
            )
            self.flash_completed.emit(result)
        self._cleanup()

    def _cleanup(self):
        if self._timeout_timer:
            self._timeout_timer.stop()
            self._timeout_timer = None
        if self._worker:
            self._worker.progress.disconnect()
            self._worker.completed.disconnect()
            if self._worker.isRunning():
                self._worker.abort()
                self._worker.wait(5000)
            self._worker = None

    def _log(self, level: str, msg: str):
        try:
            if self._log_service:
                getattr(self._log_service, level)(msg)
        except Exception:
            pass