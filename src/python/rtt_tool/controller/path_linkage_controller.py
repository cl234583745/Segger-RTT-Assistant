import os
from PyQt5.QtCore import QObject, pyqtSignal

from ..utils.path_linkage_utils import PathLinkageUtils


class PathLinkageController(QObject):
    map_path_suggested = pyqtSignal(str)
    firmware_path_suggested = pyqtSignal(str)

    def __init__(self, config_service=None, log_service=None):
        super().__init__()
        self._config_service = config_service
        self._log_service = log_service
        self._linkage_enabled = True
        self._linkage_in_progress = False

    def on_firmware_path_changed(self, firmware_path: str, current_map_path: str = ''):
        if self._linkage_in_progress or not self._linkage_enabled:
            return
        if not firmware_path:
            return
        if current_map_path and current_map_path.strip():
            return

        fw_dir = PathLinkageUtils.get_directory(firmware_path)
        fw_basename = os.path.splitext(os.path.basename(firmware_path))[0]
        map_path = PathLinkageUtils.search_map_file(fw_dir, fw_basename)

        if map_path:
            self._linkage_in_progress = True
            self.map_path_suggested.emit(map_path)
            self._linkage_in_progress = False

    def on_map_path_changed(self, map_path: str, current_firmware_paths: list = None):
        if self._linkage_in_progress or not self._linkage_enabled:
            return
        if not map_path:
            return

        map_dir = PathLinkageUtils.get_directory(map_path)
        fw_path = PathLinkageUtils.search_firmware_file(map_dir, hex_priority=True)

        if fw_path:
            if current_firmware_paths and fw_path in current_firmware_paths:
                return
            self._linkage_in_progress = True
            self.firmware_path_suggested.emit(fw_path)
            self._linkage_in_progress = False

    def set_linkage_enabled(self, enabled: bool):
        self._linkage_enabled = enabled
