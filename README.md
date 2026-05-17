# RTT Assistant

- 一个功能丰富的RTT调试工具，通过J-Link或DAP-Link/ST-Link与MCU进行SEGGER RTT通信。
- 目前测试和验证了3中调试器：J-Link、DAP-Link、ST-Link。

![](./images/Debug%20support%20list.png)

<div style="display: flex; gap: 5%; justify-content: center; align-items: center; width: 100%;">
    <img src="./images/NUCLEO-U575ZI-Q.jpg" style="width: 28%; height: auto;" />
    <img src="./images/RT-Thread Titan Board.jpg" style="width: 28%; height: auto;" />
    <img src="./images/EK-RA8P1.jpg" style="width: 28%; height: auto;" />
</div>


## 快速开始

1. 双击 `RTT-Assistant v2.0.0.exe` 启动
2. 点击"连接"按钮
3. 选择探针类型（J-Link / DAP-Link / ST-Link）
4. 选择目标芯片，配置接口和速度
5. 点击"确定"连接，开始收发RTT数据

## 功能特性

- 支持多种调试探针：J-Link、DAP-Link、ST-Link（通过PyOCD后端）
- RTT数据收发，HEX/字符串模式，时间戳显示
- ANSI转义码染色（兼容SEGGER RTT颜色宏）
- 关键字高亮（ERROR/WARN/OK/INFO等，支持自定义）
- RTT控制块搜索：自动检测/手动地址/搜索范围/Map文件符号搜索
- CMSIS Pack管理：下载Pack、自动加载目标芯片定义
- 配置保存/加载，窗口置顶，字体设置

## 系统要求

- Windows 10/11（64位）
- J-Link软件（V930+）或 DAP-Link/ST-Link 探针
- MCU需已移植SEGGER RTT代码并初始化

## 目录结构（打包后）

```
RTT-Assistant v2.0.0/
├── RTT-Assistant v2.0.0.exe   # 主程序
├── config/                     # 配置文件
│   └── config.json
├── runtime/
│   ├── dll/                    # 动态链接库
│   │   ├── JLink_x64.dll
│   │   └── libusb-1.0.dll
│   ├── packs/                  # CMSIS Pack文件
│   └── venv/                   # Python虚拟环境（PyOCD等依赖）
├── doc/                        # 文档
├── resources/                  # 资源文件
└── log/                        # 日志（自动创建）
    ├── rtt_system.log          # 系统日志（5MB轮转）
    ├── pyocd_diag.log          # PyOCD诊断日志（5MB轮转）
    └── rttdata_*.log           # RTT数据日志
```

## 源码开发

```bash
pip install -r requirements.txt
python src/scripts/main.py
```

### 打包

```bash
python build.py
```

输出: `dist/RTT-Assistant v2.0.0/`

## 许可证

GNU General Public License v3.0 (GPL v3)

## 作者

陈卡卡
