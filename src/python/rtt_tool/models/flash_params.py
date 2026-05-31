from dataclasses import dataclass


@dataclass
class FlashParams:
    firmware_path: str
    debugger_type: str
    chip_model: str
    interface: str
    speed: int
    serial_number: str = ''
    pyocd_target: str = ''
    connect_mode: str = 'under_reset'
    timeout: int = 120
    jlink_path: str = ''