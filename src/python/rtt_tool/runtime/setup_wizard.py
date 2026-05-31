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
from ..i18n import _ as i18n, language_changed as i18n_language_changed


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

            self.progress.emit(i18n("setup.exec_pip_install").format(self._target_dir))
            self.progress.emit(i18n("setup.package_list").format(" ".join(self._packages)))

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
                self.finished.emit(True, i18n("setup.log_download_complete"))
            else:
                self.finished.emit(False, i18n("setup.log_download_failed").format(process.returncode))
        except Exception as e:
            self.finished.emit(False, i18n("setup.log_download_error").format(e))

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
            _sig = i18n_language_changed()
            if _sig:
                _sig.connect(self._on_language_changed)

        def _init_ui(self):
            self.setWindowTitle(i18n("setup.window_title"))
            self.setMinimumSize(720, 600)
            self.setModal(True)

            layout = QVBoxLayout(self)

            title = QLabel(i18n("setup.welcome"))
            title.setFont(QFont('Microsoft YaHei', 18, QFont.Bold))
            title.setAlignment(Qt.AlignCenter)
            layout.addWidget(title)

            subtitle = QLabel(i18n("setup.subtitle"))
            subtitle.setAlignment(Qt.AlignCenter)
            subtitle.setWordWrap(True)
            layout.addWidget(subtitle)

            backend_group = QGroupBox(i18n("setup.select_backend"))
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

            hint = QLabel(i18n("setup.dap_stlink_hint"))
            hint.setWordWrap(True)
            hint.setStyleSheet('color: #666; font-size: 11px;')
            layout.addWidget(hint)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll_widget = QWidget()
            scroll_layout = QVBoxLayout(scroll_widget)

            status_group = QGroupBox(i18n("setup.dep_status"))
            status_layout = QVBoxLayout()
            for item in self._report.items:
                if not item.is_available:
                    tag = '✗'
                    color = 'red'
                else:
                    tag = '✓'
                    color = 'green'
                req = i18n("setup.required") if item.required else i18n("setup.optional")
                label = QLabel(f'<span style="color:{color}">{tag}</span> {req} <b>{item.name}</b>: {item.detail}')
                status_layout.addWidget(label)
            status_group.setLayout(status_layout)
            scroll_layout.addWidget(status_group)

            info_label = QLabel(
                f'{i18n("setup.dep_install_location")}\n'
                f'  {i18n("setup.python_packages")} {RUNTIME_VENV_SITE_PACKAGES}\n'
                f'  {i18n("setup.dll_files")}  {RUNTIME_DLL_DIR}\n'
                f'  {i18n("setup.pack_files")} {RUNTIME_PACKS_DIR}'
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

            self._btn_download = QPushButton(i18n("setup.btn_download"))
            self._btn_download.setMinimumHeight(44)
            self._btn_download.setStyleSheet('QPushButton { background-color: #4CAF50; color: white; font-size: 14px; font-weight: bold; }')
            self._btn_download.clicked.connect(self._on_download)
            btn_layout.addWidget(self._btn_download)

            self._btn_manual = QPushButton(i18n("setup.btn_manual"))
            self._btn_manual.clicked.connect(self._on_manual_setup)
            btn_layout.addWidget(self._btn_manual)

            self._btn_refresh = QPushButton(i18n("setup.btn_refresh"))
            self._btn_refresh.clicked.connect(self._on_refresh)
            btn_layout.addWidget(self._btn_refresh)

            self._btn_continue = QPushButton(i18n("setup.btn_continue"))
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
                QMessageBox.warning(self, i18n("dialog.hint_title"), i18n("setup.warn_select_backend"))
                return

            self._selected_backends = selected
            packages = get_pip_install_list(selected)
            if not packages:
                QMessageBox.information(self, i18n("dialog.hint_title"), i18n("setup.info_no_packages"))
                return

            self._log_text.setVisible(True)
            self._log_text.append(i18n("setup.log_selected_backends").format(", ".join(BACKEND_INFO[bt]["name"] for bt in selected)))
            self._log_text.append(i18n("setup.log_will_download").format(len(packages)))

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
                QMessageBox.warning(self, i18n("dialog.download_failed"), msg)

        def _copy_libusb_dll(self):
            try:
                import usb1
                src = os.path.join(os.path.dirname(usb1.__file__), 'libusb-1.0.dll')
                if os.path.isfile(src):
                    import shutil
                    dst = os.path.join(RUNTIME_DLL_DIR, 'libusb-1.0.dll')
                    shutil.copy2(src, dst)
                    self._log_text.append(i18n("setup.log_copied_dll").format(dst))
            except Exception as e:
                self._log_text.append(i18n("setup.log_copy_dll_failed").format(e))

        def _on_manual_setup(self):
            selected = self._get_selected_backends()
            backend_names = ', '.join(BACKEND_INFO[bt]['name'] for bt in selected) if selected else i18n("setup.no_backend_selected")

            jlink_hint = ''
            if BackendType.JLINK in selected:
                jlink_hint = (
                    f'\n\n{i18n("setup.manual_jlink_dll")}\n'
                    f'  {i18n("setup.manual_jlink_dll_hint")}\n'
                    f'  {RUNTIME_DLL_DIR}\\JLink_x64.dll'
                )

            pack_hint = ''
            if BackendType.DAPLINK in selected:
                pack_hint = (
                    f'\n\n{i18n("setup.manual_dap_pack")}\n'
                    f'  {i18n("setup.manual_dap_pack_hint").format(RUNTIME_PACKS_DIR + "\\")}'
                )

            QMessageBox.information(self, i18n("setup.manual_config_title"),
                f'{i18n("setup.manual_selected_backends").format(backend_names)}\n\n'
                f'{i18n("setup.manual_pip_command")}\n'
                f'  {i18n("setup.manual_pip_to_venv").format(RUNTIME_VENV_DIR)}\n'
                f'{jlink_hint}{pack_hint}\n\n'
                f'{i18n("setup.manual_after_config")}'
            )

        def _on_refresh(self):
            self._report = DependencyChecker.check_all(
                selected_backends=self._get_selected_backends(),
            )
            if self._report.all_required_ok:
                self._btn_continue.setEnabled(True)
                QMessageBox.information(self, i18n("setup.detect_complete"), i18n("setup.all_deps_ready"))
            else:
                missing = [s.name for s in self._report.missing_required]
                QMessageBox.warning(self, i18n("setup.detect_complete"), i18n("setup.still_missing").format(", ".join(missing)))

        def _on_language_changed(self, lang):
            self.setWindowTitle(i18n("setup.window_title"))
            if hasattr(self, '_btn_download'):
                self._btn_download.setText(i18n("setup.btn_download"))
            if hasattr(self, '_btn_manual'):
                self._btn_manual.setText(i18n("setup.btn_manual"))
            if hasattr(self, '_btn_refresh'):
                self._btn_refresh.setText(i18n("setup.btn_refresh"))
            if hasattr(self, '_btn_continue'):
                self._btn_continue.setText(i18n("setup.btn_continue"))

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
