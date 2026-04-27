#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RTT Assistant - RTT调试助手
版本: v1.3.1
作者: CodeArts Agent
"""

import sys
import os
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtGui import QIcon
from rtt_tool.utils.resource_utils import get_resource_path


def exception_hook(exctype, value, traceback):
    """全局异常处理"""
    error_msg = f"{exctype.__name__}: {value}"
    print(f"错误: {error_msg}")
    
    # 写入系统日志文件
    try:
        from datetime import datetime
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        with open('rtt_system.log', 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] [ERROR] {error_msg}\n")
    except:
        pass
    
    # 显示错误对话框
    QMessageBox.critical(None, "错误", f"程序发生错误:\n\n{error_msg}")
    
    # 调用原始异常处理
    sys.__excepthook__(exctype, value, traceback)


def main():
    """主函数"""
    # 设置全局异常处理
    sys.excepthook = exception_hook
    
    app = QApplication(sys.argv)
    
    # 设置应用名称
    app.setApplicationName("RTT Assistant")
    app.setApplicationVersion("1.3.1")
    
    # 设置应用图标
    icon_path = get_resource_path("icon.ico")
    if icon_path and os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    # 创建主控制器
    from rtt_tool.controller.main_controller import MainController
    controller = MainController()
    controller.show()
    
    # 运行应用
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
