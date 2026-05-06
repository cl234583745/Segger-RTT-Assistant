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
- ✅ ANSI转义码染色（兼容SEGGER RTT颜色宏）
- ✅ 关键字高亮（ERROR/WARN/OK/INFO等，支持自定义规则）
- ✅ RTT搜索日志增强（memory zones、buffer信息）
- ✅ RTT范围搜索模式（起始地址+大小）
- ✅ 设备列表从DLL更新（完整属性读取，v2结构化格式）
- ✅ 连接时设备信息日志打印
- ✅ J-Link DLL版本/设备数显示，状态栏显示SN/HW/FW

## 系统要求

- Python 3.8+
- PyQt5
- JLink软件（V930+）

## 安装

### 1. 安装Python依赖

```bash
pip install -r requirements.txt
```

### 2. 准备JLink DLL

将`JLink_x64.dll`（64位）或`JLinkARM.dll`（32位）放在程序目录下。

也可从SEGGER官网安装JLink软件：https://www.segger.com/downloads/jlink/

## 使用方法

### 运行程序

```bash
python main.py
```

### 连接MCU

1. 点击工具栏的"连接"按钮
2. 在连接对话框中选择设备型号、接口类型、速度
3. 选择RTT控制块搜索模式：自动检测 / 指定地址 / 搜索范围
4. 连接成功后，状态栏显示J-Link序列号和版本信息

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
├── infrastructure/         # 基础设施层
│   ├── jlink_rtt_wrapper.py     # JLink RTT封装
│   └── ring_buffer.py           # 环形缓冲区
└── utils/                  # 工具类
    ├── config_service.py        # 配置管理
    ├── device_info.py           # 设备信息数据模型
    ├── device_info_service.py   # 设备信息服务（读取/持久化/日志）
    ├── resource_utils.py        # 资源路径工具
    └── data_format_service.py   # 数据格式化
```

## 打包为EXE

使用PyInstaller打包为独立的exe文件：

```bash
pip install pyinstaller
pyinstaller RTT-Assistant.spec
```

打包后的exe文件位于`dist/Segger-RTT-Assistant vx.x.x.exe`

**注意**：`config.json`、`JLink_x64.dll`、`devices.txt`需与exe放在同一目录。打包脚本会自动复制这些文件到dist目录。

## 配置文件

程序会在exe同目录下创建`config.json`配置文件，保存以下设置：

- 连接参数（设备型号、接口类型、速度、RTT模式/地址/范围）
- 显示设置（时间戳、HEX显示、ANSI染色、关键字高亮）
- 窗口设置（大小、置顶）
- 字体设置
- 关键字高亮规则

## 注意事项

1. 将`JLink_x64.dll`放在exe同目录，程序会自动查找
2. MCU需要已移植RTT代码并初始化
3. 首次连接可能需要几秒钟时间
4. 大量数据接收时建议使用HEX显示模式
5. 多AP芯片（如瑞萨RZ系列Cortex-A/R）建议使用"搜索范围"模式指定RTT控制块所在RAM区域

## 许可证

MIT License

## 作者

陈卡卡
