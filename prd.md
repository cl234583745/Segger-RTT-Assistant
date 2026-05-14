markdown

复制

下载
# RTT Assistant 软件需求规格说明书

## 项目概述

RTT Assistant 是一个基于 PyQt5 的图形化 RTT（Real-Time Transfer）调试工具，用于通过调试器（J-Link / DAP-Link / ST-Link 等）实时读取和显示 MCU 端 SEGGER RTT 库输出的日志数据，并支持高级功能如示波器模式、变量监视等。

## 一、核心架构要求

### 1.1 整体架构原则

- **分层解耦**：UI层、业务逻辑层、硬件抽象层严格分离
- **模块化**：每个功能模块独立，可插拔
- **可扩展**：新调试器类型、新功能模块可轻松添加
- **向后兼容**：不破坏现有功能

### 1.2 目录结构
RTT_Assistant/
├── main.py # 程序入口
├── requirements.txt # Python 依赖
├── README.md # 项目说明
│
├── ui/ # UI 层
│ ├── init.py
│ ├── main_window.py # 主窗口
│ ├── config_dialog.py # 配置对话框
│ ├── log_widget.py # 日志显示组件
│ └── waveform_widget.py # 波形显示组件 (PyQtGraph)
│
├── backend/ # 硬件抽象层
│ ├── init.py
│ ├── base.py # 抽象基类
│ ├── jlink_backend.py # J-Link 实现
│ ├── pyocd_backend.py # PyOCD 实现
│ └── manager.py # 调试器管理器
│
├── processors/ # 数据处理器层
│ ├── init.py
│ ├── base.py # 处理器基类
│ ├── log_processor.py # 文本日志处理
│ ├── waveform_processor.py # 波形数据处理
│ └── variable_monitor.py # 变量监视
│
├── utils/ # 工具函数层
│ ├── init.py
│ ├── map_parser.py # .map 文件解析
│ ├── rtt_address_finder.py # RTT 地址查找
│ └── config_manager.py # 配置管理
│
├── plugins/ # 插件目录（用户扩展）
│ └── (用户自行放置插件)
│
├── packs/ # CMSIS-Pack 目录
│ └── (按需下载的 pack 文件)
│
├── logs/ # 日志保存目录
│ └── (运行产生的日志文件)
│
├── config/ # 配置文件目录
│ └── settings.ini # 用户配置
│
└── JLinkARM.dll # 外置 J-Link DLL（用户自行更新）

text

复制

下载

## 二、硬件抽象层（Hardware Abstraction Layer）

### 2.1 抽象基类设计

```python
# backend/base.py
from abc import ABC, abstractmethod

class DebuggerBackend(ABC):
    """调试器后端抽象基类"""
    
    @abstractmethod
    def connect(self, device: str, rtt_address: int, speed: int = 4000) -> bool:
        """连接调试器
        
        Args:
            device: 芯片型号 (如 "STM32F407VG")
            rtt_address: RTT 控制块地址
            speed: SWD 通信频率 (kHz)
        
        Returns:
            连接是否成功
        """
        pass
    
    @abstractmethod
    def disconnect(self):
        """断开连接"""
        pass
    
    @abstractmethod
    def rtt_read(self, channel: int = 0, timeout_ms: int = 10) -> bytes:
        """读取 RTT 数据
        
        Args:
            channel: RTT 通道号 (0=上行日志)
            timeout_ms: 超时时间(毫秒)
        
        Returns:
            读取到的原始字节数据
        """
        pass
    
    @abstractmethod
    def rtt_write(self, channel: int, data: bytes) -> int:
        """向 RTT 通道写入数据
        
        Args:
            channel: RTT 通道号 (1=下行命令)
            data: 要发送的字节数据
        
        Returns:
            实际发送的字节数
        """
        pass
    
    @abstractmethod
    def get_probe_list(self) -> list:
        """获取已连接的调试器列表
        
        Returns:
            [
                {"type": "jlink", "name": "J-Link (SN:1234)", "backend": "jlink"},
                {"type": "cmsis-dap", "name": "DAP-Link CMSIS-DAP", "backend": "pyocd"}
            ]
        """
        pass
    
    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """返回连接状态"""
        pass
2.2 两种后端实现要求
后端	依赖	实现要点
JLinkBackend	pylink, SEGGER DLL	保持现有代码逻辑，封装成类
PyOCDBackend	pyocd, libusb	调用 PyOCD Python API，支持 CMSIS-DAP 协议
2.3 调试器管理器
python

复制

下载
# backend/manager.py
class DebuggerManager:
    """管理所有后端，实现自动探测和切换"""
    
    def __init__(self):
        self.backends = {
            "jlink": JLinkBackend(),
            "pyocd": PyOCDBackend()
        }
        self.current_backend: DebuggerBackend = None
    
    def detect_all_probes(self) -> list:
        """探测所有已连接的调试器"""
        probes = []
        for name, backend in self.backends.items():
            probes.extend(backend.get_probe_list())
        return probes
    
    def select_backend(self, probe_type: str) -> DebuggerBackend:
        """根据类型选择后端"""
        backend = self.backends.get(probe_type)
        if backend:
            self.current_backend = backend
        return self.current_backend
三、RTT 地址获取模块
3.1 三种地址获取方式（保持现有逻辑）
方式	实现	适用场景
自动搜索	调用后端 API 扫描内存范围	RTT 控制块位置标准时
手动输入	用户直接输入十六进制地址	确定地址时
从 .map 文件解析	解析编译器生成的 .map 文件	瑞萨 MCU 专用，官方工具搜索失败时
3.2 .map 文件解析器
python

复制

下载
# utils/map_parser.py
def parse_map_file(map_path: str) -> dict:
    """解析 .map 文件，提取 SEGGER_RTT 控制块地址
    
    支持编译器格式：
    - ARMCC (Keil MDK)
    - GCC (STM32CubeIDE, RT-Thread Studio)
    - IAR
    
    Args:
        map_path: .map 文件路径
    
    Returns:
        {
            "rtt_address": 0x20001234,
            "symbols": {"_SEGGER_RTT": 0x20001234, ...},
            "sections": {...}
        }
    """
    # 搜索关键字: SEGGER_RTT, _SEGGER_RTT, __SEGGER_RTT
    pass
四、数据处理器模块
4.1 处理器基类
python

复制

下载
# processors/base.py
from abc import ABC, abstractmethod

class DataProcessor(ABC):
    """数据处理器抽象基类"""
    
    @abstractmethod
    def process(self, channel: int, data: bytes):
        """处理接收到的数据"""
        pass
    
    def set_output_widget(self, widget):
        """设置输出控件"""
        self.output_widget = widget
4.2 文本日志处理器（现有功能）
支持通道 0 的文本数据

添加时间戳（毫秒精度）

自动滚动显示

支持 HEX 模式显示

支持日志自动保存到文件

支持日志导出（TXT/CSV）

4.3 波形数据处理器（新功能）
python

复制

下载
# processors/waveform_processor.py
from collections import deque
from processors.base import DataProcessor

class WaveformProcessor(DataProcessor):
    """处理二进制波形数据"""
    
    # 支持的波形数据类型
    TYPE_INT8 = 0x01
    TYPE_UINT8 = 0x02
    TYPE_INT16 = 0x03
    TYPE_UINT16 = 0x04
    TYPE_INT32 = 0x05
    TYPE_UINT32 = 0x06
    TYPE_FLOAT = 0x07
    
    def __init__(self, buffer_size: int = 1024):
        self.buffer_size = buffer_size
        self.channel_buffers: dict[int, deque] = {}  # {channel: deque}
    
    def process(self, channel: int, data: bytes):
        """解析二进制格式：[type][value][type][value]..."""
        self._parse(data)
        # 通过信号发送到 UI 线程
        self.data_updated.emit(channel, self.channel_buffers[channel])
    
    def _parse(self, data: bytes):
        """解析字节流"""
        i = 0
        while i < len(data):
            data_type = data[i]
            i += 1
            
            if data_type == self.TYPE_INT16:
                value = int.from_bytes(data[i:i+2], 'little', signed=True)
                i += 2
                self._add_to_buffer(value)
            # ... 其他类型
4.4 变量监视处理器（新功能）
python

复制

下载
# processors/variable_monitor.py
class VariableMonitor(DataProcessor):
    """监视指定地址的变量值"""
    
    def __init__(self, backend):
        self.backend = backend
        self.variables: dict[str, dict] = {}  # {name: {"address": int, "type": str}}
    
    def add_variable(self, name: str, address: int, var_type: str):
        """添加要监视的变量
        
        Args:
            name: 变量名
            address: 内存地址
            var_type: "uint8", "uint16", "uint32", "int8", "int16", "int32", "float"
        """
        self.variables[name] = {"address": address, "type": var_type}
    
    def read_all(self) -> dict:
        """读取所有监视变量的当前值"""
        results = {}
        for name, info in self.variables.items():
            # 通过后端读取指定地址的内存
            value = self.backend.read_memory(info["address"], info["type"])
            results[name] = value
        return results
五、工作线程设计
5.1 RTT 读取线程
python

复制

下载
# worker/rtt_worker.py
from PyQt5.QtCore import QThread, pyqtSignal

class RTTWorker(QThread):
    """独立的 RTT 数据读取线程"""
    
    # 信号定义（与 UI 线程通信）
    data_received = pyqtSignal(int, bytes)  # (channel, data)
    log_text = pyqtSignal(int, str)         # (channel, text)
    waveform_data = pyqtSignal(int, float)  # (channel, value)
    status_changed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.backend = None
        self.poll_interval_ms = 10  # 默认 10ms
        self.stop_flag = False
        self.paused = False
    
    def run(self):
        """主循环：轮询读取 RTT 数据"""
        while not self.stop_flag:
            if self.paused:
                self.msleep(100)
                continue
            
            try:
                # 读取多个通道
                for channel in [0, 1, 2]:
                    data = self.backend.rtt_read(channel, timeout_ms=5)
                    if data:
                        self.data_received.emit(channel, data)
                
                self.msleep(self.poll_interval_ms)
                
            except Exception as e:
                self.error_occurred.emit(str(e))
                break
    
    def set_poll_interval(self, ms: int):
        """设置轮询间隔"""
        self.poll_interval_ms = max(1, min(ms, 100))
5.2 线程安全要求
不得在子线程中直接操作 UI 控件

所有 UI 更新必须通过信号/槽机制

使用 pyqtSignal 进行跨线程通信

六、UI 界面设计
6.1 主窗口布局
text

复制

下载
┌─────────────────────────────────────────────────────────────┐
│ [菜单栏] 文件 | 工具 | 视图 | 帮助                            │
├─────────────────────────────────────────────────────────────┤
│ [工具栏] 连接 | 断开 | 暂停 | 清空 | 保存 | 配置              │
├─────────────────────────────────────────────────────────────┤
│ 模式切换:  ○ 日志模式  ○ 示波器模式  ○ 混合模式              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                                                     │   │
│  │                 日志显示区域 / 波形显示区域           │   │
│  │                                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ 状态栏: 已连接 | 通道数:3 | 接收速率: 125 KB/s | 运行时间    │
└─────────────────────────────────────────────────────────────┘
6.2 配置对话框
连接配置需要包含：

配置项	说明
调试器选择	自动探测列表 / 手动指定类型
芯片型号	下拉选择或手动输入
SWD 频率	100kHz ~ 15MHz，推荐 4000 kHz
RTT 地址获取	自动搜索 / 手动输入 / 从 .map 导入
轮询间隔	1-100 ms，默认 10 ms
日志保存	路径、自动分割大小
6.3 波形显示配置
配置项	选项
时基	1ms/div, 5ms/div, 10ms/div, 50ms/div, 100ms/div, 500ms/div, 1s/div
触发模式	自动 / 正常 / 单次
触发通道	Channel 0-3
触发边沿	上升沿 / 下降沿
垂直缩放	自动 / 手动
颜色主题	亮色 / 暗色
七、插件系统（远期扩展）
7.1 插件接口定义
python

复制

下载
# plugins/interface.py
from abc import ABC, abstractmethod

class Plugin(ABC):
    """插件基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """插件名称"""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """插件版本"""
        pass
    
    @abstractmethod
    def on_load(self, app_context: dict):
        """加载插件时调用
        
        Args:
            app_context: 包含 backend, ui, config 等对象
        """
        pass
    
    @abstractmethod
    def on_data(self, channel: int, data: bytes):
        """接收到 RTT 数据时调用"""
        pass
    
    def get_config_widget(self) -> QWidget:
        """返回插件配置界面（可选）"""
        return None
7.2 插件管理要求
自动扫描 plugins/ 目录

支持启用/禁用插件

插件提供独立的配置界面

插件运行在独立的线程中，不阻塞主流程

八、打包要求
8.1 打包策略
组件	打包方式	说明
主程序	单个 exe	使用 PyInstaller 或 Nuitka
SEGGER DLL	外置	用户可自行更新
CMSIS-Pack	外置于 packs/	按需下载
配置文件	外置于 config/	JSON/YAML 格式
插件	外置于 plugins/	动态加载
8.2 依赖管理
txt

复制

下载
# requirements.txt
PyQt5>=5.15.0
pyqtgraph>=0.12.0
pylink-square>=0.5.0
pyocd>=0.36.0
numpy>=1.19.0
九、实现优先级
Phase 1：基础设施
硬件抽象层（DebuggerBackend + Manager）

PyOCDBackend 实现（支持 DAP-Link/ST-Link）

RTT 地址获取模块（保持现有三种方式）

Phase 2：核心功能
工作线程重构（使用信号/槽）

数据处理器框架

波形数据处理器（支持二进制格式）

Phase 3：高级功能
变量监视器

下行命令发送

CSV 导出和数据回放

Phase 4：生态建设
插件系统

CMSIS-Pack 管理器

多语言支持（中/英）

十、注意事项
向后兼容：不能破坏现有 J-Link + 瑞萨 MCU .map 文件解析的功能

异常处理：调试器断开、芯片复位等异常情况要优雅处理

性能：轮询读数据不能阻塞 UI，波形更新帧率不低于 30 FPS

线程安全：严格遵守 Qt 的线程模型

代码注释：关键模块和接口必须有详细注释

日志记录：重要操作写入 logs/ 目录，便于用户反馈问题

跨平台兼容：优先保证 Windows，但代码应保持可移植性

十一、关键问题确认
在实现前，请确认以下关键问题：

Python 版本要求：支持 Python 3.8+

PyOCD 后端探测：使用 ConnectHelper.get_all_connected_probes()

波形数据格式：采用 <type><value> 格式，类型字节定义见 4.3 节

跨平台支持：优先 Windows，代码保持跨平台兼容性

text

复制

下载

---

以上是完整的 Markdown 文档内容。请将其全部复制并保存为 `RTT_Assistant_Requirements.md` 文件。