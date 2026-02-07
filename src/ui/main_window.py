from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

from src.core.controller import GuideController
from src.core.models import ExportFormat, SnapMode
from src.core.settings import SettingsStore
from src.core.utils import ensure_directory
from src.i18n.locale import I18n, LANGUAGES
from .canvas import CanvasView
from .line_list import LineListWidget

_LOG = logging.getLogger(__name__)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, i18n: I18n) -> None:
        super().__init__()
        self.i18n = i18n
        self.settings = SettingsStore()
        # restore saved language early
        saved_lang = self.settings.language()
        self.i18n.set_language(saved_lang)
        self.t = self.i18n.tr

        self.setWindowTitle(self.t("app.title"))
        self.resize(1200, 800)

        self.controller = GuideController(self.i18n)

        self.canvas = CanvasView()
        self.line_list = LineListWidget()

        self._build_ui()
        self._connect_signals()
        self._apply_translations()
        self._restore_settings()

        self._update_export_controls()
        self._refresh_actions()

    def _build_ui(self) -> None:
        # Toolbar actions
        self.open_action = QtGui.QAction(self)
        self.open_action.setShortcut(QtGui.QKeySequence.Open)
        self.close_action = QtGui.QAction(self)
        self.close_action.setShortcut(QtGui.QKeySequence(QtGui.QKeySequence.Close))
        self.add_line_action = QtGui.QAction(self)
        self.delete_line_action = QtGui.QAction(self)
        self.delete_line_action.setShortcut(QtGui.QKeySequence.Delete)
        self.clear_lines_action = QtGui.QAction(self)

        self.undo_action = QtGui.QAction(self)
        self.undo_action.setShortcut(QtGui.QKeySequence.Undo)
        self.redo_action = QtGui.QAction(self)
        self.redo_action.setShortcuts([QtGui.QKeySequence.Redo, QtGui.QKeySequence("Ctrl+Shift+Z")])

        toolbar = self.addToolBar("Main")
        toolbar.addAction(self.open_action)
        toolbar.addAction(self.close_action)
        toolbar.addAction(self.add_line_action)
        toolbar.addAction(self.clear_lines_action)
        toolbar.addAction(self.delete_line_action)
        toolbar.addSeparator()
        toolbar.addAction(self.undo_action)
        toolbar.addAction(self.redo_action)

        # Menus (keep visible inside window for macOS)
        self.menuBar().setNativeMenuBar(False)
        self.file_menu = self.menuBar().addMenu("")
        self.edit_menu = self.menuBar().addMenu("")
        self.guides_menu = self.menuBar().addMenu("")
        self.language_menu = self.menuBar().addMenu("")

        self.file_menu.addAction(self.open_action)
        self.file_menu.addAction(self.close_action)
        self.edit_menu.addAction(self.undo_action)
        self.edit_menu.addAction(self.redo_action)
        self.guides_menu.addAction(self.add_line_action)
        self.guides_menu.addAction(self.clear_lines_action)
        self.guides_menu.addAction(self.delete_line_action)

        self.language_actions = {}
        for code, label in LANGUAGES.items():
            act = QtGui.QAction(label, self, checkable=True)
            act.setData(code)
            act.triggered.connect(lambda checked, c=code: self._on_language_changed(c))
            self.language_menu.addAction(act)
            self.language_actions[code] = act

        # Right panel controls
        controls = QtWidgets.QWidget()
        controls_layout = QtWidgets.QVBoxLayout(controls)
        controls_layout.setContentsMargins(8, 8, 8, 8)
        controls_layout.setSpacing(10)

        # Snap settings
        self.snap_group = QtWidgets.QGroupBox()
        snap_layout = QtWidgets.QFormLayout(self.snap_group)
        self.snap_mode_combo = QtWidgets.QComboBox()
        self.grid_size_spin = QtWidgets.QSpinBox()
        self.grid_size_spin.setRange(1, 500)
        self.grid_size_spin.setValue(10)
        self.snap_mode_label = QtWidgets.QLabel()
        self.grid_size_label = QtWidgets.QLabel()
        snap_layout.addRow(self.snap_mode_label, self.snap_mode_combo)
        snap_layout.addRow(self.grid_size_label, self.grid_size_spin)

        # Line list
        self.line_group = QtWidgets.QGroupBox()
        line_layout = QtWidgets.QVBoxLayout(self.line_group)
        line_layout.addWidget(self.line_list)

        # Export settings
        self.export_group = QtWidgets.QGroupBox()
        export_layout = QtWidgets.QFormLayout(self.export_group)
        self.output_dir_edit = QtWidgets.QLineEdit()
        self.output_dir_button = QtWidgets.QPushButton()
        output_layout = QtWidgets.QHBoxLayout()
        output_layout.addWidget(self.output_dir_edit)
        output_layout.addWidget(self.output_dir_button)
        self.format_combo = QtWidgets.QComboBox()
        self.quality_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.quality_slider.setRange(1, 100)
        self.quality_slider.setValue(90)
        self.quality_value = QtWidgets.QSpinBox()
        self.quality_value.setRange(1, 100)
        self.quality_value.setValue(90)
        quality_layout = QtWidgets.QHBoxLayout()
        quality_layout.addWidget(self.quality_slider)
        quality_layout.addWidget(self.quality_value)
        self.export_button = QtWidgets.QPushButton()

        self.output_dir_label = QtWidgets.QLabel()
        self.format_label = QtWidgets.QLabel()
        self.quality_label = QtWidgets.QLabel()

        export_layout.addRow(self.output_dir_label, output_layout)
        export_layout.addRow(self.format_label, self.format_combo)
        export_layout.addRow(self.quality_label, quality_layout)
        export_layout.addRow(self.export_button)

        controls_layout.addWidget(self.snap_group)
        controls_layout.addWidget(self.line_group)
        controls_layout.addWidget(self.export_group)
        controls_layout.addStretch()

        splitter = QtWidgets.QSplitter()
        splitter.addWidget(self.canvas)
        splitter.addWidget(controls)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        self.setCentralWidget(splitter)

        # Status bar
        self.coord_label = QtWidgets.QLabel()
        self.selected_label = QtWidgets.QLabel()
        self.statusBar().addPermanentWidget(self.coord_label)
        self.statusBar().addPermanentWidget(self.selected_label)

    def _connect_signals(self) -> None:
        self.open_action.triggered.connect(self._open_image_dialog)
        self.close_action.triggered.connect(self.controller.close_image)
        self.add_line_action.triggered.connect(self._add_line)
        self.delete_line_action.triggered.connect(self._delete_line)
        self.clear_lines_action.triggered.connect(self.controller.clear_lines)
        self.undo_action.triggered.connect(self.controller.undo)
        self.redo_action.triggered.connect(self.controller.redo)

        self.snap_mode_combo.currentIndexChanged.connect(self._on_snap_mode_changed)
        self.grid_size_spin.valueChanged.connect(self._on_grid_size_changed)

        self.output_dir_button.clicked.connect(self._choose_output_dir)
        self.format_combo.currentIndexChanged.connect(self._update_export_controls)
        self.quality_slider.valueChanged.connect(self.quality_value.setValue)
        self.quality_value.valueChanged.connect(self.quality_slider.setValue)
        self.quality_value.valueChanged.connect(self._update_export_controls)
        self.export_button.clicked.connect(self._export)

        self.canvas.file_dropped.connect(self.controller.load_image)
        self.canvas.line_move_finished.connect(self._line_moved_from_canvas)
        self.canvas.line_selected.connect(self.controller.select_line)
        self.canvas.mouse_position_changed.connect(self._update_mouse_status)
        self.canvas.guide_requested.connect(self.controller.add_line)

        self.line_list.line_selected.connect(self.controller.select_line)
        self.line_list.line_y_changed.connect(self.controller.move_line)
        self.line_list.line_lock_toggled.connect(self.controller.set_locked)

        self.controller.image_changed.connect(self._on_image_changed)
        self.controller.image_cleared.connect(self._on_image_cleared)
        self.controller.lines_changed.connect(self._on_lines_changed)
        self.controller.selection_changed.connect(self._on_selection_changed)
        self.controller.status_message.connect(self.statusBar().showMessage)
        self.controller.undo_state_changed.connect(self._on_undo_state_changed)
        self.controller.export_finished.connect(self._on_export_finished)

    def _apply_translations(self) -> None:
        self.setWindowTitle(self.t("app.title"))
        self.open_action.setText(self.t("action.open"))
        self.close_action.setText(self.t("action.close_image"))
        self.add_line_action.setText(self.t("action.add_line"))
        self.delete_line_action.setText(self.t("action.delete_line"))
        self.clear_lines_action.setText(self.t("action.clear_guides"))
        self.undo_action.setText(self.t("action.undo"))
        self.redo_action.setText(self.t("action.redo"))

        # Language menu
        self.file_menu.setTitle(self.t("menu.file"))
        self.edit_menu.setTitle(self.t("menu.edit"))
        self.guides_menu.setTitle(self.t("menu.guides"))
        self.language_menu.setTitle(self.t("menu.language"))
        for code, act in self.language_actions.items():
            act.setText(LANGUAGES[code])
            act.setChecked(code == self.i18n.language)

        # Snap section
        self.snap_group.setTitle(self.t("snap.title"))
        self.snap_mode_label.setText(self.t("snap.mode"))
        self.grid_size_label.setText(self.t("snap.grid_size"))
        current_snap_index = self.snap_mode_combo.currentIndex()
        self.snap_mode_combo.clear()
        self.snap_mode_combo.addItems([self.t("snap.off"), self.t("snap.pixel"), self.t("snap.grid")])
        if current_snap_index >= 0:
            self.snap_mode_combo.setCurrentIndex(current_snap_index)

        # Guides
        self.line_group.setTitle(self.t("guides.title"))
        self.line_list.setHorizontalHeaderLabels([self.t("table.y"), self.t("table.locked")])

        # Export
        self.export_group.setTitle(self.t("export.title"))
        self.output_dir_label.setText(self.t("export.output_dir"))
        self.output_dir_button.setText(self.t("export.browse"))
        self.format_label.setText(self.t("export.format"))
        fmt_index = self.format_combo.currentIndex()
        self.format_combo.clear()
        self.format_combo.addItems([self.t("format.png"), self.t("format.jpeg"), self.t("format.keep")])
        if fmt_index >= 0:
            self.format_combo.setCurrentIndex(fmt_index)
        self.quality_label.setText(self.t("export.jpeg_quality"))
        self.export_button.setText(self.t("export.button"))

        # Status labels defaults
        self.coord_label.setText(self.t("status.coord", x="-", y="-"))
        self.selected_label.setText(self.t("status.selected.none"))

    def _restore_settings(self) -> None:
        self.snap_mode_combo.setCurrentIndex(self._snap_index(self.settings.snap_mode()))
        self.grid_size_spin.setValue(self.settings.grid_size())
        self.output_dir_edit.setText(self.settings.last_export_dir())
        self.format_combo.setCurrentIndex(self._format_index(self.settings.export_format()))
        quality = self.settings.jpeg_quality()
        self.quality_slider.setValue(quality)
        self.quality_value.setValue(quality)
        self.settings.restore_window_geometry(self)
        splitter = self.centralWidget()
        if isinstance(splitter, QtWidgets.QSplitter):
            self.settings.restore_splitter_state(splitter)

    def _open_image_dialog(self) -> None:
        start_dir = self.settings.last_open_dir()
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, self.t("dialog.open.title"), start_dir, self.t("dialog.open.filter")
        )
        if file_path:
            if self.controller.load_image(file_path):
                self.settings.set_last_open_dir(str(Path(file_path).parent))

    def _add_line(self) -> None:
        size = self.controller.image_size
        y = size.height() / 2 if size else 0
        self.controller.add_line(y)

    def _delete_line(self) -> None:
        self.controller.delete_line()

    def _on_image_changed(self, image: QtGui.QImage, path: str) -> None:
        self.canvas.set_image(image)
        self._refresh_actions()

    def _on_image_cleared(self) -> None:
        self.canvas.clear()
        self.line_list.set_lines([], selected_id=None)
        self.selected_label.setText(self.t("status.selected.none"))
        self._refresh_actions()

    def _on_lines_changed(self, lines: list) -> None:
        selected = self.controller.selected_id
        self.canvas.set_lines(lines, selected_id=selected)
        self.line_list.set_lines(lines, selected_id=selected)
        self._refresh_actions()

    def _on_selection_changed(self, line_id: Optional[str]) -> None:
        self.canvas.update_selection(line_id)
        self.line_list.select_line(line_id)
        if line_id:
            line = next((l for l in self.controller.sorted_lines() if l.id == line_id), None)
            if line:
                self.selected_label.setText(self.t("status.selected.value", y=f"{line.y:.1f}"))
        else:
            self.selected_label.setText(self.t("status.selected.none"))
        self._refresh_actions()

    def _line_moved_from_canvas(self, line_id: str, y: float) -> None:
        self.controller.move_line(line_id, y)

    def _on_snap_mode_changed(self, index: int) -> None:
        mode = [SnapMode.OFF, SnapMode.PIXEL, SnapMode.GRID][index]
        self.controller.set_snap_mode(mode)
        self.settings.set_snap_mode(mode)

    def _on_grid_size_changed(self, value: int) -> None:
        self.controller.set_grid_size(value)
        self.settings.set_grid_size(value)

    def _on_language_changed(self, language: str) -> None:
        self.i18n.set_language(language)
        self.settings.set_language(language)
        self._apply_translations()
        self._update_export_controls()

    def _choose_output_dir(self) -> None:
        start = self.output_dir_edit.text() or self.settings.last_export_dir()
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self, self.t("dialog.output_dir"), start
        )
        if directory:
            self.output_dir_edit.setText(directory)
            self.settings.set_last_export_dir(directory)

    def _export(self) -> None:
        output_dir = self.output_dir_edit.text() or self.settings.last_export_dir()
        fmt = self._format_from_combo()
        quality = self.quality_value.value()
        self.settings.set_export_format(fmt)
        self.settings.set_jpeg_quality(quality)
        self.settings.set_last_export_dir(output_dir)
        self.controller.export(output_dir, fmt, quality)

    def _format_from_combo(self) -> ExportFormat:
        index = self.format_combo.currentIndex()
        return [ExportFormat.PNG, ExportFormat.JPEG, ExportFormat.KEEP][index]

    def _format_index(self, fmt: ExportFormat) -> int:
        mapping = {ExportFormat.PNG: 0, ExportFormat.JPEG: 1, ExportFormat.KEEP: 2}
        return mapping.get(fmt, 0)

    def _snap_index(self, mode: SnapMode) -> int:
        mapping = {SnapMode.OFF: 0, SnapMode.PIXEL: 1, SnapMode.GRID: 2}
        return mapping.get(mode, 1)

    def _update_export_controls(self) -> None:
        fmt = self._format_from_combo()
        is_jpeg = fmt == ExportFormat.JPEG
        self.quality_slider.setEnabled(is_jpeg)
        self.quality_value.setEnabled(is_jpeg)
        if not is_jpeg:
            self.quality_slider.setToolTip(self.t("tooltip.quality_only_jpeg"))
        else:
            self.quality_slider.setToolTip("")

    def _on_undo_state_changed(self, can_undo: bool, can_redo: bool) -> None:
        self.undo_action.setEnabled(can_undo)
        self.redo_action.setEnabled(can_redo)

    def _on_export_finished(self, result) -> None:
        parts = []
        if result.written:
            parts.append(self.t("status.export_ok", count=len(result.written)))
        if result.skipped:
            parts.append(self.t("status.export_skipped", count=len(result.skipped)))
        if result.errors:
            parts.append(self.t("status.export_errors"))
        message = ", ".join(parts) if parts else self.t("status.export_errors")

        if result.errors:
            QtWidgets.QMessageBox.warning(
                self,
                self.t("msgbox.export.errors.title"),
                "\n".join(result.errors),
            )
        else:
            QtWidgets.QMessageBox.information(
                self,
                self.t("msgbox.export.ok.title"),
                message,
            )

    def _update_mouse_status(self, x: float, y: float) -> None:
        self.coord_label.setText(self.t("status.coord", x=f"{x:.1f}", y=f"{y:.1f}"))

    def _refresh_actions(self) -> None:
        has_image = self.controller.has_image
        self.add_line_action.setEnabled(has_image)
        self.clear_lines_action.setEnabled(has_image and bool(self.controller.sorted_lines()))
        self.export_button.setEnabled(has_image)
        self.delete_line_action.setEnabled(has_image and self.controller.selected_id is not None)
        self.close_action.setEnabled(has_image)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.settings.save_window_geometry(self)
        splitter = self.centralWidget()
        if isinstance(splitter, QtWidgets.QSplitter):
            self.settings.save_splitter_state(splitter)
        super().closeEvent(event)
