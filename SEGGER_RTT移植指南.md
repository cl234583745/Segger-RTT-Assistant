# SEGGER RTT移植指南

## 什么是SEGGER RTT?

SEGGER RTT (Real-Time Transfer) 是一种用于嵌入式目标系统与主机之间高速数据传输的技术。

### 特点
- **超高速**: 比UART快100倍以上
- **零开销**: 不影响目标系统实时性能
- **双向通信**: 支持上行和下行数据传输
- **多通道**: 支持多达16个虚拟终端

## 移植步骤

### 1. 获取源码

从SEGGER官网或GitHub获取RTT源码:
- https://www.segger.com/products/debug-trace-real-time-real-time-transfer/
- https://github.com/SEGGERMicro/SEGGER_RTT

需要的文件:
- `SEGGER_RTT.c` - RTT实现
- `SEGGER_RTT.h` - RTT头文件
- `SEGGER_RTT_Conf.h` - RTT配置
- `SEGGER_RTT_printf.c` - printf支持(可选)

### 2. 添加到工程

将源码文件添加到你的嵌入式工程中。

**Keil MDK**:
1. 右键工程 → Add Existing Files
2. 选择SEGGER_RTT.c和SEGGER_RTT_printf.c
3. 添加头文件路径

**IAR EWARM**:
1. Project → Add Files
2. 选择源码文件
3. Options → C/C++ Compiler → Additional include directories

**STM32CubeIDE/GCC**:
```makefile
# 添加源文件
SRC += SEGGER_RTT.c
SRC += SEGGER_RTT_printf.c

# 添加头文件路径
INC += -I./SEGGER_RTT
```

### 3. 配置RTT

编辑`SEGGER_RTT_Conf.h`:

```c
// 缓冲区大小(字节)
#define BUFFER_SIZE_UP    (1024)  // 上行缓冲区(目标→主机)
#define BUFFER_SIZE_DOWN  (16)    // 下行缓冲区(主机→目标)

// 通道数量
#define SEGGER_RTT_MAX_NUM_UP_BUFFERS   (3)  // 上行通道数
#define SEGGER_RTT_MAX_NUM_DOWN_BUFFERS (3)  // 下行通道数

// 其他配置
#define SEGGER_RTT_MODE_DEFAULT         SEGGER_RTT_MODE_NO_BLOCK_SKIP
```

### 4. 初始化RTT

在main函数开头初始化:

```c
#include "SEGGER_RTT.h"

int main(void) {
    // 系统初始化
    SystemInit();
    
    // 初始化RTT
    SEGGER_RTT_Init();
    
    // 输出欢迎信息
    SEGGER_RTT_printf(0, "RTT initialized!\r\n");
    
    while(1) {
        // 主循环
    }
}
```

### 5. 使用RTT输出

#### 方法1: 使用printf

```c
SEGGER_RTT_printf(0, "Hello RTT!\r\n");
SEGGER_RTT_printf(0, "Value: %d\r\n", value);
SEGGER_RTT_printf(0, "Float: %.2f\r\n", 3.14);
```

#### 方法2: 使用Write

```c
char data[] = "Hello";
SEGGER_RTT_Write(0, data, strlen(data));
```

#### 方法3: 使用多通道

```c
// 通道0: 普通日志
SEGGER_RTT_printf(0, "Log: System running\r\n");

// 通道1: 错误信息
SEGGER_RTT_printf(1, "Error: Invalid parameter\r\n");

// 通道2: 调试信息
SEGGER_RTT_printf(2, "Debug: x=%d, y=%d\r\n", x, y);
```

### 6. 接收数据

从主机接收数据:

```c
char buffer[32];
int num_bytes;

num_bytes = SEGGER_RTT_Read(0, buffer, sizeof(buffer));
if (num_bytes > 0) {
    // 处理接收到的数据
    process_data(buffer, num_bytes);
}
```

## 连接JLink

### 方法1: JLink RTT Viewer

1. 打开JLink RTT Viewer
2. 配置连接参数:
   - Connection: USB
   - Device: 你的芯片型号
   - Interface: SWD
   - Speed: 4000 kHz
3. 点击"OK"连接
4. 查看RTT输出

### 方法2: RTT Assistant

1. 打开RTT Assistant
2. 点击"配置"设置连接参数
3. 点击"连接"
4. 在接收区查看RTT输出
5. 在发送区发送数据到目标

## 常见问题

### Q1: 找不到RTT控制块?

**原因**: RTT未初始化或缓冲区太小

**解决**:
- 确保调用了`SEGGER_RTT_Init()`
- 增大`BUFFER_SIZE_UP`
- 检查JLink速度设置

### Q2: 数据丢失?

**原因**: 缓冲区溢出

**解决**:
- 增大缓冲区大小
- 使用`SEGGER_RTT_MODE_NO_BLOCK_SKIP`模式
- 减少输出频率

### Q3: 连接速度慢?

**原因**: JLink速度设置太低

**解决**:
- 提高JLink速度(建议4000 kHz以上)
- 使用USB 3.0接口

### Q4: 中文显示乱码?

**原因**: 编码问题

**解决**:
- 确保源码文件为UTF-8编码
- RTT Assistant会自动处理UTF-8

## 性能对比

| 方式 | 速度 | CPU占用 | 优点 | 缺点 |
|------|------|---------|------|------|
| UART | 115200 bps | 高 | 简单通用 | 速度慢 |
| RTT | >1 Mbps | 极低 | 超高速 | 需要JLink |
| Semihosting | 很慢 | 很高 | 无需硬件 | 极慢 |

## 示例代码

### STM32示例

```c
#include "SEGGER_RTT.h"

int main(void) {
    HAL_Init();
    SystemClock_Config();
    
    SEGGER_RTT_Init();
    SEGGER_RTT_printf(0, "\r\nSTM32 RTT Demo\r\n");
    SEGGER_RTT_printf(0, "Clock: %d MHz\r\n", SystemCoreClock / 1000000);
    
    uint32_t count = 0;
    while(1) {
        SEGGER_RTT_printf(0, "Count: %d\r\n", count++);
        HAL_Delay(1000);
    }
}
```

### ESP32示例

```c
#include "SEGGER_RTT.h"

void app_main(void) {
    SEGGER_RTT_Init();
    SEGGER_RTT_printf(0, "\r\nESP32 RTT Demo\r\n");
    
    int count = 0;
    while(1) {
        SEGGER_RTT_printf(0, "Count: %d\r\n", count++);
        vTaskDelay(1000 / portTICK_PERIOD_MS);
    }
}
```

## 参考资料

- [SEGGER RTT官网](https://www.segger.com/products/debug-trace-real-time-real-time-transfer/)
- [RTT知识库](https://kb.segger.com/RTT)
- [JLink用户指南](https://www.segger.com/products/debug-trace-real-time-real-time-transfer/documentation/)

---

**提示**: RTT Assistant可以替代JLink RTT Viewer,提供更友好的界面和更多功能。
