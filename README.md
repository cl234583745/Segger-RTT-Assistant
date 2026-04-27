# RTT调试工具

一个功能丰富的RTT调试工具，用于通过JLink RTT与MCU进行通信。

## 功能特性

- ✅ 通过SWD/JTAG接口连接MCU
- ✅ RTT数据接收和发送
- ✅ HEX/字符串显示模式切换
- ✅ HEX/字符串发送模式
- ✅ 时间戳显示
- ✅ 自动添加换行符
- ✅ 窗口置顶
- ✅ 字体设置
- ✅ 配置保存和加载

## 系统要求

- Python 3.8+
- PyQt5
- JLink软件（V930+）

## 安装

### 1. 安装Python依赖

```bash
pip install -r requirements.txt
```

### 2. 安装JLink软件

从SEGGER官网下载并安装JLink软件：
https://www.segger.com/downloads/jlink/

默认安装路径：`D:\Program Files\SEGGER\JLink_V930`

## 使用方法

### 运行程序

```bash
python main.py
```

### 连接MCU

1. 点击工具栏的"连接"按钮
2. 程序将自动连接到MCU并初始化RTT
3. 连接成功后，状态栏显示"已连接"

### 接收数据

- 接收到的数据会自动显示在接收区
- 可以选择"HEX显示"模式查看HEX格式数据
- 可以选择"时间戳"显示接收时间

### 发送数据

1. 在发送区输入要发送的数据
2. 选择发送模式：字符串或HEX
3. 勾选"加换行"可自动添加换行符
4. 点击"发送"按钮或按回车键发送

## 项目结构

```
rtt_tool/
├── ui/                     # 表示层
│   └── main_window.py      # 主窗口
├── controller/             # 控制器层
│   └── main_controller.py  # 主控制器
├── service/                # 业务逻辑层
│   ├── connection_service.py    # 连接服务
│   ├── data_receive_service.py  # 数据接收服务
│   └── data_send_service.py     # 数据发送服务
├── infrastructure/         # 基础设施层
│   ├── jlink_rtt_wrapper.py     # JLink RTT封装
│   └── ring_buffer.py           # 环形缓冲区
└── utils/                  # 工具类
    ├── config_service.py        # 配置管理
    └── data_format_service.py   # 数据格式化
```

## 打包为EXE

使用PyInstaller打包为独立的exe文件：

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "RTT-Tool" main.py
```

打包后的exe文件位于`dist/RTT-Tool.exe`

## 配置文件

程序会在运行目录下创建`config.json`配置文件，保存以下设置：

- 连接参数（设备型号、接口类型、速度）
- 显示设置（时间戳、HEX显示）
- 窗口设置（大小、置顶）
- 字体设置

## 注意事项

1. 确保JLink已正确安装，程序会自动查找JLinkARM.dll
2. MCU需要已移植RTT代码并初始化
3. 首次连接可能需要几秒钟时间
4. 大量数据接收时建议使用HEX显示模式

## 许可证

MIT License

## 作者

陈卡卡