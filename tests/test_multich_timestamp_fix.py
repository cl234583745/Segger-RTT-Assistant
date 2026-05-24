#!/usr/bin/env python3
"""Bug C修复验证：多通道+硬件时间戳波形乱套

验证3个修复点：
1. _hw_ts_origins 每通道独立存储
2. get_buffer_data() 返回长度一致
3. 双路分发消除（WaveformProcessor层面：process_batch不重复处理）
"""

import struct
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'python'))

from rtt_tool.processors.waveform_processor import WaveformProcessor, DataFormat


def build_t4u4(timestamps, values):
    data = b''
    for ts, v in zip(timestamps, values):
        data += struct.pack('<II', ts, v)
    return data


def build_t4u1(timestamps, values):
    data = b''
    for ts, v in zip(timestamps, values):
        data += struct.pack('<IB', ts, v)
    return data


def test_per_channel_hw_ts_origin():
    """每通道独立存储 _hw_ts_origins，不同通道的origin互不干扰"""
    proc = WaveformProcessor(buffer_size=1024)
    proc.set_channel_jscope_format(1, "JScope_t4u4")
    proc.set_channel_jscope_format(2, "JScope_t4u1")

    ch1_ts = [1000, 1100, 1200]
    ch1_vals = [10, 20, 30]
    ch2_ts = [1050, 1150, 1250]
    ch2_vals = [5, 6, 7]

    proc.process(1, build_t4u4(ch1_ts, ch1_vals))
    proc.process(2, build_t4u1(ch2_ts, ch2_vals))

    assert 1 in proc._hw_ts_origins, "CH1 应有独立的 hw_ts_origin"
    assert 2 in proc._hw_ts_origins, "CH2 应有独立的 hw_ts_origin"

    ch1_origin = proc._hw_ts_origins[1]
    ch2_origin = proc._hw_ts_origins[2]

    assert abs(ch1_origin - 1000 * 1e-6) < 1e-12, f"CH1 origin 应为 1000*1e-6, 实际 {ch1_origin}"
    assert abs(ch2_origin - 1050 * 1e-6) < 1e-12, f"CH2 origin 应为 1050*1e-6, 实际 {ch2_origin}"

    ts1, vals1 = proc.get_buffer_data(1)
    ts2, vals2 = proc.get_buffer_data(2)

    assert abs(ts1[0]) < 1e-12, f"CH1 第一个时间戳应为0（相对origin），实际 {ts1[0]}"
    assert abs(ts2[0]) < 1e-12, f"CH2 第一个时间戳应为0（相对origin），实际 {ts2[0]}"

    expected_ch1_last = (1200 - 1000) * 1e-6
    expected_ch2_last = (1250 - 1050) * 1e-6
    assert abs(ts1[-1] - expected_ch1_last) < 1e-12, f"CH1 最后时间戳错误"
    assert abs(ts2[-1] - expected_ch2_last) < 1e-12, f"CH2 最后时间戳错误"


def test_per_channel_origin_in_batch():
    """process_batch 中每通道也使用独立的 _hw_ts_origins"""
    proc = WaveformProcessor(buffer_size=1024)
    proc.set_channel_jscope_format(1, "JScope_t4u4")
    proc.set_channel_jscope_format(2, "JScope_t4u1")

    ch1_ts = [5000, 5100, 5200]
    ch1_vals = [100, 200, 300]
    ch2_ts = [5050, 5150, 5250]
    ch2_vals = [50, 60, 70]

    batch = [
        (1, build_t4u4(ch1_ts, ch1_vals)),
        (2, build_t4u1(ch2_ts, ch2_vals)),
    ]
    proc.process_batch(0.0, batch)

    assert 1 in proc._hw_ts_origins, "CH1 应有独立的 hw_ts_origin"
    assert 2 in proc._hw_ts_origins, "CH2 应有独立的 hw_ts_origin"

    assert abs(proc._hw_ts_origins[1] - 5000 * 1e-6) < 1e-12
    assert abs(proc._hw_ts_origins[2] - 5050 * 1e-6) < 1e-12


def test_get_buffer_data_length_consistency():
    """get_buffer_data() 返回的 timestamps 和 values 长度始终一致"""
    proc = WaveformProcessor(buffer_size=1024)
    proc.set_channel_jscope_format(1, "JScope_t4u4")
    proc.set_channel_jscope_format(2, "JScope_t4u1")

    ch1_ts = [1000, 1100, 1200, 1300, 1400]
    ch1_vals = [10, 20, 30, 40, 50]
    ch2_ts = [1050, 1150, 1250]
    ch2_vals = [5, 6, 7]

    proc.process(1, build_t4u4(ch1_ts, ch1_vals))
    proc.process(2, build_t4u1(ch2_ts, ch2_vals))

    ts1, vals1 = proc.get_buffer_data(1)
    ts2, vals2 = proc.get_buffer_data(2)

    assert len(ts1) == len(vals1), f"CH1: len(ts)={len(ts1)} != len(vals)={len(vals1)}"
    assert len(ts2) == len(vals2), f"CH2: len(ts)={len(ts2)} != len(vals)={len(vals2)}"
    assert len(vals1) == 5, f"CH1 应有5个值，实际 {len(vals1)}"
    assert len(vals2) == 3, f"CH2 应有3个值，实际 {len(vals2)}"


def test_no_cross_channel_origin_contamination():
    """后处理的通道不会"污染"先处理通道的时间戳基准"""
    proc = WaveformProcessor(buffer_size=1024)
    proc.set_channel_jscope_format(1, "JScope_t4u4")
    proc.set_channel_jscope_format(2, "JScope_t4u1")

    ch1_ts = [100, 200, 300]
    ch1_vals = [1, 2, 3]
    ch2_ts = [99999, 100099, 100199]
    ch2_vals = [99, 98, 97]

    proc.process(1, build_t4u4(ch1_ts, ch1_vals))
    proc.process(2, build_t4u1(ch2_ts, ch2_vals))

    ts1, vals1 = proc.get_buffer_data(1)

    expected_ch1_first = 0.0
    expected_ch1_last = (300 - 100) * 1e-6

    assert abs(ts1[0] - expected_ch1_first) < 1e-12, \
        f"CH1 时间戳不应被CH2的origin污染: ts1[0]={ts1[0]}"
    assert abs(ts1[-1] - expected_ch1_last) < 1e-12, \
        f"CH1 最后时间戳不应被CH2污染: ts1[-1]={ts1[-1]}"


def test_reset_clears_all_origins():
    """reset() 应清除所有通道的 _hw_ts_origins"""
    proc = WaveformProcessor(buffer_size=1024)
    proc.set_channel_jscope_format(1, "JScope_t4u4")
    proc.set_channel_jscope_format(2, "JScope_t4u1")

    proc.process(1, build_t4u4([1000, 1100], [10, 20]))
    proc.process(2, build_t4u1([1050, 1150], [5, 6]))

    assert len(proc._hw_ts_origins) == 2

    proc.reset()

    assert len(proc._hw_ts_origins) == 0, "reset 后 _hw_ts_origins 应为空"


def test_multich_timestamps_monotonic():
    """多通道+时间戳时，各通道的时间戳都应单调递增"""
    proc = WaveformProcessor(buffer_size=1024)
    proc.set_channel_jscope_format(1, "JScope_t4u4")
    proc.set_channel_jscope_format(2, "JScope_t4u1")

    for batch_idx in range(5):
        base_ts = 10000 + batch_idx * 1000
        ch1_ts = [base_ts, base_ts + 100, base_ts + 200]
        ch1_vals = [batch_idx * 10 + i for i in range(3)]
        ch2_ts = [base_ts + 50, base_ts + 150, base_ts + 250]
        ch2_vals = [batch_idx * 5 + i for i in range(3)]

        batch = [
            (1, build_t4u4(ch1_ts, ch1_vals)),
            (2, build_t4u1(ch2_ts, ch2_vals)),
        ]
        proc.process_batch(0.0, batch)

    ts1, vals1 = proc.get_buffer_data(1)
    ts2, vals2 = proc.get_buffer_data(2)

    for i in range(1, len(ts1)):
        assert ts1[i] > ts1[i-1], f"CH1 时间戳非单调: ts[{i-1}]={ts1[i-1]}, ts[{i}]={ts1[i]}"

    for i in range(1, len(ts2)):
        assert ts2[i] > ts2[i-1], f"CH2 时间戳非单调: ts[{i-1}]={ts2[i-1]}, ts[{i}]={ts2[i]}"
