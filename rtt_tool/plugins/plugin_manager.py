import os
import importlib
import importlib.util
from .plugin_base import Plugin


class PluginManager:
    """插件管理器，自动扫描、加载和管理插件。"""

    def __init__(self, plugins_dir=None, log_service=None):
        self._plugins = {}
        self._enabled = {}
        self._log_service = log_service
        self._plugins_dir = plugins_dir
        self._app_context = {}

    def _log(self, level, msg):
        if self._log_service:
            getattr(self._log_service, level)(msg)

    def set_app_context(self, context: dict):
        self._app_context = context

    def discover_plugins(self, plugins_dir: str = None):
        """扫描插件目录，发现可用插件。

        Args:
            plugins_dir: 插件目录路径，None则使用默认路径
        """
        if plugins_dir is None:
            plugins_dir = self._plugins_dir
        if plugins_dir is None or not os.path.isdir(plugins_dir):
            return

        for filename in os.listdir(plugins_dir):
            if filename.endswith('.py') and not filename.startswith('_'):
                filepath = os.path.join(plugins_dir, filename)
                try:
                    spec = importlib.util.spec_from_file_location(filename[:-3], filepath)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and
                                issubclass(attr, Plugin) and attr is not Plugin):
                            plugin = attr()
                            self._plugins[plugin.name] = plugin
                            self._enabled[plugin.name] = True
                            self._log('info', f'发现插件: {plugin.name} v{plugin.version}')
                except Exception as e:
                    self._log('warning', f'加载插件文件 {filename} 失败: {e}')

    def load_plugin(self, name: str):
        """加载并初始化指定插件。"""
        plugin = self._plugins.get(name)
        if plugin is None:
            raise ValueError(f"插件 '{name}' 不存在")
        try:
            plugin.on_load(self._app_context)
            self._enabled[name] = True
            self._log('info', f'插件 {name} 已加载')
        except Exception as e:
            self._enabled[name] = False
            self._log('error', f'插件 {name} 加载失败: {e}')

    def unload_plugin(self, name: str):
        """卸载指定插件。"""
        plugin = self._plugins.get(name)
        if plugin is not None:
            try:
                plugin.on_unload()
            except Exception as e:
                self._log('warning', f'插件 {name} 卸载载失败: {e}')
            self._enabled[name] = False

    def on_data(self, channel: int, data: bytes):
        """向所有启用的插件分发数据。"""
        for name, plugin in self._plugins.items():
            if self._enabled.get(name, False):
                try:
                    plugin.on_data(channel, data)
                except Exception as e:
                    self._log('warning', f'插件 {name} 处理数据异常: {e}')
                    self._enabled[name] = False

    def get_plugin(self, name: str) -> Plugin:
        return self._plugins.get(name)

    def list_plugins(self) -> list:
        return [(name, plugin.version, self._enabled.get(name, False))
                for name, plugin in self._plugins.items()]
