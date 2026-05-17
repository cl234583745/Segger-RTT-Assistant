import csv
import os
from PyQt5.QtCore import QThread, pyqtSignal


class DataReplayThread(QThread):
    """数据回放线程，从CSV文件逐行回放数据。"""

    data_ready = pyqtSignal(int, bytes)
    replay_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, filepath: str, interval_ms: int = 10, parent=None):
        super().__init__(parent)
        self._filepath = filepath
        self._interval_ms = interval_ms
        self._running = False

    def run(self):
        self._running = True
        try:
            with open(self._filepath, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if not self._running:
                        break
                    if len(row) >= 3:
                        try:
                            channel = int(row[1]) if row[1].isdigit() else 0
                            data = row[2].encode('utf-8', errors='replace')
                            self.data_ready.emit(channel, data)
                        except (ValueError, IndexError):
                            continue
                    self.msleep(self._interval_ms)
            self.replay_finished.emit()
        except Exception as e:
            self.error_occurred.emit(str(e))

    def stop(self):
        self._running = False
        self.wait()


class DataReplayService:
    """数据回放服务。"""

    def __init__(self):
        self._thread = None

    def start_replay(self, filepath: str, interval_ms: int = 10):
        """开始回放。

        Args:
            filepath: CSV 文件路径
            interval_ms: 回放间隔(ms)
        """
        self.stop_replay()
        self._thread = DataReplayThread(filepath, interval_ms)
        self._thread.start()
        return self._thread

    def stop_replay(self):
        if self._thread is not None:
            self._thread.stop()
            self._thread = None
