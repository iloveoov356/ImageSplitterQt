from __future__ import annotations

from pathlib import Path

from PySide6 import QtCore

from .models import ExportFormat, SnapMode


class SettingsStore:
    def __init__(self) -> None:
        self._settings = QtCore.QSettings("ImageSplitter", "ImageSplitterQt")

    def last_open_dir(self) -> str:
        return self._settings.value("paths/last_open", str(Path.home()), type=str)

    def set_last_open_dir(self, path: str) -> None:
        self._settings.setValue("paths/last_open", path)

    def last_export_dir(self) -> str:
        return self._settings.value("paths/last_export", str(Path.home()), type=str)

    def set_last_export_dir(self, path: str) -> None:
        self._settings.setValue("paths/last_export", path)

    def export_format(self) -> ExportFormat:
        value = self._settings.value("export/format", ExportFormat.PNG.value, type=str)
        try:
            return ExportFormat(value)
        except ValueError:
            return ExportFormat.PNG

    def set_export_format(self, fmt: ExportFormat) -> None:
        self._settings.setValue("export/format", fmt.value)

    def jpeg_quality(self) -> int:
        return self._settings.value("export/jpeg_quality", 90, type=int)

    def set_jpeg_quality(self, quality: int) -> None:
        self._settings.setValue("export/jpeg_quality", quality)

    def snap_mode(self) -> SnapMode:
        value = self._settings.value("snap/mode", SnapMode.PIXEL.value, type=str)
        try:
            return SnapMode(value)
        except ValueError:
            return SnapMode.PIXEL

    def set_snap_mode(self, mode: SnapMode) -> None:
        self._settings.setValue("snap/mode", mode.value)

    def grid_size(self) -> int:
        return self._settings.value("snap/grid_size", 10, type=int)

    def set_grid_size(self, size: int) -> None:
        self._settings.setValue("snap/grid_size", size)

    def show_grid(self) -> bool:
        return self._settings.value("snap/show_grid", False, type=bool)

    def set_show_grid(self, show: bool) -> None:
        self._settings.setValue("snap/show_grid", show)

    def show_grid_vertical(self) -> bool:
        return self._settings.value("snap/show_grid_vertical", False, type=bool)

    def set_show_grid_vertical(self, show: bool) -> None:
        self._settings.setValue("snap/show_grid_vertical", show)

    def language(self) -> str:
        return self._settings.value("ui/language", "en", type=str)

    def set_language(self, language: str) -> None:
        self._settings.setValue("ui/language", language)

    def restore_window_geometry(self, widget: QtCore.QObject) -> None:
        geometry = self._settings.value("window/geometry")
        if geometry:
            widget.restoreGeometry(geometry)

    def save_window_geometry(self, widget: QtCore.QObject) -> None:
        self._settings.setValue("window/geometry", widget.saveGeometry())

    def restore_splitter_state(self, splitter: QtCore.QObject) -> None:
        state = self._settings.value("window/splitter")
        if state:
            splitter.restoreState(state)

    def save_splitter_state(self, splitter: QtCore.QObject) -> None:
        self._settings.setValue("window/splitter", splitter.saveState())
