#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2026 chenkaka
# SPDX-License-Identifier: GPL-3.0-or-later

"""
RTT Assistant - RTT调试助手 (重构版)
源码在 src/ 目录，依赖在 runtime/ 目录
"""

import sys
import os


def _setup_src_path():
    this_dir = os.path.dirname(os.path.abspath(__file__))
    src_python = os.path.join(this_dir, 'src', 'python')
    if os.path.isdir(src_python):
        abs_src = os.path.abspath(src_python)
        if abs_src not in sys.path:
            sys.path.insert(0, abs_src)


_setup_src_path()


def exception_hook(exctype, value, traceback):
    error_msg = f"{exctype.__name__}: {value}"

    if 'pyocd' in str(traceback) and 'svd' in error_msg.lower():
        return
    if 'load-svd' in error_msg or 'Invalid coresight component' in error_msg:
        return
    if 'genuine ST Device' in error_msg:
        return
    if 'coresight' in error_msg.lower() and 'fault' in error_msg.lower():
        return

    print(f"错误: {error_msg}")

    try:
        from datetime import datetime
        from rtt_tool.runtime.path_config import RUNTIME_LOG_DIR
        import os
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        os.makedirs(RUNTIME_LOG_DIR, exist_ok=True)
        log_path = os.path.join(RUNTIME_LOG_DIR, 'rtt_system.log')
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] [ERROR] {error_msg}\n")
    except:
        pass

    try:
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.critical(None, "错误", f"程序发生错误:\n\n{error_msg}")
    except:
        pass

    sys.__excepthook__(exctype, value, traceback)


def main():
    sys.excepthook = exception_hook

    try:
        import logging
        from rtt_tool.runtime.path_config import RUNTIME_LOG_DIR
        import os
        os.makedirs(RUNTIME_LOG_DIR, exist_ok=True)
        log_path = os.path.join(RUNTIME_LOG_DIR, 'rtt_debug.log')
        logging.basicConfig(
            level=logging.DEBUG,
            format='[%(asctime)s.%(msecs)03d] [%(levelname)s] %(name)s: %(message)s',
            datefmt='%H:%M:%S',
            filename=log_path,
            filemode='a'
        )
    except Exception:
        pass

    from rtt_tool.runtime.runtime_guard import RuntimeGuard
    RuntimeGuard.setup()

    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtGui import QIcon
    from rtt_tool.utils.resource_utils import get_resource_path, get_exe_dir

    try:
        exe_dir = get_exe_dir()
        os.chdir(exe_dir)
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setApplicationName("RTT Assistant")
    from rtt_tool import __version__
    app.setApplicationVersion(__version__)

    icon_path = get_resource_path("resources/icon.ico")
    if icon_path and os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    from rtt_tool.controller.main_controller import MainController
    controller = MainController()
    controller.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
