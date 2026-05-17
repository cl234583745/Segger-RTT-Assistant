from PyQt5.QtCore import QDateTime, pyqtSignal

from .base import DataProcessor
from ..utils.data_format_service import DataFormatService


class LogProcessor(DataProcessor):
    """文本日志数据处理器，处理通道0的文本数据。"""

    text_updated = pyqtSignal(int, str)

    def __init__(self, log_service=None, data_log_handle=None, parent=None):
        super().__init__(parent)
        self._log_service = log_service
        self._data_log_handle = data_log_handle
        self._hex_mode = False
        self._timestamp_enabled = False

    def process(self, channel: int, data: bytes) -> None:
        if channel != 0:
            return

        if self._hex_mode:
            text = DataFormatService.format_to_hex(data)
        else:
            text = data.decode('utf-8', errors='replace')

        if self._timestamp_enabled:
            timestamp = QDateTime.currentDateTime().toString("[yyyy-MM-dd hh:mm:ss.zzz] ")
            if '\n' in text:
                lines = text.split('\n')
                text = '\n'.join(timestamp + line if line else line for line in lines)
            else:
                text = timestamp + text

        if self._data_log_handle is not None:
            try:
                self._data_log_handle.write(data if isinstance(data, bytes) else data.encode('utf-8', errors='replace'))
                self._data_log_handle.flush()
            except Exception:
                pass

        self.text_updated.emit(channel, text)
        self.data_updated.emit(text)

    def get_supported_channels(self) -> list:
        return [0]

    def set_hex_mode(self, enabled: bool):
        self._hex_mode = enabled

    def set_timestamp_enabled(self, enabled: bool):
        self._timestamp_enabled = enabled

    def set_data_log_handle(self, handle):
        self._data_log_handle = handle
