from abc import ABC, abstractmethod
from PyQt5.QtWidgets import QWidget


class Plugin(ABC):
    """插件基类，定义插件接口。"""

    @property
    @abstractmethod
    def name(self) -> str:
        """插件名称"""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """插件版本"""
        pass

    @abstractmethod
    def on_load(self, app_context: dict):
        """加载插件时调用。

        Args:
            app_context: 包含 backend, ui, config 等对象的上下文字典
        """
        pass

    @abstractmethod
    def on_data(self, channel: int, data: bytes):
        """接收到 RTT 数据时调用。"""
        pass

    def on_unload(self):
        """卸载插件时调用（可选）。"""
        pass

    def get_config_widget(self) -> QWidget:
        """返回插件配置界面（可选）。"""
        return None
