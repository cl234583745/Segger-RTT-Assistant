from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QToolBar, QTableWidget,
    QTableWidgetItem, QHeaderView, QDialog, QFormLayout,
    QLineEdit, QComboBox, QDialogButtonBox, QLabel, QPushButton
)
from PyQt5.QtCore import Qt, pyqtSignal
from ..i18n import _ as i18n
from datetime import datetime


class VariableMonitorWidget(QWidget):
    """变量监视 UI 组件，显示监视变量的实时值。"""

    variable_add_requested = pyqtSignal(str, int, str)
    variable_remove_requested = pyqtSignal(str)

    VAR_TYPES = ['uint8', 'int8', 'uint16', 'int16', 'uint32', 'int32', 'float']

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        toolbar = QToolBar()
        toolbar.setMovable(False)

        add_action = QPushButton(i18n("btn.add_variable"))
        add_action.clicked.connect(self._on_add_variable)
        toolbar.addWidget(add_action)

        remove_action = QPushButton(i18n("btn.remove_variable"))
        remove_action.clicked.connect(self._on_remove_variable)
        toolbar.addWidget(remove_action)

        layout.addWidget(toolbar)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels([i18n("header.var_name"), i18n("header.var_address"), i18n("header.var_type"), i18n("header.var_value"), i18n("header.var_time")])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)

        layout.addWidget(self._table)

    def _on_add_variable(self):
        dialog = AddVariableDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            name = dialog.name_text.text()
            addr_str = dialog.address_text.text()
            var_type = dialog.type_combo.currentText()
            try:
                address = int(addr_str, 16)
                self.add_variable_row(name, address, var_type)
                self.variable_add_requested.emit(name, address, var_type)
            except ValueError:
                pass

    def _on_remove_variable(self):
        row = self._table.currentRow()
        if row >= 0:
            name = self._table.item(row, 0).text()
            self._table.removeRow(row)
            self.variable_remove_requested.emit(name)

    def add_variable_row(self, name: str, address: int, var_type: str):
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setItem(row, 0, QTableWidgetItem(name))
        self._table.setItem(row, 1, QTableWidgetItem(f"0x{address:08X}"))
        self._table.setItem(row, 2, QTableWidgetItem(var_type))
        self._table.setItem(row, 3, QTableWidgetItem("--"))
        self._table.setItem(row, 4, QTableWidgetItem("--"))

    def remove_variable_row(self, name: str):
        for row in range(self._table.rowCount()):
            if self._table.item(row, 0).text() == name:
                self._table.removeRow(row)
                return

    def update_variable(self, name: str, value):
        for row in range(self._table.rowCount()):
            if self._table.item(row, 0).text() == name:
                if isinstance(value, float):
                    self._table.item(row, 3).setText(f"{value:.4f}")
                else:
                    self._table.item(row, 3).setText(str(value))
                self._table.item(row, 4).setText(
                    datetime.now().strftime('%H:%M:%S.%f')[:-3]
                )
                return

    def set_variable_error(self, name: str, error_msg: str):
        for row in range(self._table.rowCount()):
            if self._table.item(row, 0).text() == name:
                self._table.item(row, 3).setText(f"Error: {error_msg}")
                return


class AddVariableDialog(QDialog):
    """添加监视变量对话框。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加监视变量")
        self.setWindowTitle(i18n("dialog.add_monitor_var"))

        self.name_text = QLineEdit()
        layout.addRow(i18n("label.name"), self.name_text)

        self.address_text = QLineEdit()
        self.address_text.setPlaceholderText(i18n("placeholder.var_address"))
        layout.addRow(i18n("label.address"), self.address_text)

        self.type_combo = QComboBox()
        self.type_combo.addItems(VariableMonitorWidget.VAR_TYPES)
        layout.addRow(i18n("label.type"), self.type_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
