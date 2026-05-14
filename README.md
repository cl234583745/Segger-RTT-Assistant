# RTT调试工具

一个功能丰富的RTT调试工具，用于通过JLink RTT或PyOCD（DAP-Link/ST-Link）与MCU进行通信。

## 功能特性

- ✅ 通过SWD/JTAG接口连接MCU
- ✅ **支持多种调试探针**：J-Link、DAP-Link、ST-Link（通过PyOCD后端）
- ✅ RTT数据接收和发送
- ✅ HEX/字符串显示模式切换
- ✅ HEX/字符串发送模式
- ✅ 时间戳显示
- ✅ 自动添加换行符
- ✅ 窗口置顶
- ✅ 字体设置
- ✅ 配置保存和加载
- ✅ ANSI转义码染色（兼容SEGGER RTT颜色宏）
- ✅ 关键字高亮（ERROR/WARN/OK/INFO等，支持自定义规则）
- ✅ RTT搜索日志增强（memory zones、buffer信息）
- ✅ RTT范围搜索模式（起始地址+大小）
- ✅ 设备列表从DLL更新（完整属性读取，v2结构化格式）
- ✅ 连接时设备信息日志打印
- ✅ J-Link DLL版本/设备数显示，状态栏显示SN/HW/FW
- ✅ **RTT控制块搜索范围自动填充**（从devices.txt自动获取RAM信息）
- ✅ **Map文件符号搜索**（自动提取_SEGGER_RTT地址）
- ✅ **连接时自动更新RTT地址**（MCU重新编译后自动适配）
- ✅ **DEBUG日志级别筛选**（性能追踪分析）
- ✅ **CMSIS Pack支持**（自动加载Pack中的目标芯片定义）
- ✅ **pyocd.yaml自动同步**（用户添加Pack后刷新即可更新）

## 系统要求

- Python 3.8+
- PyQt5
- J-Link软件（V930+）或 DAP-Link/ST-Link 探针

## 安装

### 1. 安装Python依赖

```bash
pip install -r requirements.txt
```

### 2. 准备调试探针

**J-Link方式**：将`JLink_x64.dll`（64位）或`JLinkARM.dll`（32位）放在程序目录下。也可从SEGGER官网安装JLink软件：https://www.segger.com/downloads/jlink/

**DAP-Link/ST-Link方式**：安装PyOCD依赖：
```bash
pip install pyocd usb1
```
并将`.pack`文件放入程序目录下的`packs/`文件夹。

## 使用方法

### 运行程序

```bash
python main.py
```

### 连接MCU

1. 点击工具栏的"连接"按钮
2. 在配置对话框中按步骤操作：
   - **步骤1**：选择调试器（J-Link或DAP-Link/ST-Link）
   - **步骤2**：选择连接方式（USB/TCP/IP）
   - **步骤3**：选择目标设备（J-Link设备或PyOCD目标）
   - **步骤4**：设置接口和速度
   - **步骤5**：配置RTT控制块搜索方式
3. 连接成功后，状态栏显示探针序列号和版本信息

### 接收数据

- 接收到的数据会自动显示在接收区
- 可以选择"HEX显示"模式查看HEX格式数据
- 可以选择"时间戳"显示接收时间
- 通过工具菜单 → ANSI染色，启用ANSI转义码颜色解析
- 通过工具菜单 → 关键字高亮，启用关键字匹配高亮

### 发送数据

1. 在发送区输入要发送的数据
2. 选择发送模式：字符串或HEX
3. 勾选"加换行"可自动添加换行符
4. 点击"发送"按钮或按回车键发送

## 项目结构

```
rtt_tool/
├── ui/                     # 表示层
│   ├── main_window.py      # 主窗口
│   ├── connection_dialog.py # 连接配置对话框
│   └── log_window.py       # 日志窗口
├── controller/             # 控制器层
│   └── main_controller.py  # 主控制器
├── service/                # 业务逻辑层
│   ├── connection_service.py    # 连接服务
│   ├── data_receive_service.py  # 数据接收服务
│   ├── data_send_service.py     # 数据发送服务
│   └── log_service.py           # 日志服务
├── backend/                # 调试器后端
│   ├── base.py                 # 后端基类
│   ├── jlink_backend.py        # J-Link后端
│   ├── pyocd_backend.py        # PyOCD后端（DAP-Link/ST-Link）
│   └── manager.py              # 后端管理器
├── infrastructure/         # 基础设施层
│   ├── jlink_rtt_wrapper.py     # JLink RTT封装
│   └── ring_buffer.py           # 环形缓冲区
└── utils/                  # 工具类
    ├── config_service.py        # 配置管理
    ├── device_info.py           # 设备信息数据模型
    ├── device_info_service.py   # 设备信息服务
    ├── resource_utils.py        # 资源路径工具
    └── data_format_service.py   # 数据格式化
```

## 打包为EXE

使用PyInstaller打包为独立的exe文件：

```bash
pip install pyinstaller
python build.py
```

打包后的exe文件位于`dist/Segger-RTT-Assistant v1.5.0.exe`

**注意**：以下文件需与exe放在同一目录，打包脚本会自动复制：
- `config.json` — 配置文件
- `JLink_x64.dll` — J-Link驱动（可选）
- `devices.txt` — J-Link设备列表
- `pyocd.yaml` — PyOCD配置（自动生成）
- `pyocd_targets.txt` — PyOCD目标列表缓存
- `packs/` — CMSIS Pack文件目录
- `libusb-1.0.dll` — USB驱动库

## 配置文件

程序会在exe同目录下创建`config.json`配置文件，保存以下设置：

- 连接参数（设备型号、接口类型、速度、RTT模式/地址/范围、探针选择）
- 显示设置（时间戳、HEX显示、ANSI染色、关键字高亮）
- 窗口设置（大小、置顶）
- 字体设置
- 关键字高亮规则

## 注意事项

1. 将`JLink_x64.dll`放在exe同目录，程序会自动查找
2. DAP-Link/ST-Link探针需要`packs/`目录下有对应的`.pack`文件
3. MCU需要已移植RTT代码并初始化
4. 首次连接可能需要几秒钟时间
5. 大量数据接收时建议使用HEX显示模式
6. 多AP芯片（如瑞萨RZ系列Cortex-A/R）建议使用"搜索范围"模式指定RTT控制块所在RAM区域
7. 用户可自行下载CMSIS Pack文件放入`packs/`目录，点击"更新"按钮刷新

## 许可证

GNU General Public License v3.0 (GPL v3)

本项目使用PyQt5 (GPL v3)作为GUI框架，根据GPL v3条款，本项目以GPL v3发布。

## 作者

陈卡卡
