from dataclasses import dataclass


_VALID_STATUSES = frozenset({'success', 'failure', 'timeout', 'aborted'})


@dataclass
class FlashResult:
    status: str
    firmware_path: str
    debugger_type: str
    chip_model: str
    start_time: str
    end_time: str
    error_message: str = ''
    log_output: str = ''

    def __post_init__(self):
        if self.status not in _VALID_STATUSES:
            self.status = 'failure'

    def to_dict(self) -> dict:
        return {
            'status': self.status,
            'firmware_path': self.firmware_path,
            'debugger_type': self.debugger_type,
            'chip_model': self.chip_model,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'error_message': self.error_message,
            'log_output': self.log_output,
        }

    @staticmethod
    def from_dict(d: dict) -> 'FlashResult':
        return FlashResult(
            status=d.get('status', 'failure'),
            firmware_path=d.get('firmware_path', ''),
            debugger_type=d.get('debugger_type', ''),
            chip_model=d.get('chip_model', ''),
            start_time=d.get('start_time', ''),
            end_time=d.get('end_time', ''),
            error_message=d.get('error_message', ''),
            log_output=d.get('log_output', ''),
        )