#!/usr/bin/env python3
"""SubChannelSplitter与子通道拆分验证测试"""

import struct
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'python'))

from rtt_tool.processors.sub_channel_splitter import SubChannelSplitter
from rtt_tool.processors.jscope_parser import parse_channel_name, parse_jscope_format
from rtt_tool.models.sub_channel_id import SubChannelId


def build_u4u4_packets(pairs):
    data = b''
    for a, b in pairs:
        data += struct.pack('<II', a, b)
    return data


def build_u4u1_packets(pairs):
    data = b''
    for a, b in pairs:
        data += struct.pack('<IB', a, b)
    return data


def build_t4u4u1_packets(triples):
    data = b''
    for ts, a, b in triples:
        data += struct.pack('<IIB', ts, a, b)
    return data


def test_u4u4_split():
    splitter = SubChannelSplitter()
    fields = parse_jscope_format("u4u4")
    data = build_u4u4_packets([(100, 200), (0, 90), (50, 150)])

    sub_data, residual, hw_ts = splitter.parse_and_split(1, data, fields, b'', "JScope_u4u4")

    assert len(sub_data) == 2, f"expected 2 sub-channels, got {len(sub_data)}"

    sub_ids = sorted(sub_data.keys(), key=lambda x: x.field_index)
    assert sub_ids[0].field_index == 0
    assert sub_ids[1].field_index == 1
    assert sub_data[sub_ids[0]]['values'] == [100, 0, 50], f"sub_ch(1,0) values: {sub_data[sub_ids[0]]['values']}"
    assert sub_data[sub_ids[1]]['values'] == [200, 90, 150], f"sub_ch(1,1) values: {sub_data[sub_ids[1]]['values']}"
    assert len(residual) == 0
    print("  PASS: JScope_u4u4 split into 2 sub-channels")


def test_u4u1_split():
    splitter = SubChannelSplitter()
    fields = parse_jscope_format("u4u1")
    data = build_u4u1_packets([(1000, 10), (2000, 20)])

    sub_data, residual, hw_ts = splitter.parse_and_split(1, data, fields, b'', "JScope_u4u1")

    assert len(sub_data) == 2, f"expected 2 sub-channels, got {len(sub_data)}"

    sub_ids = sorted(sub_data.keys(), key=lambda x: x.field_index)
    assert sub_data[sub_ids[0]]['values'] == [1000, 2000]
    assert sub_data[sub_ids[1]]['values'] == [10, 20]
    print("  PASS: JScope_u4u1 split into 2 sub-channels")


def test_u4u1u4u1_split():
    splitter = SubChannelSplitter()
    fields = parse_jscope_format("u4u1u4u1")
    data = b''
    for a, b, c, d in [(100, 1, 200, 2), (300, 3, 400, 4)]:
        data += struct.pack('<IBIB', a, b, c, d)

    sub_data, residual, hw_ts = splitter.parse_and_split(1, data, fields, b'', "JScope_u4u1u4u1")

    assert len(sub_data) == 4, f"expected 4 sub-channels, got {len(sub_data)}"

    sub_ids = sorted(sub_data.keys(), key=lambda x: x.field_index)
    assert sub_data[sub_ids[0]]['values'] == [100, 300]
    assert sub_data[sub_ids[1]]['values'] == [1, 3]
    assert sub_data[sub_ids[2]]['values'] == [200, 400]
    assert sub_data[sub_ids[3]]['values'] == [2, 4]
    print("  PASS: JScope_u4u1u4u1 split into 4 sub-channels")


def test_t4u4u1_timestamp_not_sub_channel():
    splitter = SubChannelSplitter()
    fields = parse_jscope_format("t4u4u1")
    data = build_t4u4u1_packets([(1000000, 42, 10), (1000001, 43, 20)])

    sub_data, residual, hw_ts = splitter.parse_and_split(1, data, fields, b'', "JScope_t4u4u1")

    assert len(sub_data) == 2, f"expected 2 sub-channels (t4 excluded), got {len(sub_data)}"
    assert hw_ts == [1000000, 1000001], f"hw_timestamps: {hw_ts}"
    print("  PASS: JScope_t4u4u1 - t4 is timestamp, not sub-channel")


def test_single_field_degenerate():
    splitter = SubChannelSplitter()
    fields = parse_jscope_format("u4")
    data = struct.pack('<II', 100, 200)

    sub_data, residual, hw_ts = splitter.parse_and_split(1, data, fields, b'', "JScope_u4")

    assert len(sub_data) == 1, f"expected 1 sub-channel, got {len(sub_data)}"
    sub_id = list(sub_data.keys())[0]
    assert sub_id.field_index == 0
    assert sub_data[sub_id]['values'] == [100, 200]
    print("  PASS: JScope_u4 single field degenerates to 1 sub-channel")


def test_sub_channel_timestamps_shared():
    splitter = SubChannelSplitter()
    fields = parse_jscope_format("u4u4")
    data = build_u4u4_packets([(100, 200), (0, 90)])

    sub_data, residual, hw_ts = splitter.parse_and_split(1, data, fields, b'', "JScope_u4u4")

    sub_ids = sorted(sub_data.keys(), key=lambda x: x.field_index)
    ts0 = sub_data[sub_ids[0]]['timestamps']
    ts1 = sub_data[sub_ids[1]]['timestamps']
    assert ts0 == ts1, f"timestamps must be shared: {ts0} != {ts1}"
    print("  PASS: Sub-channel timestamps are shared (zero phase difference)")


def test_residual_buffer():
    splitter = SubChannelSplitter()
    fields = parse_jscope_format("u4u4")
    full_data = build_u4u4_packets([(100, 200), (0, 90)])
    chunk1 = full_data[:5]
    chunk2 = full_data[5:]

    sub_data1, residual1, _ = splitter.parse_and_split(1, chunk1, fields, b'', "JScope_u4u4")
    assert len(sub_data1) == 0, "chunk1 < packet_size, no sub-channels"
    assert len(residual1) == 5

    sub_data2, residual2, _ = splitter.parse_and_split(1, chunk2, fields, residual1, "JScope_u4u4")
    sub_ids = sorted(sub_data2.keys(), key=lambda x: x.field_index)
    assert sub_data2[sub_ids[0]]['values'] == [100, 0]
    assert sub_data2[sub_ids[1]]['values'] == [200, 90]
    assert len(residual2) == 0
    print("  PASS: Residual buffer handling")


def test_empty_data():
    splitter = SubChannelSplitter()
    fields = parse_jscope_format("u4u4")

    sub_data, residual, hw_ts = splitter.parse_and_split(1, b'', fields, b'', "JScope_u4u4")
    assert len(sub_data) == 0
    assert len(residual) == 0
    print("  PASS: Empty data handling")


def test_parse_channel_name_u4u4():
    result = parse_channel_name("JScope_u4u4")
    assert result['data_field_count'] == 2, f"expected 2, got {result['data_field_count']}"
    assert result['buffer_mode'] == "合并buffer"
    assert result['packet_size'] == 8
    assert result['has_timestamp'] == False
    assert len(result['sub_channel_names']) == 2
    print("  PASS: parse_channel_name('JScope_u4u4')")


def test_parse_channel_name_u4():
    result = parse_channel_name("JScope_u4")
    assert result['data_field_count'] == 1
    assert result['buffer_mode'] == "独立通道"
    assert result['packet_size'] == 4
    print("  PASS: parse_channel_name('JScope_u4')")


def test_parse_channel_name_t4u4u1():
    result = parse_channel_name("JScope_t4u4u1")
    assert result['data_field_count'] == 2
    assert result['has_timestamp'] == True
    assert result['packet_size'] == 9
    print("  PASS: parse_channel_name('JScope_t4u4u1')")


def test_parse_channel_name_invalid():
    result = parse_channel_name("JScope_u4_u1")
    assert result == {}, f"expected empty dict for invalid format, got {result}"
    result = parse_channel_name("JScope_u3")
    assert result == {}
    result = parse_channel_name("NotJScope")
    assert result == {}
    print("  PASS: Invalid format strings return empty dict")


def test_sub_channel_id():
    id1 = SubChannelId(1, 0, "uint32", "JScope_u4u4")
    id2 = SubChannelId(1, 1, "uint32", "JScope_u4u4")
    id3 = SubChannelId(2, 0, "uint8", "JScope_u4u1")

    assert id1.to_signal_key() == (1, 0)
    assert id2.to_signal_key() == (1, 1)
    assert id1 != id2
    assert hash(id1) != hash(id2)

    d = {id1: "ch1_field0", id2: "ch1_field1", id3: "ch2_field0"}
    assert d[id1] == "ch1_field0"
    assert d[id2] == "ch1_field1"

    legacy = SubChannelId.from_legacy_channel(3)
    assert legacy.rtt_channel == 3
    assert legacy.field_index == 0

    assert id1.to_display_name() == "CH1[1]"
    assert id2.to_display_name() == "CH1[2]"
    print("  PASS: SubChannelId dataclass")


if __name__ == '__main__':
    print("=== SubChannelSplitter 与子通道拆分验证测试 ===\n")

    tests = [
        test_u4u4_split,
        test_u4u1_split,
        test_u4u1u4u1_split,
        test_t4u4u1_timestamp_not_sub_channel,
        test_single_field_degenerate,
        test_sub_channel_timestamps_shared,
        test_residual_buffer,
        test_empty_data,
        test_parse_channel_name_u4u4,
        test_parse_channel_name_u4,
        test_parse_channel_name_t4u4u1,
        test_parse_channel_name_invalid,
        test_sub_channel_id,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  FAIL: {test.__name__} - {e}")
            failed += 1

    print(f"\n=== 结果: {passed} passed, {failed} failed ===")
    sys.exit(0 if failed == 0 else 1)