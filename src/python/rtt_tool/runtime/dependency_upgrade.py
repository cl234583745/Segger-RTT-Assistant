import os
import sys
import subprocess
import importlib
from typing import List, Optional

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
    QTextEdit, QGroupBox, QMessageBox, QAbstractItemView, QWidget,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

from .path_config import (
    RUNTIME_DIR, RUNTIME_VENV_DIR, RUNTIME_VENV_SITE_PACKAGES,
    RUNTIME_VENV_PIP, RUNTIME_VENV_PYTHON,
    RUNTIME_DLL_DIR, RUNTIME_PACKS_DIR,
    RUNTIME_JLINK_DLL_PATH, RUNTIME_LIBUSB_DLL_PATH,
)
from .dependency_manifest import (
    DependencyType, BackendType, BACKEND_INFO,
    get_all_dependencies,
)


def _get_runtime_package_version(name: str) -> str:
    try:
        import importlib.metadata
        try:
            return importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            pass
        orig_path = sys.path.copy()
        if RUNTIME_VENV_SITE_PACKAGES not in sys.path:
            sys.path.insert(0, RUNTIME_VENV_SITE_PACKAGES)
        try:
            dist = importlib.metadata.distribution(name)
            return dist.metadata['Version'] or '未知'
        except Exception:
            pass
        try:
            mod = importlib.import_module(name)
            ver = getattr(mod, '__version__', None)
            if ver is None and name == 'PyQt5':
                from PyQt5.QtCore import PYQT_VERSION_STR
                ver = PYQT_VERSION_STR
            return ver or '未知'
        finally:
            sys.path[:] = orig_path
    except Exception as e:
        return f'获取失败({e})'


def _open_folder(path: str):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    if sys.platform == 'win32':
        os.startfile(path)
    elif sys.platform == 'darwin':
        subprocess.Popen(['open', path])
    else:
        subprocess.Popen(['xdg-open', path])


def show_dependency_upgrade_dialog(parent=None):

    class PipUpgradeWorker(QThread):
        progress = pyqtSignal(str)
        finished = pyqtSignal(bool, str)

        def __init__(self, package_spec):
            super().__init__()
            self._package_spec = package_spec

        def run(self):
            try:
                pip_exe = RUNTIME_VENV_PIP
                if not os.path.isfile(pip_exe):
                    pip_exe = os.path.join(RUNTIME_VENV_DIR, 'Scripts', 'pip.exe')
                if not os.path.isfile(pip_exe):
                    self.finished.emit(False, '未找到venv中的pip，请检查runtime/venv/')
                    return

                cmd = [pip_exe, 'install', '--upgrade', self._package_spec]
                self.progress.emit(f'执行: {self._package_spec} 升级中...')

                process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding='utf-8', errors='replace',
                )
                for line in process.stdout:
                    line = line.strip()
                    if line and 'notice' not in line.lower():
                        self.progress.emit(line)
                process.wait()
                if process.returncode == 0:
                    self.finished.emit(True, f'{self._package_spec} 升级完成')
                else:
                    self.finished.emit(False, f'升级失败 (返回码: {process.returncode})')
            except Exception as e:
                self.finished.emit(False, f'升级异常: {e}')

    class DependencyUpgradeDialog(QDialog):
        def __init__(self, parent=None):
            super().__init__(parent)
            self._upgrade_worker = None
            self._init_ui()

        def showEvent(self, event):
            super().showEvent(event)
            try:
                from PyQt5.QtWidgets import QApplication as QApp
                app = QApp.instance()
                if app is not None:
                    dark = app.property('_dark_theme')
                    if dark is None or dark:
                        from rtt_tool.ui.main_window import set_dark_title_bar
                        set_dark_title_bar(self, True)
            except Exception:
                pass

        def _init_ui(self):
            self.setWindowTitle('依赖管理')
            self.setMinimumSize(900, 550)
            self.setModal(True)
            self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)

            layout = QVBoxLayout(self)

            title = QLabel('运行时依赖管理')
            title.setFont(QFont('Microsoft YaHei', 14, QFont.Bold))
            layout.addWidget(title)

            hint = QLabel(f'虚拟环境: {RUNTIME_VENV_DIR}')
            hint.setStyleSheet('color: #666;')
            layout.addWidget(hint)

            self._table = QTableWidget()
            self._table.setColumnCount(5)
            self._table.setHorizontalHeaderLabels(['依赖名称', '类型', '当前版本', '位置', '操作'])
            self._table.horizontalHeader().setStretchLastSection(True)
            self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
            self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
            self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
            self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
            self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
            self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self._table.verticalHeader().setVisible(False)

            self._populate_table()
            layout.addWidget(self._table)

            packs_group = QGroupBox('CMSIS Pack 文件')
            packs_layout = QHBoxLayout()
            self._packs_label = QLabel()
            packs_layout.addWidget(self._packs_label)
            btn_open_packs = QPushButton('打开文件夹')
            btn_open_packs.clicked.connect(lambda: _open_folder(RUNTIME_PACKS_DIR))
            packs_layout.addWidget(btn_open_packs)
            packs_group.setLayout(packs_layout)
            self._update_packs_info()
            layout.addWidget(packs_group)

            self._log_text = QTextEdit()
            self._log_text.setReadOnly(True)
            self._log_text.setMaximumHeight(80)
            self._log_text.setVisible(False)
            layout.addWidget(self._log_text)

            self._progress_bar = QProgressBar()
            self._progress_bar.setVisible(False)
            layout.addWidget(self._progress_bar)

            btn_close = QPushButton('关闭')
            btn_close.clicked.connect(self.close)
            layout.addWidget(btn_close)

        def _populate_table(self):
            deps = get_all_dependencies(list(BackendType))
            python_deps = [d for d in deps if d.dep_type in (DependencyType.SYSTEM_PACKAGE, DependencyType.PYTHON_PACKAGE)]
            dll_deps = [d for d in deps if d.dep_type == DependencyType.DLL]

            rows = []

            venv_python = RUNTIME_VENV_PYTHON
            venv_python_ver = f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}'

            rows.append({
                'name': 'Python',
                'type': '解释器(exe内嵌)',
                'version': venv_python_ver,
                'location': '(打包进exe)',
                'pip_spec': None,
                'can_upgrade': False,
            })

            for d in python_deps:
                ver = _get_runtime_package_version(d.name)
                pip_spec = d.download_url[4:] if d.download_url.startswith('pip:') else d.name
                rows.append({
                    'name': d.name,
                    'type': 'Python包',
                    'version': ver,
                    'location': RUNTIME_VENV_SITE_PACKAGES,
                    'pip_spec': pip_spec,
                    'can_upgrade': bool(pip_spec),
                })

            for d in dll_deps:
                fname = d.filename or d.name
                fpath = os.path.join(RUNTIME_DLL_DIR, fname)
                exists = os.path.isfile(fpath)
                size_str = f'{os.path.getsize(fpath)/1024/1024:.1f}MB' if exists else '未安装'
                rows.append({
                    'name': d.name,
                    'type': 'DLL',
                    'version': size_str,
                    'location': RUNTIME_DLL_DIR,
                    'pip_spec': None,
                    'can_upgrade': False,
                })

            self._table.setRowCount(len(rows))
            self._row_data = rows

            for i, row in enumerate(rows):
                self._table.setItem(i, 0, QTableWidgetItem(row['name']))
                self._table.setItem(i, 1, QTableWidgetItem(row['type']))
                self._table.setItem(i, 2, QTableWidgetItem(row['version']))
                self._table.setItem(i, 3, QTableWidgetItem(row['location']))

                btn_widget = QWidget()
                btn_layout = QHBoxLayout(btn_widget)
                btn_layout.setContentsMargins(2, 2, 2, 2)

                btn_open = QPushButton('打开')
                btn_open.setFixedWidth(50)
                btn_open.clicked.connect(lambda checked, loc=row['location']: _open_folder(loc))
                btn_layout.addWidget(btn_open)

                if row['can_upgrade']:
                    btn_upgrade = QPushButton('升级')
                    btn_upgrade.setFixedWidth(50)
                    btn_upgrade.setStyleSheet('QPushButton { background-color: #4CAF50; color: white; }')
                    btn_upgrade.clicked.connect(
                        lambda checked, spec=row['pip_spec'], idx=i: self._on_upgrade(spec, idx)
                    )
                    btn_layout.addWidget(btn_upgrade)

                self._table.setCellWidget(i, 4, btn_widget)

        def _update_packs_info(self):
            if os.path.isdir(RUNTIME_PACKS_DIR):
                packs = [f for f in os.listdir(RUNTIME_PACKS_DIR) if f.endswith('.pack')]
                self._packs_label.setText(f'已安装 {len(packs)} 个Pack文件')
            else:
                self._packs_label.setText('未安装Pack文件')

        def _on_upgrade(self, pip_spec: str, row_idx: int):
            self._log_text.setVisible(True)
            self._progress_bar.setVisible(True)
            self._progress_bar.setRange(0, 0)
            self._log_text.append(f'正在升级 {pip_spec} ...')

            self._upgrade_worker = PipUpgradeWorker(pip_spec)
            self._upgrade_worker.progress.connect(self._on_upgrade_progress)
            self._upgrade_worker.finished.connect(self._on_upgrade_finished)
            self._upgrade_worker.start()

        def _on_upgrade_progress(self, msg):
            self._log_text.append(msg)

        def _on_upgrade_finished(self, success, msg):
            self._progress_bar.setVisible(False)
            self._log_text.append(f'>>> {msg}')
            if success:
                self._populate_table()
                QMessageBox.information(self, '升级完成', msg)
            else:
                QMessageBox.warning(self, '升级失败', msg)

    return DependencyUpgradeDialog(parent)
