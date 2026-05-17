from abc import ABCMeta, abstractmethod
from PyQt5.QtCore import QObject, pyqtSignal


class _ABCQObjectMeta(type(QObject), ABCMeta):
    """合并 PyQt5 元类和 ABCMeta 的元类，解决多重继承冲突。"""
    pass


class DataProcessor(QObject, metaclass=_ABCQObjectMeta):
    """数据处理器抽象基类，定义统一的数据处理接口。

    所有数据处理器（LogProcessor、WaveformProcessor等）必须继承此类。
    """

    data_updated = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)

    @abstractmethod
    def process(self, channel: int, data: bytes) -> None:
        """处理接收到的数据。

        Args:
            channel: RTT 通道号
            data: 原始字节数据
        """
        pass

    @abstractmethod
    def get_supported_channels(self) -> list:
        """返回此处理器支持的通道号列表。

        Returns:
            通道号列表，如 [0] 或 [1, 2]
        """
        pass

    def reset(self) -> None:
        """重置处理器状态（虚方法，默认空实现）。"""
        pass
