from PyQt5.QtWidgets import (QGroupBox, QListWidget, QListWidgetItem, QHBoxLayout,
                             QVBoxLayout, QPushButton, QFileDialog)
from PyQt5.QtCore import pyqtSignal, Qt
from ..i18n import _ as i18n, language_changed


class FirmwarePathPanel(QGroupBox):
    firmware_path_added = pyqtSignal(str)
    firmware_path_removed = pyqtSignal(int)
    firmware_path_replaced = pyqtSignal(int, str)
    active_path_changed = pyqtSignal(str)
    firmware_paths_persist = pyqtSignal(list, int)

    def __init__(self, parent=None):
        super().__init__(i18n("group.firmware_file"), parent)
        self._init_ui()
        sig = language_changed()
        if sig:
            sig.connect(self._on_language_changed)

    def _on_language_changed(self, lang):
        self.setTitle(i18n("group.firmware_file"))
        self._open_btn.setText(i18n("btn.open_firmware"))
        self._replace_btn.setText(i18n("btn.replace_firmware"))
        self._delete_btn.setText(i18n("btn.delete_firmware"))

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        self._path_list = QListWidget()
        self._path_list.setMinimumHeight(48)
        self._path_list.currentRowChanged.connect(self._on_row_changed)
        self._path_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self._path_list)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)

        self._open_btn = QPushButton(i18n("btn.open_firmware"))
        self._open_btn.clicked.connect(self._on_open_clicked)

        self._replace_btn = QPushButton(i18n("btn.replace_firmware"))
        self._replace_btn.setEnabled(False)
        self._replace_btn.clicked.connect(self._on_replace_clicked)

        self._delete_btn = QPushButton(i18n("btn.delete_firmware"))
        self._delete_btn.setEnabled(False)
        self._delete_btn.clicked.connect(self._on_delete_clicked)

        btn_layout.addWidget(self._open_btn)
        btn_layout.addWidget(self._replace_btn)
        btn_layout.addWidget(self._delete_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _get_file_filter(self) -> str:
        return (f"{i18n('group.firmware_file')} (*.hex *.bin *.elf *.srec);;"
                f"HEX (*.hex);;BIN (*.bin);;ELF (*.elf);;SREC (*.srec);;"
                f"{i18n('btn.all_files') if i18n('btn.all_files') else 'All Files'} (*)")

    def _on_open_clicked(self):
        path, _ = QFileDialog.getOpenFileName(self, i18n("btn.open_firmware"), '', self._get_file_filter())
        if path:
            self.add_path(path)

    def _on_replace_clicked(self):
        row = self._path_list.currentRow()
        if row < 0:
            return
        path, _ = QFileDialog.getOpenFileName(self, i18n("btn.replace_firmware"), '', self._get_file_filter())
        if path:
            self._path_list.item(row).setText(path)
            self._path_list.item(row).setToolTip(path)
            self.firmware_path_replaced.emit(row, path)
            self._emit_persist()

    def _on_delete_clicked(self):
        row = self._path_list.currentRow()
        if row < 0:
            return
        self._path_list.takeItem(row)
        self.firmware_path_removed.emit(row)
        self._emit_persist()
        if self._path_list.count() > 0:
            new_row = min(row, self._path_list.count() - 1)
            self._path_list.setCurrentRow(new_row)
        else:
            self.active_path_changed.emit('')
            self._replace_btn.setEnabled(False)
            self._delete_btn.setEnabled(False)

    def _on_row_changed(self, row):
        has_selection = row >= 0
        self._replace_btn.setEnabled(has_selection)
        self._delete_btn.setEnabled(has_selection)
        if has_selection:
            path = self._path_list.item(row).text()
            self.active_path_changed.emit(path)
            self._emit_persist()
        else:
            self.active_path_changed.emit('')

    def _on_item_double_clicked(self, item):
        pass

    def add_path(self, path: str):
        item = QListWidgetItem(path)
        item.setToolTip(path)
        self._path_list.addItem(item)
        self._path_list.setCurrentRow(self._path_list.count() - 1)
        self.firmware_path_added.emit(path)
        self._emit_persist()

    def set_firmware_paths(self, paths: list, active_index: int):
        self._path_list.blockSignals(True)
        self._path_list.clear()
        for p in paths:
            item = QListWidgetItem(p)
            item.setToolTip(p)
            self._path_list.addItem(item)
        if 0 <= active_index < len(paths):
            self._path_list.setCurrentRow(active_index)
        self._path_list.blockSignals(False)
        has_selection = self._path_list.currentRow() >= 0
        self._replace_btn.setEnabled(has_selection)
        self._delete_btn.setEnabled(has_selection)
        if has_selection:
            self.active_path_changed.emit(self._path_list.currentItem().text())

    def get_active_path(self) -> str:
        row = self._path_list.currentRow()
        if row >= 0:
            return self._path_list.item(row).text()
        return ''

    def get_all_paths(self) -> list:
        return [self._path_list.item(i).text() for i in range(self._path_list.count())]

    def get_active_index(self) -> int:
        return self._path_list.currentRow()

    def _emit_persist(self):
        paths = self.get_all_paths()
        idx = self.get_active_index()
        self.firmware_paths_persist.emit(paths, idx)