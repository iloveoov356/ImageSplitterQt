from __future__ import annotations

from typing import List, Optional

from PySide6 import QtCore, QtWidgets

from src.core.models import GuideLine


class LineListWidget(QtWidgets.QTableWidget):
    line_selected = QtCore.Signal(object)
    line_y_changed = QtCore.Signal(str, float)
    line_lock_toggled = QtCore.Signal(str, bool)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(0, 2, parent)
        self.setHorizontalHeaderLabels(["Y (px)", "Locked"])
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked | QtWidgets.QAbstractItemView.EditKeyPressed)
        self._updating = False

        self.itemSelectionChanged.connect(self._on_selection_changed)
        self.cellChanged.connect(self._on_cell_changed)

    def set_lines(self, lines: List[GuideLine], selected_id: Optional[str]) -> None:
        self._updating = True
        self.setRowCount(len(lines))
        for row, line in enumerate(lines):
            y_item = QtWidgets.QTableWidgetItem(f"{line.y:.1f}")
            y_item.setData(QtCore.Qt.UserRole, line.id)
            flags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
            if not line.locked:
                flags |= QtCore.Qt.ItemIsEditable
            y_item.setFlags(flags)

            lock_item = QtWidgets.QTableWidgetItem()
            lock_item.setData(QtCore.Qt.UserRole, line.id)
            lock_item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
            lock_item.setCheckState(QtCore.Qt.Checked if line.locked else QtCore.Qt.Unchecked)

            self.setItem(row, 0, y_item)
            self.setItem(row, 1, lock_item)

            if selected_id == line.id:
                self.selectRow(row)
        self._updating = False

    def _on_selection_changed(self) -> None:
        if self._updating:
            return
        items = self.selectedItems()
        if not items:
            self.line_selected.emit(None)
            return
        line_id = items[0].data(QtCore.Qt.UserRole)
        self.line_selected.emit(line_id)

    def _on_cell_changed(self, row: int, column: int) -> None:
        if self._updating:
            return
        item = self.item(row, column)
        if not item:
            return
        line_id = item.data(QtCore.Qt.UserRole)
        if column == 0:
            try:
                value = float(item.text())
                self.line_y_changed.emit(line_id, value)
            except ValueError:
                pass
        elif column == 1:
            self.line_lock_toggled.emit(line_id, item.checkState() == QtCore.Qt.Checked)

    def select_line(self, line_id: Optional[str]) -> None:
        if line_id is None:
            self.clearSelection()
            return
        for row in range(self.rowCount()):
            item = self.item(row, 0)
            if item and item.data(QtCore.Qt.UserRole) == line_id:
                self._updating = True
                self.selectRow(row)
                self._updating = False
                return
