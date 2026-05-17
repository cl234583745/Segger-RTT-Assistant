import os
import sys
import subprocess
from typing import Optional, List

from .path_config import (
    RUNTIME_VENV_DIR, RUNTIME_VENV_SITE_PACKAGES, RUNTIME_DLL_DIR, RUNTIME_PACKS_DIR,
    ensure_runtime_dirs, get_app_root,
)
from .dependency_manifest import (
    DependencyType, BackendType, BACKEND_INFO,
    get_pip_install_list, get_all_dependencies, get_backend_size_mb,
)
from .dependency_checker import DependencyChecker, DependencyCheckReport


class DownloadWorker:
    _qthread_cls = None

    @classmethod
    def _get_qthread(cls):
        if cls._qthread_cls is None:
            from PyQt5.QtCore import QThread, pyqtSignal
            cls._qthread_cls = type('DownloadWorkerImpl', (QThread,), {
                'progress': pyqtSignal(str),
                'finished': pyqtSignal(bool, str),
                'run': cls._run_impl,
            })
        return cls._qthread_cls

    @staticmethod
    def _run_impl(self):
        try:
            ensure_runtime_dirs()
            cmd = [
                sys.executable, '-m', 'pip', 'install',
                '--target', self._target_dir,
                '--no-warn-script-location',
            ] + self._packages

            self.progress.emit(f'执行: pip install --target {self._target_dir}')
            self.progress.emit(f'包列表: {" ".join(self._packages)}')

            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding='utf-8', errors='replace',
            )
            for line in process.stdout:
                line = line.strip()
                if line:
                    self.progress.emit(line)

            process.wait()
            if process.returncode == 0:
                self.finished.emit(True, '所有Python依赖下载完成!')
            else:
                self.finished.emit(False, f'下载失败 (返回码: {process.returncode})')
        except Exception as e:
            self.finished.emit(False, f'下载异常: {e}')

    @classmethod
    def create(cls, packages, target_dir):
        impl_cls = cls._get_qthread()
        worker = impl_cls()
        worker._packages = packages
        worker._target_dir = target_dir
        return worker


def show_setup_wizard(report: DependencyCheckReport) -> tuple:
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QProgressBar, QTextEdit, QGroupBox, QCheckBox, QScrollArea,
        QWidget, QMessageBox, QGridLayout,
    )
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QFont

    class SetupWizard(QDialog):
        def __init__(self, report, parent=None):
            super().__init__(parent)
            self._report = report
            self._download_worker = None
            self._deps_ready = False
            self._selected_backends: List[BackendType] = []
            self._backend_checks = {}
            self._init_ui()

        def _init_ui(self):
            self.setWindowTitle('RTT Assistant - 首次启动 - 选择调试器后端')
            self.setMinimumSize(720, 600)
            self.setModal(True)

            layout = QVBoxLayout(self)

            title = QLabel('欢迎使用 RTT Assistant')
            title.setFont(QFont('Microsoft YaHei', 18, QFont.Bold))
            title.setAlignment(Qt.AlignCenter)
            layout.addWidget(title)

            subtitle = QLabel('请选择您使用的调试器类型，将自动下载对应依赖到 runtime 目录')
            subtitle.setAlignment(Qt.AlignCenter)
            subtitle.setWordWrap(True)
            layout.addWidget(subtitle)

            backend_group = QGroupBox('选择调试器后端 (可多选)')
            backend_layout = QGridLayout()

            col = 0
            for bt in BackendType:
                info = BACKEND_INFO[bt]
                size = get_backend_size_mb(bt)
                checked = False

                if bt == BackendType.JLINK:
                    checked = True

                cb = QCheckBox(f'{info["name"]}  (~{size:.0f}MB)')
                cb.setFont(QFont('Microsoft YaHei', 11))
                cb.setChecked(checked)
                cb.setProperty('backend_type', bt)
                self._backend_checks[bt] = cb

                desc_label = QLabel(f'  {info["description"]}')
                desc_label.setWordWrap(True)

                backend_layout.addWidget(cb, 0, col, Qt.AlignTop)
                backend_layout.addWidget(desc_label, 1, col, Qt.AlignTop)
                col += 1

            backend_group.setLayout(backend_layout)
            layout.addWidget(backend_group)

            hint = QLabel('提示: DAP-Link 和 ST-Link 共享 PyOCD 核心 (~22MB)，同时勾选不会重复下载')
            hint.setWordWrap(True)
            hint.setStyleSheet('color: #666; font-size: 11px;')
            layout.addWidget(hint)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll_widget = QWidget()
            scroll_layout = QVBoxLayout(scroll_widget)

            status_group = QGroupBox('当前依赖状态')
            status_layout = QVBoxLayout()
            for item in self._report.items:
                if not item.is_available:
                    tag = '✗'
                    color = 'red'
                else:
                    tag = '✓'
                    color = 'green'
                req = '[必需]' if item.required else '[可选]'
                label = QLabel(f'<span style="color:{color}">{tag}</span> {req} <b>{item.name}</b>: {item.detail}')
                status_layout.addWidget(label)
            status_group.setLayout(status_layout)
            scroll_layout.addWidget(status_group)

            info_label = QLabel(
                f'依赖安装位置:\n'
                f'  Python包: {RUNTIME_VENV_SITE_PACKAGES}\n'
                f'  DLL文件:  {RUNTIME_DLL_DIR}\n'
                f'  Pack文件: {RUNTIME_PACKS_DIR}'
            )
            info_label.setWordWrap(True)
            scroll_layout.addWidget(info_label)

            scroll.setWidget(scroll_widget)
            layout.addWidget(scroll)

            self._log_text = QTextEdit()
            self._log_text.setReadOnly(True)
            self._log_text.setMaximumHeight(120)
            self._log_text.setVisible(False)
            layout.addWidget(self._log_text)

            self._progress_bar = QProgressBar()
            self._progress_bar.setVisible(False)
            layout.addWidget(self._progress_bar)

            btn_layout = QHBoxLayout()

            self._btn_download = QPushButton('下载选中后端的依赖')
            self._btn_download.setMinimumHeight(44)
            self._btn_download.setStyleSheet('QPushButton { background-color: #4CAF50; color: white; font-size: 14px; font-weight: bold; }')
            self._btn_download.clicked.connect(self._on_download)
            btn_layout.addWidget(self._btn_download)

            self._btn_manual = QPushButton('手动配置说明')
            self._btn_manual.clicked.connect(self._on_manual_setup)
            btn_layout.addWidget(self._btn_manual)

            self._btn_refresh = QPushButton('刷新检测')
            self._btn_refresh.clicked.connect(self._on_refresh)
            btn_layout.addWidget(self._btn_refresh)

            self._btn_continue = QPushButton('继续启动')
            self._btn_continue.setMinimumHeight(44)
            self._btn_continue.setEnabled(self._report.all_required_ok)
            self._btn_continue.clicked.connect(self._on_continue)
            btn_layout.addWidget(self._btn_continue)

            layout.addLayout(btn_layout)

        def _get_selected_backends(self) -> List[BackendType]:
            return [bt for bt, cb in self._backend_checks.items() if cb.isChecked()]

        def _on_download(self):
            selected = self._get_selected_backends()
            if not selected:
                QMessageBox.warning(self, '提示', '请至少选择一个调试器后端')
                return

            self._selected_backends = selected
            packages = get_pip_install_list(selected)
            if not packages:
                QMessageBox.information(self, '提示', '没有需要下载的Python包')
                return

            self._log_text.setVisible(True)
            self._log_text.append(f'选中后端: {", ".join(BACKEND_INFO[bt]["name"] for bt in selected)}')
            self._log_text.append(f'将下载 {len(packages)} 个Python包到 runtime/python/ ...')

            self._progress_bar.setVisible(True)
            self._progress_bar.setRange(0, 0)
            self._btn_download.setEnabled(False)
            self._btn_manual.setEnabled(False)

            self._download_worker = DownloadWorker.create(packages, RUNTIME_VENV_SITE_PACKAGES)
            self._download_worker.progress.connect(self._on_download_progress)
            self._download_worker.finished.connect(self._on_download_finished)
            self._download_worker.start()

        def _on_download_progress(self, msg):
            self._log_text.append(msg)

        def _on_download_finished(self, success, msg):
            self._progress_bar.setVisible(False)
            self._btn_download.setEnabled(True)
            self._btn_manual.setEnabled(True)
            self._log_text.append(f'\n>>> {msg}')

            if success:
                self._copy_libusb_dll()
                self._on_refresh()
            else:
                QMessageBox.warning(self, '下载失败', msg)

        def _copy_libusb_dll(self):
            try:
                import usb1
                src = os.path.join(os.path.dirname(usb1.__file__), 'libusb-1.0.dll')
                if os.path.isfile(src):
                    import shutil
                    dst = os.path.join(RUNTIME_DLL_DIR, 'libusb-1.0.dll')
                    shutil.copy2(src, dst)
                    self._log_text.append(f'已复制 libusb-1.0.dll -> {dst}')
            except Exception as e:
                self._log_text.append(f'复制libusb失败(可忽略): {e}')

        def _on_manual_setup(self):
            selected = self._get_selected_backends()
            backend_names = ', '.join(BACKEND_INFO[bt]['name'] for bt in selected) if selected else '(请先勾选)'

            jlink_hint = ''
            if BackendType.JLINK in selected:
                jlink_hint = (
                    '\n\n[J-Link] DLL文件为必须:\n'
                    f'  从SEGGER官网下载并安装JLink软件，将 JLink_x64.dll 复制到:\n'
                    f'  {RUNTIME_DLL_DIR}\\JLink_x64.dll'
                )

            pack_hint = ''
            if BackendType.DAPLINK in selected:
                pack_hint = (
                    '\n\n[DAP-Link] CMSIS Pack文件(可选):\n'
                    f'  将 .pack 文件复制到 {RUNTIME_PACKS_DIR}\\'
                )

            QMessageBox.information(self, '手动配置依赖',
                f'已选后端: {backend_names}\n\n'
                f'Python包安装命令:\n'
                f'  pip install到venv: {RUNTIME_VENV_DIR}\n'
                f'{jlink_hint}{pack_hint}\n\n'
                '配置完成后点击"刷新检测"'
            )

        def _on_refresh(self):
            self._report = DependencyChecker.check_all(
                selected_backends=self._get_selected_backends(),
            )
            if self._report.all_required_ok:
                self._btn_continue.setEnabled(True)
                QMessageBox.information(self, '检测完成', '所有必需依赖已就绪，可以继续启动!')
            else:
                missing = [s.name for s in self._report.missing_required]
                QMessageBox.warning(self, '检测完成', f'仍缺少必需依赖:\n{", ".join(missing)}')

        def _on_continue(self):
            self._deps_ready = True
            self._selected_backends = self._get_selected_backends()
            self.accept()

        @property
        def deps_ready(self):
            return self._deps_ready

        @property
        def selected_backends(self):
            return self._selected_backends

    return SetupWizard
