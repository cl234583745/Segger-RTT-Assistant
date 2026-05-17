#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2026 chenkaka
# SPDX-License-Identifier: GPL-3.0-or-later

"""
RTT Assistant - RTT调试助手
作者: chenkaka
"""

import sys
import os


def _setup_src_path():
    this_dir = os.path.dirname(os.path.abspath(__file__))
    src_python = os.path.join(os.path.dirname(this_dir), 'python')
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
        from rtt_tool.utils.resource_utils import get_exe_dir
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        log_path = os.path.join(get_exe_dir(), 'rtt_system.log')
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

    from rtt_tool.runtime.runtime_guard import RuntimeGuard
    from rtt_tool.runtime.dependency_checker import DependencyChecker

    deps_ok = RuntimeGuard.setup()
    if not deps_ok:
        report = DependencyChecker.check_all(check_runtime_only=True)
        deps_ok = RuntimeGuard.show_setup_wizard(report)
        if not deps_ok:
            print("依赖未就绪，程序退出")
            sys.exit(1)

    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtGui import QIcon
    from rtt_tool.utils.resource_utils import get_resource_path

    try:
        from rtt_tool.utils.resource_utils import get_exe_dir
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
