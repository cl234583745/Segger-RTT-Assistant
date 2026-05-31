from dataclasses import dataclass


@dataclass(frozen=True)
class SubChannelId:
    rtt_channel: int
    field_index: int
    field_label: str
    rtt_channel_name: str = ""

    @classmethod
    def from_legacy_channel(cls, channel: int) -> 'SubChannelId':
        return cls(rtt_channel=channel, field_index=0, field_label="uint32", rtt_channel_name="")

    def to_display_name(self) -> str:
        ch_prefix = f"CH{self.rtt_channel}"
        return f"{ch_prefix}[{self.field_index + 1}]"

    def to_signal_key(self) -> tuple:
        return (self.rtt_channel, self.field_index)

    @property
    def channel(self) -> int:
        return self.rtt_channel