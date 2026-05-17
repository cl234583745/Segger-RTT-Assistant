# Runtime 运行时依赖目录

此目录存放 RTT Assistant 的所有运行时依赖，与源代码完全分离。

## 目录结构

```
runtime/
├── venv/             # Python 虚拟环境 (标准 venv)
│   ├── Lib/site-packages/  # 所有 Python 第三方包
│   ├── Scripts/            # python.exe, pip.exe
│   └── ...
├── dll/              # DLL 文件 (JLink_x64.dll, libusb-1.0.dll 等)
├── packs/            # CMSIS Pack 文件 (*.pack)
```

## 手动替换升级

直接替换对应目录中的文件即可：
- Python 包: 替换 `venv/Lib/site-packages/` 下对应的包文件夹
- DLL: 替换 `dll/` 下的 DLL 文件
- Pack: 替换 `packs/` 下的 .pack 文件

## 依赖管理

软件内帮助菜单 → "依赖管理" 可查看版本和一键升级。
