from PyQt5.QtCore import QThread, pyqtSignal

from .base import DataProcessor


class VariableMonitorThread(QThread):
    """变量监视线程，定时读取目标MCU内存。"""

    variable_updated = pyqtSignal(str, object)
    error_occurred = pyqtSignal(str, str)

    def __init__(self, backend, interval_ms=100, parent=None):
        super().__init__(parent)
        self._backend = backend
        self._interval_ms = interval_ms
        self._variables = {}
        self._running = False

    def add_variable(self, name: str, address: int, var_type: str):
        self._variables[name] = {'address': address, 'type': var_type}

    def remove_variable(self, name: str):
        self._variables.pop(name, None)

    def run(self):
        self._running = True
        while self._running:
            for name, info in list(self._variables.items()):
                try:
                    value = self._backend.read_memory(info['address'], info['type'])
                    self.variable_updated.emit(name, value)
                except Exception as e:
                    self.error_occurred.emit(name, str(e))
            self.msleep(self._interval_ms)

    def stop(self):
        self._running = False
        self.wait()


class VariableMonitor(DataProcessor):
    """变量监视处理器，通过内存直读方式监视变量值。"""

    variable_updated = pyqtSignal(str, object)
    error_occurred = pyqtSignal(str, str)

    def __init__(self, backend=None, interval_ms=100, parent=None):
        super().__init__(parent)
        self._backend = backend
        self._interval_ms = interval_ms
        self._monitor_thread = None

    def set_backend(self, backend):
        self._backend = backend

    def start(self):
        if self._backend is None:
            return
        if self._monitor_thread is not None and self._monitor_thread.isRunning():
            return
        self._monitor_thread = VariableMonitorThread(
            self._backend, self._interval_ms
        )
        self._monitor_thread.variable_updated.connect(self.variable_updated)
        self._monitor_thread.error_occurred.connect(self.error_occurred)
        self._monitor_thread.start()

    def stop(self):
        if self._monitor_thread is not None:
            self._monitor_thread.stop()
            self._monitor_thread = None

    def add_variable(self, name: str, address: int, var_type: str):
        if self._monitor_thread is not None:
            self._monitor_thread.add_variable(name, address, var_type)

    def remove_variable(self, name: str):
        if self._monitor_thread is not None:
            self._monitor_thread.remove_variable(name)

    def process(self, channel: int, data: bytes) -> None:
        pass

    def get_supported_channels(self) -> list:
        return []
