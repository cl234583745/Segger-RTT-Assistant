**English | [简体中文](数据接收与多通道显示流程.md)**
# RTT-Assistant Data Reception and Multi-Channel Display Flow

## Overall Architecture Diagram

```mermaid
flowchart TB
    subgraph MCU["MCU (Same Timer 1kHz)"]
        ISR["Timer ISR"]
        WR0["CH0: SEGGER_RTT_Write<br/>(0, log_str)"]
        WR1["CH1: SEGGER_RTT_Write<br/>(1, data_u4)"]
        WR2["CH2: SEGGER_RTT_Write<br/>(2, data_u1)"]
        ISR --> WR0
        ISR --> WR1
        ISR --> WR2
    end

    subgraph RTTCB["RTT Control Block (RAM)"]
        UP0["Up[0]: Terminal (20480B)"]
        UP1["Up[1]: JScope_u4 (512B)"]
        UP2["Up[2]: JScope_u1 (256B)"]
    end

    WR0 -->|Log text| UP0
    WR1 -->|Write 4B every 1ms| UP1
    WR2 -->|Write 1B every 1ms| UP2

    subgraph PC["PC Side"]
        subgraph DRT["DataReceiveThread (QThread)"]
            POLL["1. poll_time = perf_counter()<br/>2. rtt_read_all([0,1,2]) → dict<br/>   ↓ one _poll_rtt_control_block() call<br/>   ↓ for ch: force_refresh + read<br/>3. CH0: data_received.emit → LogProcessor<br/>4. CH1+: batch_received.emit → WaveformProcessor"]
        end

        subgraph LP["LogProcessor (CH0 Log)"]
            DECODE["UTF-8 decode + write data log file<br/>→ text_updated.emit(ch0, text)"]
        end

        subgraph MW["MainWindow (CH0 Display)"]
            THROTTLE["Throttle accumulator _pending_text<br/>QTimer 50ms → _direct_insert_text()"]
            TE["QTextEdit (Smart Scroll)<br/>at_bottom → auto-tracking<br/>manual scroll up → stop tracking"]
        end

        subgraph MC["MainController"]
            BATCH["_on_batch_received(poll_time, batch)<br/>→ waveform_processor.process_batch(...)"]
        end

        subgraph WP["WaveformProcessor"]
            PB["process_batch(poll_time, batch)<br/>for (ch, data) in batch:<br/>  values = _parse_channel(ch, data)<br/>  ts = counter[ch] × Δt<br/>  buffer[ch].append(v)<br/>  timestamps[ch].append(ts)<br/>  waveform_updated.emit(ch, values)"]
        end

        subgraph WW["WaveformWidget (pyqtgraph)"]
            CURVE1["CH1: PlotCurveItem"]
            CURVE2["CH2: PlotCurveItem"]
            PLOT["PlotWidget: multiple curves overlaid for simultaneous display"]
            CURVE1 --> PLOT
            CURVE2 --> PLOT
        end
    end

    RTTCB -->|Single poll reads all channels| POLL
    POLL -->|Qt signal data_received| DECODE
    DECODE -->|text_updated signal| THROTTLE
    THROTTLE --> TE
    POLL -->|Qt signal batch_received| BATCH
    BATCH -->|call| PB
    PB -->|waveform_updated signal| CURVE1
    PB -->|waveform_updated signal| CURVE2
```

## v2.1.5 Key Improvements

### 1. RTT Read Integrity: pyocd Native Read Mode

**Problem**: Previously `ch.read(length=1024)` was hardcoded with truncation. MCU 20 log lines ≈ 1100 bytes, a single read could not finish, causing log line loss.

**Fix**: Prefer `ch.read()` with no arguments (consistent with `pyocd rtt` command behavior), reading all available data in one call. Only fall back to `ch.read(length=20480)` when the pyocd version does not support parameterless reads.

### 2. JLink Backlog Read Loop

JLink/pylink's `rtt_read` API requires a `pylink_read_size` parameter and cannot be called without arguments. Changed to repeatedly read within a single poll cycle until 0 bytes are returned (backlog drain). `pylink_read_size` defaults to 4096 (configurable).

### 3. Adaptive Polling Strategy

| State | Poll Interval | Description |
|------|----------|------|
| Has data | fast_interval (default 2ms) | Fast tracking of MCU output |
| 3 consecutive empty reads | slow_interval (default 10ms) | Reduce frequency to lower SWD overhead |

Multi-channel dynamic calculation: `effective = max(fast_interval, channel_count × swd_latency)`

### 4. CH0 Log UI Throttling

| | Before Throttling | After Throttling |
|--|--------|--------|
| Operation frequency | 20 lines/sec × 4 O(n) ops = 80 ops/sec | 2-3 ops/sec × 4 O(n) ops = 8-12 ops/sec |
| Latency | 0ms | ≤50ms (imperceptible to human eye) |
| Data loss | None | None (append-style accumulation) |

Data log file is written **in real time** and is not affected by throttling. Throttling only optimizes the QTextEdit display frequency.

### 5. Smart Scroll Tracking

| Scrollbar Position | Behavior |
|------------|------|
| At bottom | New data auto-scrolls to bottom (tracking mode) |
| Manual scroll up | Stops auto-scroll, free to browse history |
| Scrolled back to bottom | Automatically resumes tracking mode |

### 6. Signal Consolidation Optimization

Multiple CH0 reads within the same poll cycle are consolidated into a single `data_received` signal emission, reducing signal count.

### 7. Diagnostic Log Management

A “Log Management” entry is added to the main window log menu, allowing users to view file size and log level for the 3 diagnostic logs, with support for clear operations.

### 8. Ring Buffer Full Warning Downgrade

Buffer full warnings are downgraded from UI status bar to DEBUG log level, avoiding screen clutter.

## Key Improvement: Single-Poll Batch Read

### Before (Buggy)

```mermaid
sequenceDiagram
    participant DRT as DataReceiveThread
    participant RTT as RTT Control Block
    participant WP as WaveformProcessor

    Note over DRT: for ch in [0,1,2]:
    DRT->>RTT: rtt_read(CH0) → _poll_rtt_control_block() + read
    RTT-->>DRT: data_ch0
    DRT->>RTT: rtt_read(CH1) → _poll_rtt_control_block() + read
    Note over RTT: ❌ 2nd poll! MCU may have written new data
    RTT-->>DRT: data_ch1
    DRT->>RTT: rtt_read(CH2) → _poll_rtt_control_block() + read
    Note over RTT: ❌ 3rd poll! CH1 and CH2 are not from the same time snapshot
    RTT-->>DRT: data_ch2

    DRT->>WP: process(CH1, data_ch1) → counter1 += N1
    DRT->>WP: process(CH2, data_ch2) → counter2 += N2
    Note over WP: ❌ N1≠N2, counters grow at different rates, phase drift
```

### Now (Fixed)

```mermaid
sequenceDiagram
    participant DRT as DataReceiveThread
    participant RTT as RTT Control Block
    participant MC as MainController
    participant WP as WaveformProcessor

    DRT->>DRT: poll_time = perf_counter()
    DRT->>RTT: rtt_read_all([0,1,2])
    Note over RTT: ✅ Only 1 _poll_rtt_control_block() call
    RTT-->>DRT: {CH0:data0, CH1:data1, CH2:data2}

    DRT->>MC: batch_received.emit(poll_time, [(CH1,data1),(CH2,data2)])
    MC->>WP: process_batch(poll_time, batch)
    Note over WP: for (ch, data) in batch:
    Note over WP: ✅ All channels share the same poll_time
    Note over WP: ✅ counter[ch] × Δt ensures continuity
    WP->>WP: CH1: counter1 += N1, ts = counter1 × Δt
    WP->>WP: CH2: counter2 += N2, ts = counter2 × Δt
```

## Timestamp Generation Logic

```mermaid
flowchart TB
    A["process_batch(poll_time, batch)"]
    B["for (ch, data) in batch:"]
    C["values, hw_ts = _parse_channel(ch, data)"]
    D{use_hw_ts?}
    E["Hardware timestamp: ts = hw_ts × 1e-6"]
    F["Estimated timestamp: ts = counter[ch] × Δt"]
    G["counter[ch] += len(values)"]
    H["buffer[ch].append(v)"]
    I["timestamps[ch].append(ts)"]
    J["waveform_updated.emit(ch, values)"]

    A --> B --> C --> D
    D -->|Yes| E --> H
    D -->|No| F --> G --> H
    H --> I --> J
```

### Why counter[ch] × Δt instead of wall clock?

| Approach | Continuity | Multi-Channel Alignment | Complexity |
|------|--------|-----------|--------|
| counter[ch] × Δt | ✅ Strictly monotonically increasing | ✅ Single poll guarantees same-time snapshot | Low |
| wall clock (perf_counter) | ❌ Poll interval jitter causes gaps/overlaps | ✅ | High |
| Global counter | ✅ Strictly increasing | ❌ CH1 and CH2 interleave counting | Low |

**Chosen: counter[ch] × Δt**:
- Per-channel independent counter ensures timeline continuity (no gaps)
- `rtt_read_all` single poll guarantees CH1/CH2 data is from the same time snapshot
- Independent counters growing at different rates is no longer a problem, because data from all channels within the same poll is processed simultaneously

## Data Flow Key Timestamp Logs

```
[DRT batch] #1 poll=12345.6789 CH1:124B, CH2:31B     ← DataReceiveThread: rtt_read_all complete, emit batch
[batch] #1 poll_offset=0.0000s est_dt=1.00ms ...       ← WaveformProcessor: process_batch start
[batch] #2 poll_offset=0.0105s est_dt=1.00ms ...       ← Next batch, ~10ms later
[flush] #1 ch_count=2 elapsed=0.8ms                     ← WaveformWidget: setData to pyqtgraph
```

### Log Locations

| Stage | File | Log Prefix | Content |
|------|------|---------|------|
| RTT batch read | `data_receive_service.py` | `[DRT batch]` | poll time, channel:bytes |
| Batch processing | `waveform_processor.py` | `[batch]` | poll_offset, est_dt, elapsed, buffer length |
| Render to graph | `waveform_widget.py` | `[flush]` | channel count, elapsed |

## pyqtgraph Multi-Channel Implementation

```mermaid
flowchart TB
    PW["PlotWidget (1)"]
    VB["ViewBox (1)"]
    C1["PlotCurveItem CH1<br/>color=#5DADE2"]
    C2["PlotCurveItem CH2<br/>color=#58D68D"]
    GI["OscilloscopeGridItem"]
    AX["FixedTickAxisItem"]

    PW --> VB
    VB --> C1
    VB --> C2
    VB --> GI
    PW --> AX

    C1 -.->|setData x,y| DATA1["CH1: timestamps1[], values1[]"]
    C2 -.->|setData x,y| DATA2["CH2: timestamps2[], values2[]"]
```

Each channel has an independent `PlotCurveItem`, each calling `setData(timestamps, values)` independently. Multiple curves are overlaid in the same ViewBox and rendered simultaneously. This is natively supported by pyqtgraph with no special handling required.

## Configuration Reference

| Configuration Item | Default | Description |
|--------|--------|------|
| `ring_buffer_size` | 65536 | Ring buffer size (bytes) |
| `ring_buffer_full_log_level` | DEBUG | Buffer full warning level |
| `log_level.rtt_system` | INFO | rtt_system log level |
| `log_level.pyocd_diag` | INFO | pyocd_diag log level |
| `log_level.rtt_debug` | INFO | rtt_debug log level |
