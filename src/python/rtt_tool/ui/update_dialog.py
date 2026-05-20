from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QApplication, QWidget,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor
from ..utils.update_checker import (
    check_all_sources, parse_version, RELEASE_PAGE_URLS,
)
from .. import __version__


class _CheckThread(QThread):
    finished = pyqtSignal(list)

    def run(self):
        results = check_all_sources()
        self.finished.emit(results)


class UpdateDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("检查更新")
        self.resize(580, 420)
        self._results = []
        self._current_version = __version__
        self._setup_ui()
        self._start_check()

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

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel(f"<h3>检查更新</h3>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self._ver_label = QLabel(
            f'<p style="color:#888;">当前版本: v{self._current_version}</p>')
        self._ver_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._ver_label)

        self._status_label = QLabel("正在检查更新…")
        self._status_label.setAlignment(Qt.AlignCenter)
        self._status_label.setStyleSheet("color: #00AAFF;")
        layout.addWidget(self._status_label)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["来源", "最新版本", "状态", "操作"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionMode(QTableWidget.NoSelection)
        self._table.setVisible(False)
        layout.addWidget(self._table)

        btn_layout = QHBoxLayout()
        self._retry_btn = QPushButton("重新检查")
        self._retry_btn.clicked.connect(self._start_check)
        self._retry_btn.setVisible(False)
        btn_layout.addStretch()
        btn_layout.addWidget(self._retry_btn)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _start_check(self):
        self._status_label.setText("正在检查更新…")
        self._status_label.setStyleSheet("color: #00AAFF;")
        self._table.setVisible(False)
        self._retry_btn.setVisible(False)
        self._thread = _CheckThread()
        self._thread.finished.connect(self._on_results)
        self._thread.start()

    def _on_results(self, results):
        self._results = results
        self._status_label.setVisible(False)
        self._table.setVisible(True)
        self._retry_btn.setVisible(True)

        if not results:
            self._table.setRowCount(1)
            self._table.setItem(0, 0, QTableWidgetItem("—"))
            self._table.setItem(0, 1, QTableWidgetItem("—"))
            self._table.setItem(0, 2, QTableWidgetItem("检查失败"))
            self._table.setItem(0, 3, QTableWidgetItem(""))
            msg = QTableWidgetItem("请检查网络连接后重试")
            msg.setForeground(QColor("#888"))
            self._table.setItem(0, 3, msg)
            return

        current = parse_version(self._current_version)
        has_newer = False

        self._table.setRowCount(len(results))
        for row, r in enumerate(results):
            src_item = QTableWidgetItem(r["source"])
            src_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, 0, src_item)

            ver_item = QTableWidgetItem(f'v{r["version"]}')
            ver_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, 1, ver_item)

            remote = parse_version(r["version"])
            row_newer = bool(remote and current and remote > current)
            if row_newer:
                status = QTableWidgetItem("有新版本 ✓")
                status.setForeground(QColor("#00AA00"))
                has_newer = True
            elif remote and current and remote == current:
                status = QTableWidgetItem("已是最新")
                status.setForeground(QColor("#888"))
            else:
                status = QTableWidgetItem("已是最新")
                status.setForeground(QColor("#888"))
            status.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, 2, status)

            self._table.setCellWidget(row, 3, self._make_action_widget(r, row_newer))

        if has_newer:
            self._ver_label.setText(
                f'<p style="color:#00AA00; font-weight:bold;">'
                f'发现新版本！当前: v{self._current_version}</p>')
        else:
            self._ver_label.setText(
                f'<p style="color:#888;">当前版本: v{self._current_version}（已是最新）</p>')

    def _make_action_widget(self, r, has_newer):
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        if has_newer:
            for f in r.get("files", []):
                btn = QPushButton("复制链接")
                btn.setToolTip(f"{r['source']}: {f['name']}\n点击复制下载链接")
                url = f["url"]
                btn.clicked.connect(lambda checked, u=url, src=r["source"]: self._copy_link(u, src))
                layout.addWidget(btn)
                break

        page_btn = QPushButton("打开页面")
        source_lower = r["source"].lower()
        if source_lower == "github":
            page_btn.setToolTip("点击 Assets 选择文件，使用迅雷下载")
        elif source_lower == "gitee":
            page_btn.setToolTip("点击 下载 选择文件下载")
        page_url = RELEASE_PAGE_URLS.get(
            r["source"].lower(),
            r.get("url", ""))
        page_btn.clicked.connect(lambda checked, u=page_url: self._open_page(u))
        layout.addWidget(page_btn)
        layout.addStretch()
        return w

    def _copy_link(self, url, source):
        QApplication.clipboard().setText(url)
        hint = ""
        if source in ("github", "GitHub"):
            hint = "（推荐使用迅雷下载）"
        QMessageBox.information(self, "链接已复制",
                                f"下载链接已复制到剪贴板{hint}\n\n{url}")

    def _open_page(self, url):
        import webbrowser
        webbrowser.open(url)
