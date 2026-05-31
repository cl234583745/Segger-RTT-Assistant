from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class FirmwarePathRecord:
    path: str
    is_active: bool = False
    added_time: str = ''

    def __post_init__(self):
        if not self.added_time:
            self.added_time = datetime.now().isoformat()


    def to_dict(self) -> dict:
        return {
            'path': self.path,
            'is_active': self.is_active,
            'added_time': self.added_time,
        }

    @staticmethod
    def from_dict(d: dict) -> 'FirmwarePathRecord':
        return FirmwarePathRecord(
            path=d.get('path', ''),
            is_active=d.get('is_active', False),
            added_time=d.get('added_time', ''),
        )