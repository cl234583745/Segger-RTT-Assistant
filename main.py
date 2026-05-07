#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2026 chenkaka
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
RTT Assistant - RTT调试助手
作者: chenkaka
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
    
    try:
        from datetime import datetime
        from rtt_tool.utils.resource_utils import get_exe_dir
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        log_path = os.path.join(get_exe_dir(), 'rtt_system.log')
        with open(log_path, 'a', encoding='utf-8') as f:
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
    from rtt_tool import __version__
    app.setApplicationVersion(__version__)
    
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
