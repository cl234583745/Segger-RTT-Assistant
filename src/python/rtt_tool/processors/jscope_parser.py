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


def parse_channel_name(channel_name: str) -> list:
    """
    解析RTT通道名，返回JScope格式字段列表。
    如果通道名以 'JScope_' 开头，解析其格式；
    否则返回空列表（自动识别模式）。
    """
    if not channel_name:
        return []
    if channel_name.startswith(JSOCOPE_PREFIX):
        format_str = channel_name[len(JSOCOPE_PREFIX):]
        return parse_jscope_format(format_str)
    return []


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
