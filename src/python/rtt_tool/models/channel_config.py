from dataclasses import dataclass, field
from typing import Dict


DEFAULT_CHANNEL_COLORS = [
    '#00FF00', '#FF6600', '#00AAFF', '#FF00FF',
    '#FFFF00', '#00FFFF', '#FF8888', '#88FF88',
    '#AA88FF', '#FFAA88',
]

V_DIV_STEPS = [
    0.001, 0.002, 0.005,
    0.01, 0.02, 0.05,
    0.1, 0.2, 0.5,
    1, 2, 5,
    10, 20, 50,
    100, 200, 500,
    1000, 2000, 5000,
]

DRAW_STYLES = ["线条", "点", "线+点", "矩形"]


@dataclass
class ChannelConfig:
    channel: int
    name: str = ''
    color: str = '#00FF00'
    style: int = 0
    vdiv: float = 1.0
    yoffset: float = 0.0
    enabled: bool = True

    def __post_init__(self):
        if not self.name:
            self.name = f"CH{self.channel}"

    @staticmethod
    def default(channel: int) -> 'ChannelConfig':
        return ChannelConfig(
            channel=channel,
            name=f"CH{channel}",
            color=DEFAULT_CHANNEL_COLORS[(channel - 1) % len(DEFAULT_CHANNEL_COLORS)],
            style=0,
            vdiv=1.0,
            yoffset=0.0,
            enabled=True,
        )

    def to_dict(self) -> dict:
        return {
            'channel': self.channel,
            'name': self.name,
            'color': self.color,
            'style': self.style,
            'vdiv': self.vdiv,
            'yoffset': self.yoffset,
            'enabled': self.enabled,
        }

    @staticmethod
    def from_dict(d: dict) -> 'ChannelConfig':
        return ChannelConfig(
            channel=d.get('channel', 1),
            name=d.get('name', ''),
            color=d.get('color', '#00FF00'),
            style=d.get('style', 0),
            vdiv=d.get('vdiv', 1.0),
            yoffset=d.get('yoffset', 0.0),
            enabled=d.get('enabled', True),
        )


@dataclass
class PanelState:
    collapsed: bool = True
    collapsed_width: int = 40
    expanded_width: int = 240


@dataclass
class AutoDetectState:
    enabled: bool = True
    threshold: int = 3
    detection_counts: Dict[int, int] = field(default_factory=dict)


class ChannelRoute:

    @staticmethod
    def rtt_to_display(rtt_channel: int) -> int:
        return rtt_channel

    @staticmethod
    def display_to_rtt(display_channel: int) -> int:
        return display_channel
