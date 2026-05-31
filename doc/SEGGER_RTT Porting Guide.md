**English | [简体中文](SEGGER_RTT移植指南.md)**
# SEGGER RTT Porting Guide

This document is intended for MCU-side developers and describes how to port SEGGER RTT and use it with RTT Assistant. RTT Assistant supports two working modes, which the MCU distinguishes through different channels:

| Mode | Channel | Purpose | Data Format |
|------|---------|---------|-------------|
| **Log Mode** | Channel 0 | Text debug output, log printing | UTF-8 text, optional ANSI color codes |
| **Oscilloscope Mode** | Channel 1 | Real-time numerical data waveform display | JScope standard format binary packets |

---

## RTT Porting

### Obtaining the Source Code

Add the following files to your embedded project:

| File | Description |
|------|-------------|
| `SEGGER_RTT.c` | RTT core implementation |
| `SEGGER_RTT.h` | Header file |
| `SEGGER_RTT_Conf.h` | Configuration (buffer sizes, number of channels, etc.) |
| `SEGGER_RTT_printf.c` | Optional, provides the `SEGGER_RTT_printf()` function |
| `SEGGER_RTT_ASM_ARMv7M.S` | Optional, ARM Cortex-M assembly acceleration |

The source code can be obtained from the SEGGER official website, or you can use the bundled `resources/RTT.zip` included with RTT Assistant.

### Configuring Buffers

Edit `SEGGER_RTT_Conf.h` and adjust according to your needs:

```c
// Up buffer size (MCU -> Host)
// Channel 0 (Log): Recommended 1024 or larger; can be increased if text output is heavy
// Channel 1 (Oscilloscope): Depends on packet size and send frequency
#define BUFFER_SIZE_UP          (2048)

// Down buffer size (Host -> MCU)
#define BUFFER_SIZE_DOWN        (128)

// Number of up channels: At least 2 (Channel 0 Log + Channel 1 Oscilloscope)
#define SEGGER_RTT_MAX_NUM_UP_BUFFERS   (3)

// Number of down channels
#define SEGGER_RTT_MAX_NUM_DOWN_BUFFERS (3)

// Default write mode: Non-blocking, discard new data when buffer is full
#define SEGGER_RTT_MODE_DEFAULT         SEGGER_RTT_MODE_NO_BLOCK_SKIP
```

### Initialization

Call at the beginning of `main()` or after system initialization:

```c
#include "SEGGER_RTT.h"

int main(void) {
    SystemInit();
    SEGGER_RTT_Init();          // Initialize RTT control block
    // ... other initialization ...
}
```

`SEGGER_RTT_Init()` creates the default Channel 0 (up + down), which can be used directly afterwards.

---

## Log Mode (Channel 0)

Channel 0 is the default debug output channel of RTT, and can be used without additional configuration after initialization.

### Basic Usage

```c
// String output
SEGGER_RTT_WriteString(0, "System started\r\n");

// Formatted output
SEGGER_RTT_printf(0, "Temp: %d C, Humidity: %d%%\r\n", temp, humidity);

// Binary data
uint8_t data[] = {0x01, 0x02, 0x03};
SEGGER_RTT_Write(0, data, sizeof(data));
```

### ANSI Color Output

RTT Assistant supports ANSI escape code coloring (enable it from the tool menu). SEGGER RTT provides predefined color macros:

```c
SEGGER_RTT_WriteString(0, RTT_CTRL_TEXT_RED    "[ERROR] System fault\r\n");
SEGGER_RTT_WriteString(0, RTT_CTRL_TEXT_YELLOW  "[WARN]  Temperature too high\r\n");
SEGGER_RTT_WriteString(0, RTT_CTRL_TEXT_GREEN   "[INFO]  Task completed\r\n");
SEGGER_RTT_WriteString(0, RTT_CTRL_TEXT_BLUE    "[DEBUG] x=100\r\n");
SEGGER_RTT_WriteString(0, RTT_CTRL_RESET        "Normal text\r\n");
```

Available color macros are defined in `SEGGER_RTT.h`:

| Macro | Effect |
|-------|--------|
| `RTT_CTRL_TEXT_BLACK` / `WHITE` / `RED` / `GREEN` / `BLUE` / `YELLOW` / `CYAN` / `MAGENTA` | Text color |
| `RTT_CTRL_BG_...` (same colors as above) | Background color |
| `RTT_CTRL_RESET` | Reset all attributes |

> **Note**: `SEGGER_RTT_printf()` internally uses `SEGGER_RTT_Write()`, and color macros in format strings may be truncated. It is recommended to output color macros separately via `SEGGER_RTT_WriteString()`, or ensure that the `PRINTF_USE_SEGGER_RTT` configuration in your `SEGGER_RTT_Conf.h` is correct.

---

## Oscilloscope Mode (Channel 1)

Oscilloscope mode uses Channel 1 (or any non-zero channel) to send structured numerical data, which RTT Assistant displays as real-time waveform curves.

### Configuring the Channel

Channel 1 is not created automatically; it must be explicitly configured using `SEGGER_RTT_ConfigUpBuffer()`. **The channel name declares the data format** and must follow the JScope naming convention:

```c
SEGGER_RTT_ConfigUpBuffer(1, "JScope_<field_descriptors>", NULL, 0, SEGGER_RTT_MODE_NO_BLOCK_SKIP);
```

Passing `NULL` as the third parameter lets RTT manage the buffer internally. The fourth parameter `0` means the buffer size from `BUFFER_SIZE_UP` in `SEGGER_RTT_Conf.h` will be used.

To specify a custom buffer size:

```c
static uint8_t scope_buf[1024];
SEGGER_RTT_ConfigUpBuffer(1, "JScope_t4i4u1", scope_buf, sizeof(scope_buf), SEGGER_RTT_MODE_NO_BLOCK_SKIP);
```

### JScope Data Format

The string after `JScope_` in the channel name declares the structure of the data packet. Each field consists of a **type letter + byte count**:

| Descriptor | C Type | Size | Description |
|------------|--------|------|-------------|
| `t4` | `uint32_t` | 4 bytes | Timestamp (microseconds), **must be the first field** |
| `i1` | `int8_t` | 1 byte | Signed 8-bit integer |
| `i2` | `int16_t` | 2 bytes | Signed 16-bit integer |
| `i4` | `int32_t` | 4 bytes | Signed 32-bit integer |
| `u1` | `uint8_t` | 1 byte | Unsigned 8-bit integer |
| `u2` | `uint16_t` | 2 bytes | Unsigned 16-bit integer |
| `u4` | `uint32_t` | 4 bytes | Unsigned 32-bit integer |

All multi-byte fields use **Little-Endian** byte order.

### Common Format Examples

| Channel Name | Packet Size | Field Description |
|--------------|-------------|-------------------|
| `JScope_t4i4` | 8 bytes | Timestamp + int32 |
| `JScope_t4u4u4` | 12 bytes | Timestamp + uint32 + uint32 |
| `JScope_i4i4` | 8 bytes | int32 + int32 (no timestamp) |
| `JScope_t4i2u2u1` | 9 bytes | Timestamp + int16 + uint16 + uint8 |
| `JScope_t4f4` | 8 bytes | Timestamp + float (requires RTT Assistant 2.x support) |

> **Note**: Use `u4` (4 bytes) for multi-byte types, not `u2` (2 bytes) or `u1` (1 byte). The size must match the actual C type, otherwise parsing will be misaligned.

### Oscilloscope Mode Complete Example

```c
#include "SEGGER_RTT.h"
#include <stdint.h>

// Channel 1 buffer
static uint8_t _scope_buf[1024];

// Initialize oscilloscope channel
void scope_init(void) {
    // Format: 4-byte timestamp + 4-byte int32 + 2-byte uint16 + 1-byte uint8
    // Total: 11 bytes per packet
    SEGGER_RTT_ConfigUpBuffer(1, "JScope_t4i4u2u1",
                              _scope_buf, sizeof(_scope_buf),
                              SEGGER_RTT_MODE_NO_BLOCK_SKIP);
}

// Send one frame of data
void scope_send_frame(int32_t value, uint16_t flags, uint8_t status) {
    uint8_t packet[11];
    uint32_t ts = get_system_us();   // Microsecond timestamp

    *(uint32_t*)&packet[0] = ts;       // t4: timestamp
    *(int32_t*) &packet[4] = value;    // i4: int32
    *(uint16_t*)&packet[8] = flags;    // u2: uint16
    packet[10] = status;               // u1: uint8

    SEGGER_RTT_Write(1, packet, sizeof(packet));
}

// Call periodically (e.g., in a timer interrupt or RTOS task)
void scope_timer_callback(void) {
    static int32_t counter = 0;
    scope_send_frame(counter++, 0x01, 0xAA);
}
```

### Formats Without Timestamp

The timestamp field `t4` is optional. When omitted, RTT Assistant will number the data based on arrival order, and the horizontal axis will show sample indices instead of absolute time:

```c
// No-timestamp format: two uint32 values
SEGGER_RTT_ConfigUpBuffer(1, "JScope_u4u4",
                          NULL, 0, SEGGER_RTT_MODE_NO_BLOCK_SKIP);

void send_data(uint32_t ch1, uint32_t ch2) {
    uint8_t packet[8];
    *(uint32_t*)&packet[0] = ch1;
    *(uint32_t*)&packet[4] = ch2;
    SEGGER_RTT_Write(1, packet, 8);
}
```

---

## Auto-Detection Mode (Without JScope Naming)

If the channel name does not start with `JScope_`, RTT Assistant will use auto-detection mode. Each numerical value must be prefixed with a 1-byte type identifier:

| type_byte | Type |
|-----------|------|
| 0x01 | int8 |
| 0x02 | uint8 |
| 0x03 | int16 |
| 0x04 | uint16 |
| 0x05 | int32 |
| 0x06 | uint32 |
| 0x07 | float |

```c
// Channel name does not start with JScope_, triggers auto-detection mode
SEGGER_RTT_ConfigUpBuffer(1, "ScopeData", NULL, 0, SEGGER_RTT_MODE_NO_BLOCK_SKIP);

void send_auto_float(float val) {
    uint8_t packet[5];
    packet[0] = 0x07;                      // type_byte: float
    *(float*)&packet[1] = val;
    SEGGER_RTT_Write(1, packet, 5);
}
```

---

## Combined Example: Log + Oscilloscope Running Simultaneously

The following code demonstrates Channel 0 (Log) and Channel 1 (Oscilloscope) running simultaneously:

```c
#include "SEGGER_RTT.h"
#include <stdint.h>

// Simulated ADC reading
static uint32_t read_adc(void) { return /* ... */; }
static uint32_t get_tick_us(void) { return /* microsecond timestamp */; }

int main(void) {
    SystemInit();
    SEGGER_RTT_Init();    // Channel 0 automatically available

    // Configure Channel 1 for oscilloscope mode
    SEGGER_RTT_ConfigUpBuffer(1, "JScope_t4u4",
                              NULL, 0, SEGGER_RTT_MODE_NO_BLOCK_SKIP);

    SEGGER_RTT_WriteString(0, "System started, logging enabled\r\n");

    uint32_t count = 0;
    while (1) {
        // Log output (Channel 0)
        SEGGER_RTT_printf(0, "Count: %u, ADC: %u\r\n", count, read_adc());

        // Oscilloscope data (Channel 1)
        uint8_t pkt[8];
        *(uint32_t*)&pkt[0] = get_tick_us();
        *(uint32_t*)&pkt[4] = read_adc();
        SEGGER_RTT_Write(1, pkt, 8);

        count++;
        delay_ms(10);
    }
}
```

In RTT Assistant:
1. After connecting, the receive area automatically displays log text from Channel 0
2. Switch to **Oscilloscope Mode** or **Mixed Mode**, then click **Start** to display the ADC waveform from Channel 1
3. The **Format** label in the toolbar will show the auto-parsed `timestamp(µs) + uint32`

---

## Channel Configuration Comparison Table

| Step | Log Mode (Channel 0) | Oscilloscope Mode (Channel 1) |
|------|----------------------|-------------------------------|
| Initialization | Automatically created by `SEGGER_RTT_Init()` | Must call `SEGGER_RTT_ConfigUpBuffer()` |
| Channel Name | No need to set (internal name) | Must be set to `JScope_<format>` |
| Buffer | Default allocation from `BUFFER_SIZE_UP` | Can customize or use default size |
| Write Function | `WriteString` / `printf` / `Write` | `Write` (binary data) |
| Write Mode | Recommended `NO_BLOCK_SKIP` | Recommended `NO_BLOCK_SKIP` |
| Data Type | UTF-8 text | Structured binary packets |
| RTT Assistant Mode | Log Mode | Oscilloscope Mode |

---

## Important Notes

1. **Do not rename Channel 0**: Channel 0 is the default SEGGER RTT debug channel. Do not use `SEGGER_RTT_ConfigUpBuffer(0, ...)` to change its channel name, as this may affect RTT Assistant's text display
2. **Use Channel 1 for oscilloscope**: Although any non-zero channel can be used, RTT Assistant defaults to monitoring Channel 1 for waveform display
3. **Use NO_BLOCK_SKIP for buffer mode**: `SEGGER_RTT_MODE_NO_BLOCK_SKIP` ensures the MCU will not be blocked when the RTT buffer is full, and is the recommended configuration for production environments
4. **Timestamp precision**: The `t4` field is in microseconds; the MCU must provide a reliable microsecond timer. If timing is inaccurate, the waveform horizontal axis will be distorted. If no reliable time source is available, `t4` can be omitted
5. **Data packet alignment**: Unaligned access on ARM Cortex-M may trigger a fault or performance penalty. It is recommended to align data packets to 4 bytes, or use `memcpy` to fill byte-by-byte before sending
6. **Do not mix channels**: Oscilloscope data should only go through channels configured with JScope format, and log text should go through Channel 0. Do not mix text and binary data on the same channel
