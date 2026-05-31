**English | [简体中文](使用说明.md)**
# RTT Assistant - Usage Guide

RTT Assistant is a graphical RTT (Real Time Transfer) debugging tool that supports multiple debug probes including J-Link, DAP-Link, and ST-Link. It provides features such as log transmission/reception, oscilloscope waveform display, and variable monitoring.

---

## Quick Start

1. **Launch the program**: Double-click `RTT-Assistant v2.1.1.exe`
2. **Configure connection**: Click the **Configure** button on the toolbar to open the connection configuration dialog
3. **Select debug probe**: In "Step 1", click **Refresh** and select a detected probe
4. **Select target chip**:
   - J-Link: In "Step 3", select the chip model from the J-Link target device dropdown (e.g., STM32F407VE)
   - DAP-Link / ST-Link: In "Step 3", select a PyOCD target from the other Link target device dropdown (e.g., r7ka8p1kf); if not in the list, click the **Pack** button to download
5. **Set interface**: In "Step 4", select SWD as the interface; 4000kHz is the recommended speed
6. **RTT control block**: In "Step 5", keep the default "Auto Detect" setting
7. **Click OK**: Wait for the connection to succeed; the status bar will display probe information and a green "Connected" indicator
8. **Send/receive data**: The receive area automatically displays RTT data; in the send area, type text and press **Enter** or click **Send**

---

## Main Interface

### Window Layout

The main window is divided from top to bottom into: toolbar, display area (receive area / oscilloscope), send area, and status bar.

The default size is 1000×700 pixels and can be freely resized.

### Toolbar

From left to right:

| Button | Description |
|--------|-------------|
| **Connect** | Connect directly using the previous configuration without opening the configuration dialog again |
| **Configure** | Open the connection configuration dialog to modify all connection parameters |
| **Disconnect** | Disconnect from the current MCU (available after connection) |
| **Clear** | Clear the display content in the receive area (does not affect log files) |
| **Mode** | Switch display mode: Log / Oscilloscope / Mixed (select from dropdown menu) |
| **Timestamp** | When checked, each received line of data is prefixed with a `[yyyy-MM-dd hh:mm:ss.zzz]` timestamp |
| **HEX Display** | When checked, received data is displayed in hexadecimal format (e.g., `48 65 6C 6C 6F`) |

Right-side buttons:

| Button | Description |
|--------|-------------|
| **Tools** | Font settings, theme switching, ANSI color toggle, keyword highlight configuration |
| **Help** | Usage guide, update notes, SEGGER RTT documentation, dependency management, About |
| **Log** | Open system log window, open data log file directory |
| **📌** | Window always-on-top toggle (when clicked, the window stays above all other windows) |

### Tools Menu

| Menu Item | Description |
|-----------|-------------|
| **Font** | Open the system font dialog to change the display font in the receive area |
| **Theme → Dark** | Switch to dark theme (default), dark background with light text |
| **Theme → Light** | Switch to light theme, white background with dark text |
| **ANSI Color** | Toggle ANSI escape code parsing; when enabled, color codes in RTT data are rendered as corresponding colors |
| **Keyword Highlight → Enable** | Toggle keyword highlighting |
| **Keyword Highlight → Rule Configuration** | Customize highlight keywords and colors; defaults match ERROR (red), WARN/WARNING (yellow), FAIL (red), OK/SUCCESS (green), INFO (blue) |

### Help Menu

| Menu Item | Description |
|---------|-------------|
| **Feedback** | Display author email (292812832@qq.com); please attach the `log/` directory when reporting issues |
| **Usage Guide** | Open this document |
| **Update Notes** | View version update history |
| **Upgrade Guide** | Version upgrade instructions |
| **SEGGER RTT → RTT Introduction** | Open the SEGGER official RTT knowledge base page |
| **SEGGER RTT → RTT Source** | Open the local RTT source package (`resources/RTT.zip`) |
| **SEGGER RTT → Porting Guide** | View the guide for porting RTT to MCU |
| **Dependency Management** | Check and install/upgrade runtime dependencies such as PyOCD |
| **About** | Display version number, J-Link DLL version, PyOCD version, author information, and contact details |

### Status Bar

| Area | Description |
|--------|-------------|
| Connection status | Gray "Disconnected" / Orange "Connecting" / Green "Connected"; displays error information when disconnected |
| RX count | Number of bytes received |
| TX count | Number of bytes sent |
| **Reset** button | Reset RX/TX counters to zero |
| Probe info | Right side displays detailed information about the current probe (J-Link serial number/hardware version/firmware version, or PyOCD probe name/serial number/target chip) |

---

## Connection Configuration

Click the **Configure** button on the toolbar to open the "Connection Configuration" dialog. The configuration process is divided into 5 steps:

### Step 1: Debug Probe Selection

- Click the **Refresh** button; the program automatically detects connected debug probes
- Detection results list all probes in the format `[Type] Name (SN:SerialNumber)`
- J-Link probes, DAP-Link, and ST-Link are all listed here
- Select the probe you want to use

> **Note**: If no probes are found after refreshing, check the USB connection and drivers. J-Link requires the J-Link software package to be installed; DAP-Link/ST-Link do not require additional drivers.

### Step 2: Connection Method

- **USB**: Default method, connect to the probe via USB
  - Check **SN/Nickname** to enter a serial number or nickname, used to specify a particular probe in a multi-probe environment
- **TCP/IP**: Connect to a remote J-Link over the network (requires J-Link with Ethernet support)
  - Enter the J-Link IP address

### Step 3: Target Device

Depending on the selected probe type, the corresponding configuration row is displayed:

**J-Link Target Device:**

- Select the chip model from the dropdown (e.g., STM32F407VE, Cortex-M4)
- The dropdown is editable; you can type the model directly
- **...** button: Opens the device model filter dialog, where you can search and filter, and view chip Flash/RAM size, Core ID, and other information
- **Update** button: Re-reads the device list from the JLink DLL and saves it to `runtime/devices.txt`

**Other Link Target Device (DAP-Link / ST-Link and other CMSIS-DAP probes):**

- Select the PyOCD target type from the dropdown (e.g., stm32f407ve, r7ka8p1kf)
- The dropdown is editable; you can type directly
- **...** button: Opens the PyOCD target filter dialog, where you can view the target source (builtin / pack installation); entries from Pack are highlighted in green
- **Update** button: Re-scans all CMSIS Pack files and refreshes the target list
- **Pack** button: Download CMSIS Pack. Click and enter the chip model (e.g., STM32U575); the program automatically downloads and installs from the official Keil Pack source, and the chip will appear in the target list after installation

> **Note**: Before connecting with DAP-Link/ST-Link, ensure the target chip's Pack is installed or that PyOCD has built-in support for the chip.

### Step 4: Interface Settings

| Parameter | Description |
|-----------|-------------|
| **Interface** | SWD (default) or JTAG. SWD is sufficient for the vast majority of MCUs |
| **Speed** | 17 speed options from 125kHz to 50000kHz. **4000kHz** is recommended for a balance of stability and speed. Higher frequencies can be tried for high-speed targets; reduce speed if connection is unstable |
| **Connection Mode** | under_reset (reset then connect, default), halt_on_connect (halt after connect), pre_reset (reset before connect), attach (attach directly without halting), default (default behavior) |

### Step 5: RTT Control Block

The RTT control block is a structure in MCU memory that stores RTT channel information. There are 4 ways to locate it:

| Mode | Description | Use Case |
|------|-------------|----------|
| **Auto Detect** | J-Link automatically searches for the RTT control block signature in memory | Most single-core MCUs; recommended as the first choice |
| **Address** | Manually specify the RTT control block address in RAM | Use when auto detection fails |
| **Search Range** | Specify RAM start address and size; search within this range | Multi-AP chips (e.g., Renesas RZ series) or MCUs with special RAM layout |
| **Map File Search** | Parse the compiler-generated .map file and automatically extract the `_SEGGER_RTT` symbol address | Automatically adapts when the RTT address changes after each recompilation |

**Map File Search Usage:**

1. Select "Address" mode
2. Click **Open map file** and select the compiler-generated .map file
3. Click **Search _SEGGER_RTT**; the program automatically parses and fills in the address
4. Supports GCC, IAR, Keil, and other mainstream compiler formats

**Search Range Usage:**

1. Select "Search Range" mode
2. Click **Get auto-detect address**; the program automatically fills in the RAM start address and size based on the chip model
3. You can also manually enter the start address and search size

> **Note**: When auto detection fails, try "Address" mode first and get the `_SEGGER_RTT` symbol address from the .map file.

### OK / Cancel

After configuration, click **OK** to save and start connecting, or click **Cancel** to discard changes.

---

## Data Transmission and Reception

### Receive Area

- Displays data sent by the MCU through the RTT up channel
- Displays in text mode by default; check **HEX Display** to switch to hexadecimal
- Check **Timestamp** to add arrival time to each line of data
- When **ANSI Color** is enabled, color escape codes in RTT data are rendered as colored text
- When **Keyword Highlight** is enabled, specific words like ERROR and WARNING are automatically colored
- The receive area retains up to 1000 lines; older content is automatically cleared when exceeded (does not affect log files)
- All received data is simultaneously written to the log file `runtime/log/rtt_data_YYYYMMDD_HHMMSS.log`

### Send Area

- Type text and press **Enter** to send; press **Shift+Enter** for a new line
- Two send modes are supported:

| Mode | Description | Example |
|------|-------------|---------|
| **String** | Send UTF-8 text; MCU receives it as a string | `AT+OK` → sends 5 bytes |
| **HEX** | Send hexadecimal bytes, space-separated | `01 02 A0 FF` → sends 4 bytes |

- Check **Add newline** to automatically append `\r\n` to the sent content
- The byte count of sent data is displayed to the right of the send button

---

## Oscilloscope Mode

Oscilloscope mode is used to display numerical data sent by the MCU in real time, showing it as waveform curves, similar to a virtual oscilloscope.

### Switching Modes

Click the **Mode** button on the toolbar and select **Oscilloscope** or **Mixed** mode:

- **Log mode**: Display only the RTT text receive area
- **Oscilloscope mode**: Display only the waveform view
- **Mixed mode**: Split view showing both the text receive area and waveform view simultaneously

### Acquisition Control

| Button | Description |
|--------|-------------|
| **Start** | Start data acquisition; button changes to "Stop" |
| **Stop** | Stop acquisition and clear the waveform canvas |
| **Pause** | Freeze the current display; data continues to be received in the background; button changes to "Resume" |
| **Resume** | Resume real-time display |
| **Clear** | Clear all channel curves and data |

### Waveform Display Controls

| Control | Description |
|---------|-------------|
| **Timebase** | Horizontal axis time scale, 27 adjustable steps from 1µs/div to 500s/div |
| **Trigger** | Auto (continuous display), Normal (display when trigger condition is met), Single (stop after one trigger) |
| **Color Scheme** | Channel curve color scheme: Default / Warm / Cool / Grayscale |
| **Style** | Drawing style: Line / Point / Line+Point / Step |
| **Sample Rate** | Set sampling frequency (Hz); 0 for auto-estimation (sample as fast as possible) |

Mouse operations in the waveform area:

- **Scroll wheel**: Zoom in/out timebase (scroll up to speed up, scroll down to slow down)
- **Mouse hover**: Display crosshair cursor and current coordinates `x=... y=...`
- **Right-click menu**: Auto range, reset view, toggle grid display

### MCU Data Format

Oscilloscope mode supports three data formats:

#### JScope Standard Format (Recommended)

The MCU declares the data structure through the RTT channel name. The channel name must start with `JScope_`, followed by field descriptors:

```
JScope_<type1><size1><type2><size2>...
```

Field descriptors:

| Descriptor | Type | Size |
|------------|------|------|
| `t4` | Timestamp (microseconds) | 4 bytes |
| `i1` | int8 | 1 byte |
| `i2` | int16 | 2 bytes |
| `i4` | int32 | 4 bytes |
| `u1` | uint8 | 1 byte |
| `u2` | uint16 | 2 bytes |
| `u4` | uint32 | 4 bytes |

Example: `JScope_t4i4u1` means "4-byte timestamp + 4-byte int32 + 1-byte uint8", 9 bytes per packet.

After a successful connection, RTT Assistant automatically parses the format descriptor from the channel name and displays it in the **Format** label on the toolbar.

#### Auto-Detection Mode

If the channel name does not start with `JScope_`, auto-detection mode is used: each value is preceded by a 1-byte type identifier.

| type_byte | Type |
|-----------|------|
| 0x01 | int8 |
| 0x02 | uint8 |
| 0x03 | int16 |
| 0x04 | uint16 |
| 0x05 | int32 |
| 0x06 | uint32 |
| 0x07 | float |

#### Fixed Format

Manually select a fixed type (int8 / uint8 / int16 / uint16 / int32 / uint32 / float); all values are parsed according to that type.

### High-Speed Mode

The program automatically switches processing mode based on data volume:

- **< 2000 samples/sec**: Normal mode, processed directly in the main thread
- **> 5000 samples/sec**: Automatically switches to high-speed mode, independent thread + 30FPS downsampled display (peak detection algorithm)
- Switching is automatic and requires no user intervention

In high-speed mode, the buffer can cache up to 1,000,000 samples, and display downsamples to 2000 points, ensuring smooth waveforms without slowing down the interface.

### MCU Buffer Information

The **MCU Buffer** label on the toolbar displays the buffer size for each channel (e.g., `CH1=1024B`); hover the mouse to view the channel name and detailed size.

---

## Log Window

Open the system log window via **Log → System Log** on the toolbar.

- Displays system runtime logs in real time, automatically refreshing every 1 second
- Supports filtering by log level: All / DEBUG / INFO / WARNING / ERROR / SUCCESS
- Color-coded by level: DEBUG gray, INFO green, WARNING yellow, ERROR red, SUCCESS cyan
- **Clear** button clears the display content
- **Open Log File** button directly opens `runtime/log/rtt_system.log`
- Log files auto-rotate; single file max 5MB with 3 backup copies retained

---

## Variable Monitor

The variable monitor is used to read the values of specified variables in MCU memory in real time.

- **Add variable**: Opens a dialog to enter variable name, memory address (hexadecimal), and data type
- **Delete variable**: Select a row and delete it
- Table display: Name, Address, Type, Current Value, Update Time
- The program automatically reads variable values at a fixed interval (default 100ms) and updates the display

Supported variable types: uint8, int8, uint16, int16, uint32, int32, float

> **Note**: Variable monitoring relies on the debug probe's memory read functionality; some probes may have delayed responses under high load.

---

## MCU Integration Guide

### RTT Porting

The MCU needs to have the SEGGER RTT code ported. Basic steps:

1. Obtain the RTT source code from the SEGGER website or the program's built-in resources (`resources/RTT.zip`)
2. Add `SEGGER_RTT.c`, `SEGGER_RTT.h`, and `SEGGER_RTT_Conf.h` to the project
3. Call `SEGGER_RTT_Init()` to initialize
4. Compile and download to the MCU

For detailed porting steps, refer to the program menu **Help → SEGGER RTT → Porting Guide**.

### Log Mode (Channel 0)

Channel 0 is the default RTT debug channel; no additional MCU-side configuration is needed after initialization:

```c
#include "SEGGER_RTT.h"

// Initialize (typically called once at the beginning of main)
SEGGER_RTT_Init();

// Send text
SEGGER_RTT_WriteString(0, "Hello RTT Assistant!\r\n");

// Formatted output
SEGGER_RTT_printf(0, "Temperature: %d, Humidity: %d%%\r\n", temp, humidity);
```

Data from channel 0 is displayed in the RTT Assistant **receive area**.

### Oscilloscope Mode (Channel 1)

Oscilloscope mode typically uses channel 1 (or another non-zero channel). The MCU needs to:

1. Call `SEGGER_RTT_ConfigUpBuffer()` to configure the channel, with the channel name declaring the JScope data format
2. Pack binary data according to the declared format and call `SEGGER_RTT_Write()` to send

```c
#include "SEGGER_RTT.h"

// Configure channel 1, channel name declares data format
// JScope_t4i4u1 = 4-byte timestamp + 4-byte int32 + 1-byte uint8
SEGGER_RTT_ConfigUpBuffer(1, "JScope_t4i4u1", NULL, 0, SEGGER_RTT_MODE_NO_BLOCK_SKIP);

// Send data according to format
void send_data(int32_t value, uint8_t status) {
    uint8_t packet[9];
    uint32_t ts = get_timestamp_us();   // Microsecond timestamp

    *(uint32_t*)&packet[0] = ts;        // t4: timestamp
    *(int32_t*)&packet[4]  = value;     // i4: int32
    packet[8] = status;                 // u1: uint8

    SEGGER_RTT_Write(1, packet, 9);
}
```

> **Note**:
> - The channel name must start with `JScope_`, otherwise it will be treated as auto-detection mode
> - Data packets must strictly follow the field order and size declared in the channel name, otherwise parsing will be misaligned
> - Buffer mode should use `SEGGER_RTT_MODE_NO_BLOCK_SKIP` to prevent the MCU from blocking when the buffer is full
> - The timestamp field `t4` must be in the first position

### Using ANSI Color Output

RTT supports ANSI escape codes; the MCU can use SEGGER RTT predefined color macros:

```c
#include "SEGGER_RTT.h"

SEGGER_RTT_WriteString(0, SEGGER_RTT_CTRL_RESET "Normal text\r\n");
SEGGER_RTT_WriteString(0, RTT_CTRL_TEXT_RED "Red text\r\n");
SEGGER_RTT_WriteString(0, RTT_CTRL_TEXT_GREEN "Green text\r\n");
SEGGER_RTT_WriteString(0, RTT_CTRL_TEXT_YELLOW "Yellow text\r\n");
SEGGER_RTT_WriteString(0, RTT_CTRL_TEXT_BLUE "Blue text\r\n");
SEGGER_RTT_WriteString(0, RTT_CTRL_BG_RED "Red background\r\n");
```

RTT Assistant must have **Tools → ANSI Color** enabled to display colors correctly.

---

## FAQ

| Issue | Solution |
|-------|----------|
| **J-Link DLL not found** | Place `JLink_x64.dll` (64-bit) or `JLinkARM.dll` (32-bit) in the `runtime/dll/` directory |
| **DAP-Link / ST-Link connection failed** | Confirm the CMSIS Pack for the target chip has been downloaded, or click the **Pack** button in the configuration dialog to download |
| **Probe list is empty** | Check USB connection; for J-Link, confirm the J-Link software package is installed; for DAP-Link, confirm the driver is working |
| **RTT initialization failed** | Confirm the MCU has the RTT code ported and the initialization function has been called; try using "Address" mode in the configuration dialog and enter the `_SEGGER_RTT` address from the .map file |
| **Target chip list is empty** | J-Link: Click **Update** to refresh from DLL; DAP-Link: Click **Pack** to download the Pack for the target chip |
| **Channel data not displayed** | Confirm the MCU send channel number matches the RTT Assistant configuration; adjust the RTT control block mode in the configuration dialog |
| **No oscilloscope waveform** | Confirm the MCU uses the correct channel naming format (starting with `JScope_`); confirm the data packet format matches the channel name declaration |
| **ANSI colors not displayed** | Confirm **Tools → ANSI Color** is enabled |
| **Slow window startup** | First startup requires loading the device list, which is normal; subsequent startups use cached data for faster loading |
| **Oscilloscope display stuttering** | Try reducing the sample rate or increasing the timebase; the program automatically optimizes in high-speed mode |

---

## File Description

Key files in the program directory:

| File/Directory | Description |
|----------------|-------------|
| `runtime/config/config.json` | Configuration file, stores all connection parameters, display settings, and window settings |
| `runtime/dll/JLink_x64.dll` | J-Link dynamic library (user must place manually) |
| `runtime/packs/*.pack` | CMSIS Pack files (downloaded via the Pack button or placed manually) |
| `runtime/venv/` | Python virtual environment (PyOCD and other dependencies) |
| `log/rtt_system.log` | System log (5MB rotation, 3 backup copies retained) |
| `log/pyocd_diag.log` | PyOCD diagnostic log (5MB rotation, 2 backup copies retained) |
| `log/rttdata_*.log` | RTT data log (new file created for each connection) |
| `log/rtt_devices.txt` | J-Link device list cache |
| `log/pyocd_targets.txt` | PyOCD target list cache |
| `doc/` | Documentation directory |

---

## Notes

1. **J-Link users**: Need to install the J-Link software package (V930+) separately, or place `JLink_x64.dll` in the software directory
2. **DAP-Link / ST-Link users**: No additional drivers required, but need to download the CMSIS Pack for the target MCU
3. **First-time use**: When opening the configuration dialog, device list loading may take a few seconds (loaded asynchronously, does not block the interface)
4. **Multi-probe environment**: In Step 2, check SN/Nickname and enter the serial number to specify which probe to use
5. **Oscilloscope buffer**: In high-speed mode, the buffer can hold up to 1,000,000 samples; excessively high sample rates may still cause data loss
6. **Log files** will continue to grow; it is recommended to periodically clean the `log/` directory
7. **The program supports dark and light themes**, switchable via Tools → Theme
8. **RTT data transmission** uses non-blocking mode (`SEGGER_RTT_MODE_NO_BLOCK_SKIP`); it is recommended that the MCU also use this mode to avoid blocking business logic when the buffer is full

---

## Firmware Flashing

1. **Select firmware file**: Click the **Configure** button on the toolbar, then click **Open** in the "Firmware File Selection" area at the top of the config dialog to select a firmware file (supports .hex / .bin / .elf / .srec formats)
2. **Multi-path management**: Add multiple firmware paths; click to activate; supports **Replace** and **Delete** operations
3. **Click Flash**: Click the **Flash** button on the toolbar; a progress dialog appears showing real-time flash log
4. **Flash Success**: Progress dialog shows green "Flash Successful" label, auto-closes after 2 seconds
5. **Flash Failure**: Progress dialog shows red "Flash Failed" label, stays open for user to review error
6. **Path Linkage**: When selecting a firmware file, if a same-name .map file exists in the same directory, the RTT control block map path is auto-filled; and vice versa
7. **Supported Debuggers**: J-Link (pylink DLL), DAP-Link / ST-Link (pyocd)

---

## Oscilloscope Multi-Channel Usage

### Method 1: Sub-Channel Mode (Recommended for same-frequency same-phase multi-channel)

Use a single RTT channel (e.g., CH1) with JScope merged buffer format (e.g., `JScope_u4u4`) to send all channel data at once. MCU code example:

```c
// Configure channel 1 as JScope_u4u4 format
static char buf1[1024];
SEGGER_RTT_ConfigUpBuffer(1, "JScope_u4u4", buf1, sizeof(buf1), SEGGER_RTT_MODE_NO_BLOCK_SKIP);

// Define merged data structure (1-byte aligned)
#pragma pack(push, 1)
typedef struct {
    uint32_t ch1;
    uint32_t ch2;
    // Can extend with more channels
} MultiChannelData_t;
#pragma pack(pop)

// Send data
MultiChannelData_t data;
temp1 = (temp1 == 100) ? 0 : 100;
temp2 = (temp2 == 90) ? 10 : 90;
data.ch1 = temp1;
data.ch2 = temp2;
SEGGER_RTT_Write(1, &data, sizeof(data));
```

The host software automatically splits CH1 into sub-channels CH1[1] and CH1[2], each displaying waveforms independently with shared time base.

### Method 2: Independent Channel Mode (Recommended for different-frequency multi-channel)

Use multiple RTT channels (CH1~CH10), each sending data independently. MCU code example:

```c
// Configure channel 1
static char buf1[1024];
SEGGER_RTT_ConfigUpBuffer(1, "JScope_u4", buf1, sizeof(buf1), SEGGER_RTT_MODE_NO_BLOCK_SKIP);
// Configure channel 2
static char buf2[1024];
SEGGER_RTT_ConfigUpBuffer(2, "JScope_u4", buf2, sizeof(buf2), SEGGER_RTT_MODE_NO_BLOCK_SKIP);

// Channel 1 sends data
temp1 = (temp1 == 100) ? 0 : 100;
SEGGER_RTT_Write(1, &temp1, 4);

// Channel 2 sends data
temp2 = (temp2 == 90) ? 10 : 90;
SEGGER_RTT_Write(2, &temp2, 1);
```

CH1 and CH2 each display waveforms independently, suitable for different sample rates or different phases.
