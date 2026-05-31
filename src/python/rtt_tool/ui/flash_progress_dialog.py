from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QPlainTextEdit,
                             QHBoxLayout, QPushButton, QLabel)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QTextCursor
from datetime import datetime
from ..i18n import _ as i18n, language_changed


class FlashProgressDialog(QDialog):

    def __init__(self, firmware_name: str, debugger_type: str, chip_model: str, parent=None):
        super().__init__(parent)
        self._firmware_name = firmware_name
        self._debugger_type = debugger_type
        self._chip_model = chip_model
        title = f"{i18n('btn.flash')}: {firmware_name} [{debugger_type} / {chip_model}]"
        self.setWindowTitle(title)
        self.setFixedSize(600, 380)
        self.setModal(False)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinimizeButtonHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        self._info_label = QLabel(f"{i18n('btn.flash')}: {firmware_name}")
        self._info_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self._info_label)

        self._log_text = QPlainTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setStyleSheet("""
            QPlainTextEdit {
                font-family: 'Courier New', Consolas, monospace;
                font-size: 13px;
                color: #e0e0e0;
                background-color: #1e1e1e;
                padding: 8px;
            }
        """)
        layout.addWidget(self._log_text)

        self._result_label = QLabel()
        self._result_label.setAlignment(Qt.AlignCenter)
        self._result_label.setFixedHeight(36)
        self._result_label.hide()
        layout.addWidget(self._result_label)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self._close_btn = QPushButton(i18n("btn.close") if i18n("btn.close") else "关闭")
        self._close_btn.clicked.connect(self.close)
        btn_layout.addWidget(self._close_btn)
        layout.addLayout(btn_layout)

        sig = language_changed()
        if sig:
            sig.connect(self._on_language_changed)

    def _on_language_changed(self, lang):
        self.setWindowTitle(f"{i18n('btn.flash')}: {self._firmware_name} [{self._debugger_type} / {self._chip_model}]")
        self._info_label.setText(f"{i18n('btn.flash')}: {self._firmware_name}")
        self._close_btn.setText(i18n("btn.close") if i18n("btn.close") else "关闭")

    def append_log(self, text: str):
        timestamp = datetime.now().strftime('%H:%M:%S')
        self._log_text.appendPlainText(f"[{timestamp}] {text}")
        scrollbar = self._log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def set_result(self, success: bool):
        if success:
            self._result_label.setText(f"✓ {i18n('status.flash_success')}")
            self._result_label.setStyleSheet("""
                QLabel {
                    background-color: #2e7d32;
                    color: #ffffff;
                    font-size: 16px;
                    font-weight: bold;
                    border-radius: 4px;
                    padding: 4px;
                }
            """)
            self._result_label.show()
            self.append_log(f"\n✓ {i18n('status.flash_success')}")
            self.start_auto_close_timer(2000)
        else:
            self._result_label.setText(f"✗ {i18n('status.flash_failed')}")
            self._result_label.setStyleSheet("""
                QLabel {
                    background-color: #c62828;
                    color: #ffffff;
                    font-size: 16px;
                    font-weight: bold;
                    border-radius: 4px;
                    padding: 4px;
                }
            """)
            self._result_label.show()
            self.append_log(f"\n✗ {i18n('status.flash_failed')}")

    def start_auto_close_timer(self, delay_ms: int = 2000):
        QTimer.singleShot(delay_ms, self.close)
