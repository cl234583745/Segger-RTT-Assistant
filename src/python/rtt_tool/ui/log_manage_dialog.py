#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QHeaderView, QMessageBox)
from PyQt5.QtCore import Qt

from ..i18n import _ as i18n, language_changed as i18n_language_changed


class LogManageDialog(QDialog):
    def __init__(self, diag_log_registry, parent=None):
        super().__init__(parent)
        self._registry = diag_log_registry
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle(i18n("dialog.diag_log_manage"))
        self.setFixedSize(520, 280)

        layout = QVBoxLayout(self)

        self._table = QTableWidget(0, 4, self)
        self._table.setHorizontalHeaderLabels([i18n("header.log_name"), i18n("header.file_size"), i18n("header.current_level"), i18n("header.clear")])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._table.setSelectionMode(QTableWidget.NoSelection)
        layout.addWidget(self._table)

        btn_layout = QHBoxLayout()
        self._refresh_btn = QPushButton(i18n("btn.refresh"))
        self._refresh_btn.clicked.connect(self._on_refresh_clicked)
        self._clear_btn = QPushButton(i18n("btn.confirm_clear"))
        self._clear_btn.clicked.connect(self._on_clear_clicked)
        self._close_btn = QPushButton(i18n("btn.close"))
        self._close_btn.clicked.connect(self.close)
        btn_layout.addStretch()
        btn_layout.addWidget(self._refresh_btn)
        btn_layout.addWidget(self._clear_btn)
        btn_layout.addWidget(self._close_btn)
        layout.addLayout(btn_layout)
        
        _sig = i18n_language_changed()
        if _sig:
            _sig.connect(self._on_language_changed)
    
    def _on_language_changed(self, lang):
        self.setWindowTitle(i18n("dialog.diag_log_manage"))
        self._table.setHorizontalHeaderLabels([i18n("header.log_name"), i18n("header.file_size"), i18n("header.current_level"), i18n("header.clear")])
        self._refresh_btn.setText(i18n("btn.refresh"))
        self._clear_btn.setText(i18n("btn.confirm_clear"))
        self._close_btn.setText(i18n("btn.close"))
        self._refresh_table()

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_table()

    def _refresh_table(self):
        targets = self._registry.get_all_targets()
        self._table.setRowCount(len(targets))
        for row, target in enumerate(targets):
            desc_item = QTableWidgetItem(f'{target.description}\n({target.file_name})')
            desc_item.setFlags(desc_item.flags() & ~Qt.ItemIsEditable)
            self._table.setItem(row, 0, desc_item)

            file_size = self._registry.get_file_size(target)
            size_item = QTableWidgetItem(self._registry.format_file_size(file_size))
            size_item.setFlags(size_item.flags() & ~Qt.ItemIsEditable)
            size_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._table.setItem(row, 1, size_item)

            level = self._registry.get_log_level(target)
            level_item = QTableWidgetItem(level)
            level_item.setFlags(level_item.flags() & ~Qt.ItemIsEditable)
            level_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, 2, level_item)

            clear_item = QTableWidgetItem()
            clear_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            clear_item.setCheckState(Qt.Unchecked)
            clear_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, 3, clear_item)

    def _on_refresh_clicked(self):
        self._refresh_table()

    def _on_clear_clicked(self):
        targets = self._registry.get_all_targets()
        to_clear = []
        for row in range(self._table.rowCount()):
            if self._table.item(row, 3).checkState() == Qt.Checked:
                to_clear.append((row, targets[row]))

        if not to_clear:
            QMessageBox.information(self, i18n("dialog.hint_title"), i18n("error.please_check_log_to_clear"))
            return

        names = ', '.join(t.file_name for _, t in to_clear)
        reply = QMessageBox.question(
            self, i18n("dialog.confirm_clear"),
            i18n("error.will_clear_logs").format(names),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        failed = []
        for row, target in to_clear:
            ok, reason = self._registry.clear_log_file(target)
            if not ok:
                failed.append(f'{target.file_name}: {reason}')
            self._table.item(row, 3).setCheckState(Qt.Unchecked)

        if failed:
            QMessageBox.warning(self, i18n("error.clear_failed"), chr(10).join(failed))
        self._refresh_table()
