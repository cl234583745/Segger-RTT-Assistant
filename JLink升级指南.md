# RTT Assistant - JLink升级指南

## 如何升级JLink版本

### 方法1: 直接替换DLL文件(推荐)

这是最简单的方法,无需重新安装JLink软件。

**步骤**:

1. **下载新版JLink**
   - 访问: https://www.segger.com/downloads/jlink/
   - 下载最新版本的JLink软件

2. **提取DLL文件**
   - 安装或解压JLink软件
   - 找到DLL文件:
     - 64位: `JLink_x64.dll`
     - 32位: `JLinkARM.dll`
   - 通常位于: `C:\Program Files\SEGGER\JLink_V9xx\`

3. **替换DLL**
   - 将新的DLL文件复制到RTT Assistant目录
   - 替换旧的 `JLink_x64.dll` 文件
   - 重启RTT Assistant

**注意事项**:
- 确保DLL位数与Python位数匹配
- 64位Python使用 `JLink_x64.dll`
- 32位Python使用 `JLinkARM.dll`

### 方法2: 更新设备列表

升级JLink后,可能支持更多设备型号。

**步骤**:

1. **获取支持的设备列表**
   - 打开JLink安装目录
   - 找到 `JLinkDevices.xml` 文件
   - 或使用JLink Commander查看支持设备

2. **更新devices.txt**
   - 编辑 `devices.txt` 文件
   - 添加新支持的设备型号
   - 每行一个型号,以#开头为注释

3. **重启软件**
   - 重启RTT Assistant
   - 新设备型号将出现在下拉列表中

### 方法3: 完整升级

如果需要完整升级所有组件:

1. **卸载旧版JLink**
   - 控制面板 → 程序和功能 → 卸载

2. **安装新版JLink**
   - 运行安装程序
   - 选择正确的位数(64位/32位)

3. **更新DLL**
   - 从安装目录复制新DLL到RTT Assistant目录

4. **更新设备列表**
   - 更新 `devices.txt` 文件

## 版本兼容性

### JLink版本与设备支持

不同版本的JLink支持不同的设备:

| JLink版本 | 发布时间 | 支持设备数 | 主要新增支持 |
|-----------|----------|------------|--------------|
| V9.38a | 2024 | 5000+ | 新增STM32H5, ESP32-C6等 |
| V9.30 | 2023 | 4500+ | 新增STM32U5, nRF53等 |
| V9.20 | 2022 | 4000+ | 新增STM32G4, EFR32xG22等 |

### 查看当前JLink版本

运行RTT Assistant,在系统日志中可以看到:
```
[INFO] JLink版本: 9.38a
```

或使用诊断工具:
```bash
python diagnose_jlink.py
```

## 常见问题

### Q1: 升级后无法连接设备?

**原因**: DLL位数不匹配

**解决**:
- 检查Python位数: `python -c "import struct; print(struct.calcsize('P')*8)"`
- 使用对应位数的DLL

### Q2: 设备型号不在列表中?

**解决**:
1. 手动输入设备型号
2. 更新 `devices.txt` 文件
3. JLink会验证型号是否支持

### Q3: 升级后出现错误?

**解决**:
1. 检查DLL是否正确复制
2. 运行诊断工具检查
3. 查看系统日志了解详细错误

## 推荐升级策略

### 稳定版策略
- 使用经过验证的稳定版本
- 当前推荐: JLink V9.38a

### 最新版策略
- 定期检查SEGGER官网更新
- 下载最新DLL替换
- 更新设备列表

### 自动化升级(未来功能)
- 计划支持自动检测JLink更新
- 自动下载并替换DLL
- 自动更新设备列表

## 备份建议

升级前建议备份:
- `JLink_x64.dll` - 当前工作的DLL
- `devices.txt` - 自定义的设备列表
- `config.json` - 软件配置

## 技术支持

如遇问题:
1. 查看系统日志
2. 运行诊断工具
3. 访问SEGGER官网文档
4. 检查JLink版本兼容性

---

**提示**: RTT Assistant设计为独立运行,只需DLL文件即可,无需完整安装JLink软件。
