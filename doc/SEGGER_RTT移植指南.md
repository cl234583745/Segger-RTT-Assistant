# SEGGER RTT 移植指南

本文档面向 MCU 端开发者，介绍如何移植 SEGGER RTT 并与 RTT Assistant 配合使用。RTT Assistant 支持两种工作模式，MCU 端通过不同的通道来区分：

| 模式 | 通道 | 用途 | 数据格式 |
|------|------|------|----------|
| **日志模式** | 通道 0 | 文本调试输出、log 打印 | UTF-8 文本，可选 ANSI 颜色码 |
| **示波器模式** | 通道 1 | 实时数值数据波形显示 | JScope 标准格式二进制包 |

---

## RTT 移植

### 获取源码

将以下文件加入嵌入式工程：

| 文件 | 说明 |
|------|------|
| `SEGGER_RTT.c` | RTT 核心实现 |
| `SEGGER_RTT.h` | 头文件 |
| `SEGGER_RTT_Conf.h` | 配置（缓冲区大小、通道数等） |
| `SEGGER_RTT_printf.c` | 可选，提供 `SEGGER_RTT_printf()` 函数 |
| `SEGGER_RTT_ASM_ARMv7M.S` | 可选，ARM Cortex-M 汇编加速 |

源码可从 SEGGER 官网获取，也可使用 RTT Assistant 内附的 `resources/RTT.zip`。

### 配置缓冲区

编辑 `SEGGER_RTT_Conf.h`，根据需求调整：

```c
// 上行缓冲区大小（MCU → 主机）
// 通道 0（日志）：建议 1024 以上，文本输出较多时可以更大
// 通道 1（示波器）：取决于数据包大小和发送频率
#define BUFFER_SIZE_UP          (2048)

// 下行缓冲区大小（主机 → MCU）
#define BUFFER_SIZE_DOWN        (128)

// 上行通道数：至少 2（通道 0 日志 + 通道 1 示波器）
#define SEGGER_RTT_MAX_NUM_UP_BUFFERS   (3)

// 下行通道数
#define SEGGER_RTT_MAX_NUM_DOWN_BUFFERS (3)

// 默认写入模式：不阻塞，缓冲区满时丢弃新数据
#define SEGGER_RTT_MODE_DEFAULT         SEGGER_RTT_MODE_NO_BLOCK_SKIP
```

### 初始化

在 `main()` 开头或系统初始化后调用：

```c
#include "SEGGER_RTT.h"

int main(void) {
    SystemInit();
    SEGGER_RTT_Init();          // 初始化 RTT 控制块
    // ... 其他初始化 ...
}
```

`SEGGER_RTT_Init()` 会创建默认的通道 0（上行+下行），此后可直接使用。

---

## 日志模式（通道 0）

通道 0 是 RTT 默认的调试输出通道，初始化后无需额外配置即可使用。

### 基础用法

```c
// 字符串输出
SEGGER_RTT_WriteString(0, "System started\r\n");

// 格式化输出
SEGGER_RTT_printf(0, "温度: %d°C, 湿度: %d%%\r\n", temp, humidity);

// 二进制数据
uint8_t data[] = {0x01, 0x02, 0x03};
SEGGER_RTT_Write(0, data, sizeof(data));
```

### ANSI 彩色输出

RTT Assistant 支持 ANSI 转义码染色（需在工具菜单中开启）。SEGGER RTT 预定义了颜色宏：

```c
SEGGER_RTT_WriteString(0, RTT_CTRL_TEXT_RED    "[ERROR] 系统故障\r\n");
SEGGER_RTT_WriteString(0, RTT_CTRL_TEXT_YELLOW  "[WARN]  温度过高\r\n");
SEGGER_RTT_WriteString(0, RTT_CTRL_TEXT_GREEN   "[INFO]  任务完成\r\n");
SEGGER_RTT_WriteString(0, RTT_CTRL_TEXT_BLUE    "[DEBUG] x=100\r\n");
SEGGER_RTT_WriteString(0, RTT_CTRL_RESET        "普通文字\r\n");
```

可用的颜色宏定义在 `SEGGER_RTT.h` 中：

| 宏 | 效果 |
|----|------|
| `RTT_CTRL_TEXT_BLACK` / `WHITE` / `RED` / `GREEN` / `BLUE` / `YELLOW` / `CYAN` / `MAGENTA` | 文字颜色 |
| `RTT_CTRL_BG_...`（同上颜色） | 背景颜色 |
| `RTT_CTRL_RESET` | 重置所有属性 |

> **注意**：`SEGGER_RTT_printf()` 内部使用 `SEGGER_RTT_Write()`，颜色宏在格式化字符串中可能会被截断。建议颜色宏单独通过 `SEGGER_RTT_WriteString()` 输出，或确认你的 `SEGGER_RTT_Conf.h` 中 `PRINTF_USE_SEGGER_RTT` 配置正确。

---

## 示波器模式（通道 1）

示波器模式使用通道 1（或其他非 0 通道）发送结构化数值数据，RTT Assistant 以波形曲线实时显示。

### 配置通道

通道 1 不会自动创建，需要用 `SEGGER_RTT_ConfigUpBuffer()` 显式配置。**通道名用于声明数据格式**，必须遵循 JScope 命名规则：

```c
SEGGER_RTT_ConfigUpBuffer(1, "JScope_<字段描述符>", NULL, 0, SEGGER_RTT_MODE_NO_BLOCK_SKIP);
```

第三个参数传 `NULL` 让 RTT 内部管理缓冲区，第四个参数 `0` 表示使用 `SEGGER_RTT_Conf.h` 中 `BUFFER_SIZE_UP` 的大小。

如需自定义缓冲区大小：

```c
static uint8_t scope_buf[1024];
SEGGER_RTT_ConfigUpBuffer(1, "JScope_t4i4u1", scope_buf, sizeof(scope_buf), SEGGER_RTT_MODE_NO_BLOCK_SKIP);
```

### JScope 数据格式

通道名 `JScope_` 后的字符串声明了数据包的结构。每个字段由 **类型字母 + 字节数** 组成：

| 描述符 | C 类型 | 大小 | 说明 |
|--------|--------|------|------|
| `t4` | `uint32_t` | 4 字节 | 时间戳（微秒），**必须放在第一个字段** |
| `i1` | `int8_t` | 1 字节 | 有符号 8 位整数 |
| `i2` | `int16_t` | 2 字节 | 有符号 16 位整数 |
| `i4` | `int32_t` | 4 字节 | 有符号 32 位整数 |
| `u1` | `uint8_t` | 1 字节 | 无符号 8 位整数 |
| `u2` | `uint16_t` | 2 字节 | 无符号 16 位整数 |
| `u4` | `uint32_t` | 4 字节 | 无符号 32 位整数 |

所有多字节字段均为 **小端序**（Little-Endian）。

### 常见格式示例

| 通道名 | 包大小 | 字段说明 |
|--------|--------|----------|
| `JScope_t4i4` | 8 字节 | 时间戳 + int32 |
| `JScope_t4u4u4` | 12 字节 | 时间戳 + uint32 + uint32 |
| `JScope_i4i4` | 8 字节 | int32 + int32（无时间戳） |
| `JScope_t4i2u2u1` | 9 字节 | 时间戳 + int16 + uint16 + uint8 |
| `JScope_t4f4` | 8 字节 | 时间戳 + float（需要 RTT Assistant 2.x 支持） |

> **注意**：多字节类型使用 `u4`（4 字节），而非 `u2`（2 字节）或 `u1`（1 字节）。大小必须与实际 C 类型匹配，否则解析错位。

### 示波器模式完整示例

```c
#include "SEGGER_RTT.h"
#include <stdint.h>

// 通道 1 缓冲区
static uint8_t _scope_buf[1024];

// 初始化示波器通道
void scope_init(void) {
    // 格式：4 字节时间戳 + 4 字节 int32 + 2 字节 uint16 + 1 字节 uint8
    // 每包共 11 字节
    SEGGER_RTT_ConfigUpBuffer(1, "JScope_t4i4u2u1",
                              _scope_buf, sizeof(_scope_buf),
                              SEGGER_RTT_MODE_NO_BLOCK_SKIP);
}

// 发送一帧数据
void scope_send_frame(int32_t value, uint16_t flags, uint8_t status) {
    uint8_t packet[11];
    uint32_t ts = get_system_us();   // 微秒级时间戳

    *(uint32_t*)&packet[0] = ts;       // t4: 时间戳
    *(int32_t*) &packet[4] = value;    // i4: int32
    *(uint16_t*)&packet[8] = flags;    // u2: uint16
    packet[10] = status;               // u1: uint8

    SEGGER_RTT_Write(1, packet, sizeof(packet));
}

// 定时调用（例如在定时器中断或 RTOS 任务中）
void scope_timer_callback(void) {
    static int32_t counter = 0;
    scope_send_frame(counter++, 0x01, 0xAA);
}
```

### 无时间戳的格式

时间戳字段 `t4` 是可选的。省略时间戳时，RTT Assistant 会根据数据到达顺序编号，横轴显示为样本序号而非绝对时间：

```c
// 无时间戳格式：两个 uint32
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

## 自动识别模式（不使用 JScope 命名）

如果通道名不以 `JScope_` 开头，RTT Assistant 会使用自动识别模式。每个数值前需要加 1 字节类型标识：

| type_byte | 类型 |
|-----------|------|
| 0x01 | int8 |
| 0x02 | uint8 |
| 0x03 | int16 |
| 0x04 | uint16 |
| 0x05 | int32 |
| 0x06 | uint32 |
| 0x07 | float |

```c
// 通道名不以 JScope_ 开头，触发自动识别模式
SEGGER_RTT_ConfigUpBuffer(1, "ScopeData", NULL, 0, SEGGER_RTT_MODE_NO_BLOCK_SKIP);

void send_auto_float(float val) {
    uint8_t packet[5];
    packet[0] = 0x07;                      // type_byte: float
    *(float*)&packet[1] = val;
    SEGGER_RTT_Write(1, packet, 5);
}
```

---

## 综合示例：日志 + 示波器同时工作

以下代码展示了通道 0（日志）和通道 1（示波器）同时运行：

```c
#include "SEGGER_RTT.h"
#include <stdint.h>

// 模拟 ADC 读取
static uint32_t read_adc(void) { return /* ... */; }
static uint32_t get_tick_us(void) { return /* 微秒级时间戳 */; }

int main(void) {
    SystemInit();
    SEGGER_RTT_Init();    // 通道 0 自动可用

    // 配置通道 1 为示波器模式
    SEGGER_RTT_ConfigUpBuffer(1, "JScope_t4u4",
                              NULL, 0, SEGGER_RTT_MODE_NO_BLOCK_SKIP);

    SEGGER_RTT_WriteString(0, "System started, logging enabled\r\n");

    uint32_t count = 0;
    while (1) {
        // 日志输出（通道 0）
        SEGGER_RTT_printf(0, "Count: %u, ADC: %u\r\n", count, read_adc());

        // 示波器数据（通道 1）
        uint8_t pkt[8];
        *(uint32_t*)&pkt[0] = get_tick_us();
        *(uint32_t*)&pkt[4] = read_adc();
        SEGGER_RTT_Write(1, pkt, 8);

        count++;
        delay_ms(10);
    }
}
```

在 RTT Assistant 中：
1. 连接后接收区自动显示通道 0 的日志文本
2. 切换到 **示波器模式** 或 **混合模式**，点击 **开始** 显示通道 1 的 ADC 波形
3. 工具栏的 **格式** 标签会显示自动解析到的 `timestamp(µs) + uint32`

---

## 通道配置对照表

| 步骤 | 日志模式（通道 0） | 示波器模式（通道 1） |
|------|-------------------|---------------------|
| 初始化 | 由 `SEGGER_RTT_Init()` 自动创建 | 需调用 `SEGGER_RTT_ConfigUpBuffer()` |
| 通道名 | 无需设置（内部名称） | 必须设为 `JScope_<格式>` |
| 缓冲区 | `BUFFER_SIZE_UP` 默认分配 | 可自定义或使用默认大小 |
| 写入函数 | `WriteString` / `printf` / `Write` | `Write`（二进制数据） |
| 写入模式 | 建议 `NO_BLOCK_SKIP` | 建议 `NO_BLOCK_SKIP` |
| 数据类型 | UTF-8 文本 | 结构化二进制包 |
| RTT Assistant 模式 | 日志模式 | 示波器模式 |

---

## 注意事项

1. **通道 0 不要改名**：通道 0 是 SEGGER RTT 默认调试通道，不要用 `SEGGER_RTT_ConfigUpBuffer(0, ...)` 更改其通道名，否则可能影响 RTT Assistant 的文本显示
2. **示波器通道建议用通道 1**：虽然可用任意非 0 通道，但 RTT Assistant 默认监听通道 1 做波形显示
3. **缓冲区模式用 NO_BLOCK_SKIP**：`SEGGER_RTT_MODE_NO_BLOCK_SKIP` 确保 MCU 不会被 RTT 缓冲区写满阻塞，是生产环境的推荐配置
4. **时间戳精度**：`t4` 字段为微秒级，MCU 需要提供可靠的微秒计时。如果计时不准，波形横轴会失真。没有可靠时间源时可以省略 `t4`
5. **数据包对齐**：ARM Cortex-M 上非对齐访问可能会触发 fault 或性能损失。建议将数据包按 4 字节对齐，或在发送前用 `memcpy` 逐字节填充
6. **不要混用通道**：示波器数据只走配置了 JScope 格式的通道，日志文本走通道 0，不要在同一通道中混合发送文本和二进制数据
