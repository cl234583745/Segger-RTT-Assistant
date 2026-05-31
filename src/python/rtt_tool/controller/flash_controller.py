import os
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QMessageBox

from ..service.flash_service import FlashService
from ..models.flash_result import FlashResult
from ..i18n import _ as i18n


class FlashController(QObject):
    flash_started = pyqtSignal()
    flash_finished = pyqtSignal(bool, str)
    flash_button_state_changed = pyqtSignal(bool)

    def __init__(self, flash_service: FlashService, config_service, log_service=None, parent_window=None):
        super().__init__()
        self._flash_service = flash_service
        self._config_service = config_service
        self._log_service = log_service
        self._parent_window = parent_window

        self._flash_service.flash_completed.connect(self._on_flash_completed)
        self._flash_service.flash_error.connect(self._on_flash_error)

    def request_flash(self, firmware_path: str) -> bool:
        is_valid, error_msg = self.validate_flash_params(firmware_path)
        if not is_valid:
            self._log('warning', f"烧录参数校验失败: {error_msg}")
            self._show_error(error_msg)
            self.flash_finished.emit(False, error_msg)
            return False

        debugger_type = self._config_service.get('debugger_type', 'jlink')
        chip_model = self._config_service.get('last_device', '') or self._config_service.get('device', '')
        interface = self._config_service.get('interface', 'SWD')
        speed = self._config_service.get('speed', 4000)
        serial_number = self._config_service.get('last_serial_number', '') or ''
        pyocd_target = self._config_service.get('pyocd_target', '') or ''
        jlink_path = self._config_service.get('jlink_path', '') or ''

        if not chip_model:
            msg = i18n('error.flash_params_incomplete') + '\n(芯片型号未配置)'
            self._log('warning', f"烧录参数校验失败: {msg}")
            self._show_error(msg)
            self.flash_finished.emit(False, msg)
            return False

        fw_ext = os.path.splitext(firmware_path)[1].lower()
        if debugger_type in ('daplink', 'stlink', 'pyocd') and fw_ext == '.srec':
            elf_path = os.path.splitext(firmware_path)[0] + '.elf'
            hex_path = os.path.splitext(firmware_path)[0] + '.hex'
            if not os.path.isfile(elf_path) and not os.path.isfile(hex_path):
                msg = f"pyocd不支持.srec格式\n请选择.elf或.hex文件"
                self._log('warning', msg)
                self._show_error(msg)
                self.flash_finished.emit(False, msg)
                return False

        started = self._flash_service.start_flash(
            firmware_path=firmware_path,
            debugger_type=debugger_type,
            chip_model=chip_model,
            interface=interface,
            speed=speed,
            serial_number=serial_number,
            pyocd_target=pyocd_target,
            jlink_path=jlink_path,
        )

        if started:
            self.flash_started.emit()
            self.flash_button_state_changed.emit(False)
        return started

    def validate_flash_params(self, firmware_path: str) -> tuple:
        if not firmware_path:
            return False, '固件文件路径为空'
        if not os.path.isfile(firmware_path):
            return False, f'固件文件不存在:\n{firmware_path}'
        if not os.access(firmware_path, os.R_OK):
            return False, f'固件文件不可读:\n{firmware_path}'
        debugger_type = self._config_service.get('debugger_type', '')
        if not debugger_type:
            return False, '请先配置调试器类型'
        return True, ''

    def is_flashing(self) -> bool:
        return self._flash_service.is_flashing()

    def _on_flash_completed(self, result: FlashResult):
        success = result.status == 'success'
        error_msg = result.error_message if not success else ''
        self.flash_finished.emit(success, error_msg)
        self.flash_button_state_changed.emit(True)
        if not success and error_msg:
            self._show_error(f"{i18n('status.flash_failed')}\n\n{error_msg}")

    def _on_flash_error(self, error_msg: str):
        self.flash_finished.emit(False, error_msg)
        self.flash_button_state_changed.emit(True)
        self._show_error(error_msg)

    def _show_error(self, msg: str):
        try:
            QMessageBox.warning(self._parent_window, i18n('btn.flash'), msg)
        except Exception:
            pass

    def _log(self, level: str, msg: str):
        try:
            if self._log_service:
                getattr(self._log_service, level)(msg)
        except Exception:
            pass
