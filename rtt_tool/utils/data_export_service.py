import csv
import os
from datetime import datetime


class DataExportService:
    """数据导出服务，支持 CSV 格式导出。"""

    @staticmethod
    def export_waveform_csv(filepath: str, timestamps: list, values_dict: dict):
        """导出波形数据为 CSV。

        Args:
            filepath: 导出文件路径
            timestamps: 时间戳列表
            values_dict: {channel: [values]} 通道数据字典
        """
        channels = sorted(values_dict.keys())
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            header = ['Timestamp(s)'] + [f'CH{ch}' for ch in channels]
            writer.writerow(header)
            for i, ts in enumerate(timestamps):
                row = [f'{ts:.6f}']
                for ch in channels:
                    ch_values = values_dict[ch]
                    row.append(str(ch_values[i]) if i < len(ch_values) else '')
                writer.writerow(row)

    @staticmethod
    def export_log_csv(filepath: str, log_entries: list):
        """导出日志为 CSV。

        Args:
            filepath: 导出文件路径
            log_entries: [(timestamp, channel, data), ...]
        """
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Timestamp', 'Channel', 'Data'])
            for ts, ch, data in log_entries:
                writer.writerow([ts, ch, data])

    @staticmethod
    def export_variable_csv(filepath: str, variables: list):
        """导出变量监视历史为 CSV。

        Args:
            filepath: 导出文件路径
            variables: [(name, address, var_type, value, timestamp), ...]
        """
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Name', 'Address', 'Type', 'Value', 'Timestamp'])
            for name, addr, vtype, val, ts in variables:
                writer.writerow([name, f'0x{addr:08X}', vtype, val, ts])
