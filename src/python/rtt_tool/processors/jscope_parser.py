import struct
import logging
import re


logger = logging.getLogger(__name__)


JSOCOPE_PREFIX = "JScope_"

TYPE_MAP = {
    't': {'fmt': 'I', 'size': 4, 'label': 'timestamp', 'is_timestamp': True},
    't4': {'fmt': 'I', 'size': 4, 'label': 'timestamp', 'is_timestamp': True},
    'i1': {'fmt': 'b', 'size': 1, 'label': 'int8', 'is_timestamp': False},
    'i2': {'fmt': 'h', 'size': 2, 'label': 'int16', 'is_timestamp': False},
    'i4': {'fmt': 'i', 'size': 4, 'label': 'int32', 'is_timestamp': False},
    'u1': {'fmt': 'B', 'size': 1, 'label': 'uint8', 'is_timestamp': False},
    'u2': {'fmt': 'H', 'size': 2, 'label': 'uint16', 'is_timestamp': False},
    'u4': {'fmt': 'I', 'size': 4, 'label': 'uint32', 'is_timestamp': False},
}

AUTO_TYPE_MAP = {
    0x01: ('b', 1, 'int8'),
    0x02: ('B', 1, 'uint8'),
    0x03: ('h', 2, 'int16'),
    0x04: ('H', 2, 'uint16'),
    0x05: ('i', 4, 'int32'),
    0x06: ('I', 4, 'uint32'),
    0x07: ('f', 4, 'float'),
}


def parse_jscope_format(format_str: str) -> list:
    """
    解析 JScope 格式字符串，如 't4i4u1' -> [field_desc, ...]
    
    每个field_desc: {'fmt': struct格式, 'size': 字节数, 'label': 显示名, 'is_timestamp': bool}
    """
    if not format_str:
        return []
    
    fields = []
    i = 0
    while i < len(format_str):
        type_char = format_str[i]
        i += 1
        size_str = ''
        while i < len(format_str) and format_str[i].isdigit():
            size_str += format_str[i]
            i += 1
        if not size_str:
            return []
        key = f"{type_char}{size_str}"
        field = TYPE_MAP.get(key)
        if field is None:
            logger.warning(f"JScope格式解析: 未知类型 '{key}'")
            return []
        fields.append(dict(field))
    
    return fields


def parse_channel_name(channel_name: str) -> dict:
    """
    解析RTT通道名，返回JScope格式信息字典。
    
    Returns:
        dict with keys:
            fields: 字段定义列表
            packet_size: 包大小(字节)
            data_field_count: 非时间戳数据字段数量
            buffer_mode: "合并buffer" 或 "独立通道"
            has_timestamp: 是否含硬件时间戳
            sub_channel_names: 子通道显示名列表(仅数据字段)
        空dict表示非JScope格式或解析失败
    """
    if not channel_name:
        return {}
    if not channel_name.startswith(JSOCOPE_PREFIX):
        return {}
    
    format_str = channel_name[len(JSOCOPE_PREFIX):]
    fields = parse_jscope_format(format_str)
    if not fields:
        return {}
    
    packet_size = sum(f['size'] for f in fields)
    data_fields = [f for f in fields if not f.get('is_timestamp')]
    data_field_count = len(data_fields)
    has_timestamp = any(f.get('is_timestamp') for f in fields)
    buffer_mode = "合并buffer" if data_field_count > 1 else "独立通道"
    sub_channel_names = generate_sub_channel_names(fields)
    
    if data_field_count > 16:
        logger.warning(f"JScope格式 '{channel_name}' 包含{data_field_count}个数据字段，较多可能影响性能")
    
    return {
        'fields': fields,
        'packet_size': packet_size,
        'data_field_count': data_field_count,
        'buffer_mode': buffer_mode,
        'has_timestamp': has_timestamp,
        'sub_channel_names': sub_channel_names,
    }


def generate_sub_channel_names(fields: list) -> list:
    """
    生成子通道显示名列表（不含母通道前缀）。
    
    格式: ["[1]", "[2]"] - 1-based序号
    时间戳字段(t4)不生成子通道名
    调用方负责拼接母通道前缀，如 "CH1" + "[1]" = "CH1[1]"
    """
    data_fields = [f for f in fields if not f.get('is_timestamp')]
    if not data_fields:
        return []
    
    names = []
    for i in range(len(data_fields)):
        names.append(f"[{i + 1}]")
    
    return names


def calc_packet_size(fields: list) -> int:
    """计算一个完整数据包的字节数"""
    return sum(f['size'] for f in fields)


def parse_packet(data: bytes, fields: list, offset: int = 0) -> dict:
    """
    解析一个JScope数据包，返回 {'timestamp': val, 'values': [v1, v2, ...]}
    timestamp 可能为 None。
    """
    result = {'timestamp': None, 'values': []}
    pos = offset
    for field in fields:
        if pos + field['size'] > len(data):
            return None
        try:
            val = struct.unpack_from(f'<{field["fmt"]}', data, pos)[0]
        except struct.error:
            return None
        if field['is_timestamp']:
            result['timestamp'] = val
        else:
            result['values'].append(val)
        pos += field['size']
    return result


def format_display_text(fields: list) -> str:
    """生成格式显示文本，如 't4i4u1' -> 'timestamp(us) + int32 + uint8'"""
    parts = []
    for f in fields:
        if f['is_timestamp']:
            parts.append('timestamp(µs)')
        else:
            parts.append(f['label'])
    return ' + '.join(parts) if parts else '自动识别'
