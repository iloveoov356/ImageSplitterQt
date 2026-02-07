from __future__ import annotations

import logging
import random
import uuid
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from PySide6 import QtCore, QtGui

from . import commands
from .exporter import export_image_segments
from .image_loader import load_image
from .models import ExportFormat, ExportResult, GuideLine, SnapMode
from .utils import apply_snap, clamp
from src.i18n.locale import I18n

_LOG = logging.getLogger(__name__)


class GuideController(QtCore.QObject):
    image_changed = QtCore.Signal(QtGui.QImage, str)
    image_cleared = QtCore.Signal()
    lines_changed = QtCore.Signal(list)
    selection_changed = QtCore.Signal(object)
    status_message = QtCore.Signal(str)
    undo_state_changed = QtCore.Signal(bool, bool)
    export_finished = QtCore.Signal(ExportResult)

    def __init__(self, i18n: I18n) -> None:
        super().__init__()
        self._lines: Dict[str, GuideLine] = {}
        self._selected_id: Optional[str] = None
        self._image: Optional[QtGui.QImage] = None
        self._image_path: Optional[str] = None
        self.snap_mode: SnapMode = SnapMode.PIXEL
        self.grid_size: int = 10
        self._commands = commands.CommandStack()
        self._i18n = i18n

    @property
    def has_image(self) -> bool:
        return self._image is not None

    @property
    def image_size(self) -> Optional[QtCore.QSize]:
        return self._image.size() if self._image else None

    @property
    def selected_id(self) -> Optional[str]:
        return self._selected_id

    def load_image(self, path: str) -> bool:
        image = load_image(path)
        if image is None:
            self.status_message.emit(self._i18n.tr("status.failed_load"))
            return False
        self._image = image
        self._image_path = path
        self._lines.clear()
        self._selected_id = None
        self._commands = commands.CommandStack()
        self.image_changed.emit(image, path)
        self.lines_changed.emit([])
        self.undo_state_changed.emit(False, False)
        self.status_message.emit(
            self._i18n.tr("status.loaded", name=Path(path).name, w=image.width(), h=image.height())
        )
        return True

    def set_snap_mode(self, mode: SnapMode) -> None:
        self.snap_mode = mode
        display = {
            SnapMode.OFF: self._i18n.tr("snap.off"),
            SnapMode.PIXEL: self._i18n.tr("snap.pixel"),
            SnapMode.GRID: self._i18n.tr("snap.grid"),
        }.get(mode, mode.value)
        self.status_message.emit(self._i18n.tr("status.snap_mode", mode=display))

    def set_grid_size(self, size: int) -> None:
        self.grid_size = max(1, size)

    def add_line(self, y: float) -> None:
        if not self._image:
            self.status_message.emit(self._i18n.tr("status.open_first"))
            return
        y = self._normalize_y(y)
        if self._is_duplicate_y(y):
            self.status_message.emit(self._i18n.tr("status.line_exists"))
            return
        line = GuideLine(id=str(uuid.uuid4()), y=y)
        cmd = commands.AddLineCommand(self, line)
        self._commands.push_and_execute(cmd)
        self.select_line(line.id)
        self._emit_undo_state()

    def delete_line(self, line_id: Optional[str] = None) -> None:
        target_id = line_id or self._selected_id
        if not target_id or target_id not in self._lines:
            return
        line = self._lines[target_id]
        cmd = commands.DeleteLineCommand(self, line)
        self._commands.push_and_execute(cmd)
        if self._selected_id == target_id:
            self._selected_id = None
            self.selection_changed.emit(None)
        self._emit_undo_state()

    def clear_lines(self) -> None:
        if not self._lines:
            return
        previous = self.sorted_lines()
        cmd = commands.ClearLinesCommand(self, previous)
        self._commands.push_and_execute(cmd)
        self._selected_id = None
        self.selection_changed.emit(None)
        self._emit_undo_state()

    def close_image(self) -> None:
        if not self._image:
            return
        self._image = None
        self._image_path = None
        self._lines.clear()
        self._selected_id = None
        self._commands = commands.CommandStack()
        self.lines_changed.emit([])
        self.selection_changed.emit(None)
        self.undo_state_changed.emit(False, False)
        self.image_cleared.emit()
        self.status_message.emit(self._i18n.tr("status.image_closed"))

    def move_line(self, line_id: str, new_y: float) -> None:
        if line_id not in self._lines or not self._image:
            return
        line = self._lines[line_id]
        new_y = self._normalize_y(new_y)
        if abs(new_y - line.y) < 0.1:
            return
        if self._is_duplicate_y(new_y, exclude_id=line_id):
            self.status_message.emit(self._i18n.tr("status.line_exists_other"))
            return
        cmd = commands.MoveLineCommand(self, line_id, line.y, new_y)
        self._commands.push_and_execute(cmd)
        self._emit_undo_state()

    def set_locked(self, line_id: str, locked: bool) -> None:
        if line_id not in self._lines:
            return
        line = self._lines[line_id]
        if line.locked == locked:
            return
        cmd = commands.LockLineCommand(self, line_id, locked)
        self._commands.push_and_execute(cmd)
        self._emit_undo_state()

    def select_line(self, line_id: Optional[str]) -> None:
        if line_id and line_id not in self._lines:
            return
        self._selected_id = line_id
        self.selection_changed.emit(line_id)

    def undo(self) -> None:
        self._commands.undo()
        self._emit_undo_state()

    def redo(self) -> None:
        self._commands.redo()
        self._emit_undo_state()

    def sorted_lines(self) -> List[GuideLine]:
        return sorted(self._lines.values(), key=lambda l: l.y)

    def export(self, output_dir: str, export_format: ExportFormat, jpeg_quality: int = 90) -> None:
        if not self._image or not self._image_path:
            self.status_message.emit(self._i18n.tr("status.open_first"))
            return
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        rand = random.randint(0, 999)
        subdir = f"{ts}_{rand:03d}"
        target_dir = str(Path(output_dir) / subdir)
        result = export_image_segments(
            image=self._image,
            lines=self.sorted_lines(),
            output_dir=target_dir,
            export_format=export_format,
            jpeg_quality=jpeg_quality,
            original_suffix=Path(self._image_path).suffix,
            tr=self._i18n.tr,
        )
        self.export_finished.emit(result)
        if result.errors:
            self.status_message.emit(self._i18n.tr("status.export_errors"))
        else:
            self.status_message.emit(self._i18n.tr("status.export_ok", count=len(result.written)))

    # Internal mutation helpers called by commands
    def _add_line(self, line: GuideLine) -> None:
        self._lines[line.id] = line
        self.lines_changed.emit(self.sorted_lines())

    def _remove_line(self, line_id: str) -> None:
        if line_id in self._lines:
            del self._lines[line_id]
        if self._selected_id == line_id:
            self._selected_id = None
            self.selection_changed.emit(None)
        self.lines_changed.emit(self.sorted_lines())

    def _set_all_lines(self, lines: List[GuideLine]) -> None:
        self._lines = {line.id: line for line in lines}
        self._selected_id = None
        self.lines_changed.emit(self.sorted_lines())

    def _move_line(self, line_id: str, new_y: float) -> None:
        if line_id not in self._lines:
            return
        line = self._lines[line_id]
        self._lines[line_id] = replace(line, y=new_y)
        self.lines_changed.emit(self.sorted_lines())

    def _set_locked(self, line_id: str, locked: bool) -> None:
        if line_id not in self._lines:
            return
        line = self._lines[line_id]
        self._lines[line_id] = replace(line, locked=locked)
        self.lines_changed.emit(self.sorted_lines())

    def _normalize_y(self, y: float) -> float:
        if not self._image:
            return y
        snapped = apply_snap(y, self.snap_mode, self.grid_size)
        return clamp(snapped, 0, float(self._image.height()))

    def _is_duplicate_y(self, y: float, exclude_id: Optional[str] = None) -> bool:
        for line in self._lines.values():
            if exclude_id and line.id == exclude_id:
                continue
            if abs(line.y - y) < 0.1:
                return True
        return False

    def _emit_undo_state(self) -> None:
        self.undo_state_changed.emit(self._commands.can_undo, self._commands.can_redo)
