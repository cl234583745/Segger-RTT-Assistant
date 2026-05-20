import logging

from PyQt5.QtCore import QObject, pyqtSignal

from ..processors.waveform_processor import AcquisitionState


logger = logging.getLogger(__name__)


class AcquisitionStateMachine(QObject):
    """示波器采集状态机，管理 idle ↔ running ↔ paused 三态转换。"""

    state_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = AcquisitionState.IDLE

    def current_state(self) -> AcquisitionState:
        return self._state

    def is_idle(self) -> bool:
        return self._state == AcquisitionState.IDLE

    def is_running(self) -> bool:
        return self._state == AcquisitionState.RUNNING

    def is_paused(self) -> bool:
        return self._state == AcquisitionState.PAUSED

    def start(self) -> bool:
        if self._state != AcquisitionState.IDLE:
            return False
        self._state = AcquisitionState.RUNNING
        logger.info("示波器: 开始采集")
        self.state_changed.emit(self._state.value)
        return True

    def stop(self) -> bool:
        if self._state == AcquisitionState.IDLE:
            return False
        self._state = AcquisitionState.IDLE
        logger.info("示波器: 停止采集")
        self.state_changed.emit(self._state.value)
        return True

    def pause(self) -> bool:
        if self._state != AcquisitionState.RUNNING:
            return False
        self._state = AcquisitionState.PAUSED
        logger.info("示波器: 暂停采集")
        self.state_changed.emit(self._state.value)
        return True

    def resume(self) -> bool:
        if self._state != AcquisitionState.PAUSED:
            return False
        self._state = AcquisitionState.RUNNING
        logger.info("示波器: 恢复采集")
        self.state_changed.emit(self._state.value)
        return True

    def on_device_disconnected(self) -> None:
        if self._state == AcquisitionState.IDLE:
            return
        self._state = AcquisitionState.IDLE
        logger.info("示波器: 设备断开，采集已自动停止")
        self.state_changed.emit(self._state.value)
