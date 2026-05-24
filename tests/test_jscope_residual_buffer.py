#!/usr/bin/env python3
"""JScope残缺包缓冲区机制验证测试"""

import struct
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'python'))

from rtt_tool.processors.waveform_processor import WaveformProcessor, DataFormat
from rtt_tool.processors.jscope_parser import parse_channel_name, calc_packet_size, parse_packet


def build_jscope_packets_t4u4(timestamps, values):
    data = b''
    for ts, v in zip(timestamps, values):
        data += struct.pack('<II', ts, v)
    return data


def build_jscope_packets_t4u1(timestamps, values):
    data = b''
    for ts, v in zip(timestamps, values):
        data += struct.pack('<IB', ts, v)
    return data


def test_ch1_t4u4_aligned():
    proc = WaveformProcessor(buffer_size=1024)
    proc.set_channel_jscope_format(1, "JScope_t4u4")
    fields = proc._channel_jscope_fields[1]
    pkt_size = calc_packet_size(fields)
    assert pkt_size == 8, f"packet_size should be 8, got {pkt_size}"

    n = 20
    ts_list = [1367375181 + i for i in range(n)]
    val_list = [100 + i for i in range(n)]
    full_data = build_jscope_packets_t4u4(ts_list, val_list)

    chunk1 = full_data[:128]
    chunk2 = full_data[128:]

    v1, t1 = proc._parse_channel_jscope(1, chunk1, fields)
    assert len(v1) == 16, f"chunk1: expected 16 values, got {len(v1)}"
    residual_len = len(proc._residual_buffers.get(1, b''))
    assert residual_len == 0, f"chunk1: expected 0 residual, got {residual_len}"

    v2, t2 = proc._parse_channel_jscope(1, chunk2, fields)
    assert len(v2) == 4, f"chunk2: expected 4 values, got {len(v2)}"

    all_vals = v1 + v2
    assert all_vals == val_list, f"values mismatch: {all_vals} != {val_list}"
    print("  PASS: CH1 t4u4 aligned split")


def test_ch1_t4u4_misaligned():
    proc = WaveformProcessor(buffer_size=1024)
    proc.set_channel_jscope_format(1, "JScope_t4u4")
    fields = proc._channel_jscope_fields[1]

    n = 20
    ts_list = [1367375181 + i for i in range(n)]
    val_list = [100 + i for i in range(n)]
    full_data = build_jscope_packets_t4u4(ts_list, val_list)

    chunk1 = full_data[:143]
    chunk2 = full_data[143:]

    v1, t1 = proc._parse_channel_jscope(1, chunk1, fields)
    residual1 = proc._residual_buffers.get(1, b'')
    assert len(residual1) == 7, f"expected 7 residual bytes after chunk1 (143%%8=7), got {len(residual1)}"

    v2, t2 = proc._parse_channel_jscope(1, chunk2, fields)
    residual2 = proc._residual_buffers.get(1, b'')
    assert len(residual2) == 0, f"expected 0 residual bytes after chunk2, got {len(residual2)}"

    all_vals = v1 + v2
    assert all_vals == val_list, f"values mismatch!\n  got: {all_vals}\n  exp: {val_list}"
    print("  PASS: CH1 t4u4 misaligned split (143 bytes)")


def test_ch2_t4u1_misaligned():
    proc = WaveformProcessor(buffer_size=1024)
    proc.set_channel_jscope_format(2, "JScope_t4u1")
    fields = proc._channel_jscope_fields[2]
    pkt_size = calc_packet_size(fields)
    assert pkt_size == 5, f"packet_size should be 5, got {pkt_size}"

    n = 250
    ts_list = [1000000 + i for i in range(n)]
    val_list = [90 + (i % 160) for i in range(n)]
    full_data = build_jscope_packets_t4u1(ts_list, val_list)

    chunk1 = full_data[:1024]
    chunk2 = full_data[1024:]

    v1, t1 = proc._parse_channel_jscope(2, chunk1, fields)
    residual1 = proc._residual_buffers.get(2, b'')
    expected_residual1 = 1024 % 5
    assert len(residual1) == expected_residual1, \
        f"expected {expected_residual1} residual bytes, got {len(residual1)}"

    v2, t2 = proc._parse_channel_jscope(2, chunk2, fields)
    residual2 = proc._residual_buffers.get(2, b'')
    assert len(residual2) == 0, f"expected 0 residual after chunk2, got {len(residual2)}"

    all_vals = v1 + v2
    assert all_vals == val_list, f"values mismatch!\n  got len={len(all_vals)}, exp len={len(val_list)}"
    print("  PASS: CH2 t4u1 misaligned split (1024 bytes)")


def test_ch2_t4u1_multiple_reads():
    proc = WaveformProcessor(buffer_size=4096)
    proc.set_channel_jscope_format(2, "JScope_t4u1")
    fields = proc._channel_jscope_fields[2]

    n = 300
    ts_list = [1000000 + i for i in range(n)]
    val_list = [90 + (i % 160) for i in range(n)]
    full_data = build_jscope_packets_t4u1(ts_list, val_list)

    all_vals = []
    read_sizes = [144, 90, 552, 345, 152, 95]
    offset = 0
    for sz in read_sizes:
        chunk = full_data[offset:offset+sz]
        if not chunk:
            break
        v, t = proc._parse_channel_jscope(2, chunk, fields)
        all_vals.extend(v)
        offset += sz

    remaining = full_data[offset:]
    if remaining:
        v, t = proc._parse_channel_jscope(2, remaining, fields)
        all_vals.extend(v)

    assert all_vals == val_list, \
        f"values mismatch after multiple reads!\n  got len={len(all_vals)}, exp len={len(val_list)}\n  first diff at index {[i for i,(a,b) in enumerate(zip(all_vals,val_list)) if a!=b][:5]}"
    print("  PASS: CH2 t4u1 multiple reads with varying sizes")


def test_residual_cleared_on_reset():
    proc = WaveformProcessor(buffer_size=1024)
    proc.set_channel_jscope_format(1, "JScope_t4u4")
    proc._residual_buffers[1] = b'\x01\x02\x03'

    proc.reset()
    assert 1 not in proc._residual_buffers or proc._residual_buffers[1] == b'', \
        "residual buffer should be cleared after reset"
    print("  PASS: residual cleared on reset")


def test_residual_cleared_on_format_change():
    proc = WaveformProcessor(buffer_size=1024)
    proc.set_channel_jscope_format(1, "JScope_t4u4")
    proc._residual_buffers[1] = b'\x01\x02\x03\x04\x05'

    proc.set_channel_jscope_format(1, "JScope_t4u1")
    assert proc._residual_buffers.get(1, b'') == b'', \
        "residual buffer should be cleared on format change"
    print("  PASS: residual cleared on format change")


def test_residual_cleared_on_remove_channel():
    proc = WaveformProcessor(buffer_size=1024)
    proc.set_channel_jscope_format(1, "JScope_t4u4")
    proc._residual_buffers[1] = b'\x01\x02\x03'

    proc.remove_channel(1)
    assert 1 not in proc._residual_buffers, \
        "residual buffer should be removed with channel"
    print("  PASS: residual removed on remove_channel")


def test_data_smaller_than_packet():
    proc = WaveformProcessor(buffer_size=1024)
    proc.set_channel_jscope_format(2, "JScope_t4u1")
    fields = proc._channel_jscope_fields[2]

    small_data = b'\x4D\x0D\x72'
    v, t = proc._parse_channel_jscope(2, small_data, fields)
    assert len(v) == 0, f"expected 0 values for sub-packet data, got {len(v)}"
    assert proc._residual_buffers.get(2, b'') == small_data, \
        "sub-packet data should be stored in residual buffer"

    rest_data = b'\x51\x5A'
    v2, t2 = proc._parse_channel_jscope(2, rest_data, fields)
    assert len(v2) == 1, f"expected 1 value after completing packet, got {len(v2)}"
    assert v2[0] == 0x5A, f"expected value 0x5A (90), got {v2[0]}"
    print("  PASS: sub-packet data stored in residual, completed on next read")


def test_non_jscope_mode_unaffected():
    proc = WaveformProcessor(buffer_size=1024)
    data = struct.pack('<B', 0x06) + struct.pack('<I', 42)
    data += struct.pack('<B', 0x06) + struct.pack('<I', 100)

    v, t = proc._parse_channel(1, data)
    assert len(v) == 2, f"expected 2 values in auto mode, got {len(v)}"
    assert v[0] == 42 and v[1] == 100, f"values mismatch: {v}"
    print("  PASS: non-JScope mode unaffected")


def test_empty_data():
    proc = WaveformProcessor(buffer_size=1024)
    proc.set_channel_jscope_format(1, "JScope_t4u4")
    fields = proc._channel_jscope_fields[1]

    v, t = proc._parse_channel_jscope(1, b'', fields)
    assert len(v) == 0 and len(t) == 0, "empty data should return empty results"
    print("  PASS: empty data handling")


if __name__ == '__main__':
    print("=== JScope 残缺包缓冲区验证测试 ===\n")

    tests = [
        test_ch1_t4u4_aligned,
        test_ch1_t4u4_misaligned,
        test_ch2_t4u1_misaligned,
        test_ch2_t4u1_multiple_reads,
        test_residual_cleared_on_reset,
        test_residual_cleared_on_format_change,
        test_residual_cleared_on_remove_channel,
        test_data_smaller_than_packet,
        test_non_jscope_mode_unaffected,
        test_empty_data,
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
