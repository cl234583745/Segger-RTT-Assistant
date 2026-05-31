import logging

from .jscope_parser import parse_packet
from ..models.sub_channel_id import SubChannelId


logger = logging.getLogger(__name__)


class SubChannelSplitter:
    """子通道拆分器，一次遍历O(N)完成JScope包解析和子通道拆分。"""

    def parse_and_split(self, channel: int, data: bytes, fields: list,
                        residual_buffer: bytes = b'',
                        rtt_channel_name: str = "") -> tuple:
        """
        解析JScope数据并拆分到各子通道。

        Args:
            channel: RTT通道号
            data: 本次读取的原始字节数据
            fields: JScope字段定义列表
            residual_buffer: 上次残留的残缺数据
            rtt_channel_name: RTT通道名(用于生成子通道显示名)

        Returns:
            (sub_channel_data, new_residual, hw_timestamps_per_packet)
            sub_channel_data: dict, key=SubChannelId, value={'values': list, 'timestamps': list}
            new_residual: bytes, 新的残缺缓冲区
            hw_timestamps_per_packet: list, 每个包的硬件时间戳(可能为None)
        """
        packet_size = sum(f['size'] for f in fields)
        if packet_size <= 0:
            return ({}, b'', [])

        data_fields = [f for f in fields if not f.get('is_timestamp')]

        if residual_buffer:
            if len(residual_buffer) >= packet_size:
                logger.warning(
                    f"CH{channel} 残缺缓冲区异常: len={len(residual_buffer)} >= "
                    f"packet_size={packet_size}, 清空重置")
                residual_buffer = b''
            aligned_data = residual_buffer + data
            logger.debug(
                f"CH{channel} 拼接残缺: residual={len(residual_buffer)}B + "
                f"new={len(data)}B -> aligned={len(aligned_data)}B")
        else:
            aligned_data = data

        if len(aligned_data) < packet_size:
            logger.debug(
                f"CH{channel} 数据不足一个包: {len(aligned_data)}B < {packet_size}B, 存入残缺缓冲区")
            return ({}, aligned_data, [])

        sub_channel_data = {}
        for fi, df in enumerate(data_fields):
            sub_ch_id = SubChannelId(
                rtt_channel=channel,
                field_index=fi,
                field_label=df['label'],
                rtt_channel_name=rtt_channel_name
            )
            sub_channel_data[sub_ch_id] = {'values': [], 'timestamps': []}

        hw_timestamps_per_packet = []

        i = 0
        while i + packet_size <= len(aligned_data):
            result = parse_packet(aligned_data, fields, offset=i)
            if result is None:
                break

            packet_ts = result['timestamp']
            hw_timestamps_per_packet.append(packet_ts)

            for fi in range(len(data_fields)):
                sub_ch_id = SubChannelId(
                    rtt_channel=channel,
                    field_index=fi,
                    field_label=data_fields[fi]['label'],
                    rtt_channel_name=rtt_channel_name
                )
                sub_channel_data[sub_ch_id]['values'].append(result['values'][fi])
                sub_channel_data[sub_ch_id]['timestamps'].append(packet_ts)

            i += packet_size

        tail_len = len(aligned_data) - i
        new_residual = aligned_data[i:] if tail_len > 0 else b''
        if tail_len > 0:
            logger.debug(f"CH{channel} 保存残缺: {tail_len}B")

        return (sub_channel_data, new_residual, hw_timestamps_per_packet)

    def parse_and_split_legacy(self, channel: int, data: bytes, fields: list,
                               residual_buffer: bytes = b'') -> tuple:
        """
        独立通道模式(单字段)的兼容接口，返回扁平(values, hw_timestamps)格式。
        行为与原 _parse_channel_jscope() 完全一致。
        """
        result = self.parse_and_split(channel, data, fields, residual_buffer)
        sub_channel_data, new_residual, hw_ts_per_pkt = result

        if not sub_channel_data:
            return ([], [], new_residual)

        first_sub_ch = list(sub_channel_data.keys())[0]
        values = sub_channel_data[first_sub_ch]['values']
        hw_timestamps = [ts for ts in hw_ts_per_pkt if ts is not None]

        return (values, hw_timestamps, new_residual)