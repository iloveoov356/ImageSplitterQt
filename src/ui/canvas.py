from __future__ import annotations

from typing import Dict, Optional

from PySide6 import QtCore, QtGui, QtWidgets

from src.core.models import GuideLine
from src.core.utils import clamp


class GuideLineItem(QtWidgets.QGraphicsLineItem):
    def __init__(self, line: GuideLine, width: float, parent: Optional[QtWidgets.QGraphicsItem] = None):
        super().__init__(parent)
        self.line_id = line.id
        self.locked = line.locked
        self.width = width
        self.setZValue(10)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        self._update_pen(selected=False)
        self.setLine(0, line.y, self.width, line.y)

    def update_from_model(self, line: GuideLine, width: float, selected: bool) -> None:
        self.locked = line.locked
        self.width = width
        self.setLine(0, line.y, self.width, line.y)
        self._update_pen(selected)

    def _update_pen(self, selected: bool) -> None:
        color = QtGui.QColor("#2a8cff" if selected else "#00a676")
        if self.locked:
            color = QtGui.QColor("#888888")
        pen = QtGui.QPen(color, 2.5 if selected else 1.8)
        if self.locked:
            pen.setStyle(QtCore.Qt.DashLine)
        self.setPen(pen)

    def hoverEnterEvent(self, event: QtWidgets.QGraphicsSceneHoverEvent) -> None:
        if not self.locked:
            self.setCursor(QtCore.Qt.SizeVerCursor)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event: QtWidgets.QGraphicsSceneHoverEvent) -> None:
        self.unsetCursor()
        super().hoverLeaveEvent(event)


class CanvasView(QtWidgets.QGraphicsView):
    file_dropped = QtCore.Signal(str)
    line_move_finished = QtCore.Signal(str, float)
    line_selected = QtCore.Signal(object)
    mouse_position_changed = QtCore.Signal(float, float)
    guide_requested = QtCore.Signal(float)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setScene(QtWidgets.QGraphicsScene(self))
        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
        self.setViewportUpdateMode(QtWidgets.QGraphicsView.SmartViewportUpdate)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)

        self._pixmap_item: Optional[QtWidgets.QGraphicsPixmapItem] = None
        self._line_items: Dict[str, GuideLineItem] = {}
        self._image_width: float = 0
        self._image_height: float = 0
        self._current_selection: Optional[str] = None
        self._panning: bool = False
        self._last_pan_point: Optional[QtCore.QPoint] = None
        self._dragging_item: Optional[GuideLineItem] = None
        self._ruler_height: int = 28
        self._ruler_dragging: bool = False
        self._ruler_preview_y: Optional[float] = None

    def set_image(self, image: QtGui.QImage) -> None:
        self.scene().clear()
        self._line_items.clear()
        self._pixmap_item = QtWidgets.QGraphicsPixmapItem(QtGui.QPixmap.fromImage(image))
        self.scene().addItem(self._pixmap_item)
        self._image_width = image.width()
        self._image_height = image.height()
        self.setSceneRect(QtCore.QRectF(0, 0, self._image_width, self._image_height))
        self.resetTransform()
        # Default zoom to 85% for better overview on large assets
        self.scale(0.85, 0.85)
        self.centerOn(self._image_width / 2, self._image_height / 2)
        self.viewport().update()

    def clear(self) -> None:
        self.scene().clear()
        self._line_items.clear()
        self._pixmap_item = None
        self._image_width = 0
        self._image_height = 0
        self._current_selection = None
        self.viewport().update()

    def set_lines(self, lines: list, selected_id: Optional[str] = None) -> None:
        existing_ids = set(self._line_items.keys())
        self._current_selection = selected_id
        # add or update
        for line in lines:
            if line.id not in self._line_items:
                item = GuideLineItem(line, self._image_width)
                item.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
                self._line_items[line.id] = item
                self.scene().addItem(item)
            selected = selected_id == line.id
            self._line_items[line.id].update_from_model(line, self._image_width, selected)
        # remove missing
        for line_id in list(existing_ids - {l.id for l in lines}):
            item = self._line_items.pop(line_id, None)
            if item:
                self.scene().removeItem(item)
                item.setParentItem(None)
        self.viewport().update()

    def update_selection(self, line_id: Optional[str]) -> None:
        self._current_selection = line_id
        for lid, item in self._line_items.items():
            item._update_pen(selected=(lid == line_id))
        self.viewport().update()

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QtGui.QDragMoveEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QtGui.QDropEvent) -> None:
        urls = event.mimeData().urls()
        if urls:
            local_path = urls[0].toLocalFile()
            if local_path:
                self.file_dropped.emit(local_path)
        event.acceptProposedAction()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.pos().y() <= self._ruler_height and self._image_height > 0:
            self._ruler_dragging = True
            scene_pos = self.mapToScene(event.pos())
            self._ruler_preview_y = clamp(scene_pos.y(), 0, self._image_height)
            self.setCursor(QtCore.Qt.CrossCursor)
            event.accept()
            return
        if event.button() == QtCore.Qt.MiddleButton:
            self._panning = True
            self._last_pan_point = event.pos()
            self.setCursor(QtCore.Qt.ClosedHandCursor)
            event.accept()
            return
        if event.button() == QtCore.Qt.LeftButton:
            item = self.itemAt(event.pos())
            if isinstance(item, GuideLineItem):
                self.line_selected.emit(item.line_id)
                if not item.locked:
                    self._dragging_item = item
                    self._drag_start_y = item.line().y1()
                else:
                    self._dragging_item = None
            else:
                self.line_selected.emit(None)
                self._dragging_item = None
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        scene_pos = self.mapToScene(event.pos())
        self.mouse_position_changed.emit(scene_pos.x(), scene_pos.y())

        if self._ruler_dragging:
            self._ruler_preview_y = clamp(scene_pos.y(), 0, self._image_height)
            self.viewport().update()
            event.accept()
            return

        if self._panning and self._last_pan_point:
            delta = event.pos() - self._last_pan_point
            self._last_pan_point = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
            return

        if self._dragging_item:
            y = clamp(scene_pos.y(), 0, self._image_height)
            self._dragging_item.setLine(0, y, self._image_width, y)
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._ruler_dragging:
            self._ruler_dragging = False
            self.unsetCursor()
            y_scene = self.mapToScene(event.pos()).y()
            y_scene = clamp(y_scene, 0, self._image_height)
            self.guide_requested.emit(y_scene)
            self._ruler_preview_y = None
            self.viewport().update()
            event.accept()
            return
        if event.button() == QtCore.Qt.MiddleButton and self._panning:
            self._panning = False
            self._last_pan_point = None
            self.unsetCursor()
            event.accept()
            return

        if event.button() == QtCore.Qt.LeftButton and hasattr(self, "_dragging_item"):
            item = getattr(self, "_dragging_item")
            if item:
                y = item.line().y1()
                self.line_move_finished.emit(item.line_id, y)
            self._dragging_item = None
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        if event.angleDelta().y() == 0:
            return
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)

    def drawForeground(self, painter: QtGui.QPainter, rect: QtCore.QRectF) -> None:
        super().drawForeground(painter, rect)
        if self._image_height <= 0:
            return

        view_rect = self.viewport().rect()
        ruler_height = self._ruler_height

        painter.save()
        # Top horizontal ruler
        painter.resetTransform()
        painter.fillRect(view_rect.left(), 0, view_rect.width(), ruler_height, QtGui.QColor(245, 245, 245))
        pen = QtGui.QPen(QtGui.QColor(120, 120, 120))
        painter.setPen(pen)
        painter.drawLine(view_rect.left(), ruler_height - 1, view_rect.right(), ruler_height - 1)

        # Choose tick step based on current zoom
        scale_x = self.transform().m11() if not self.transform().isScaling() else self.transform().m11()
        if scale_x == 0:
            painter.restore()
            return
        desired_px = 60
        unit = desired_px / abs(scale_x)
        candidates = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]
        step = min(candidates, key=lambda c: abs(c - unit))

        visible_scene = self.mapToScene(view_rect).boundingRect()
        start_x = int(max(0, visible_scene.left()) // step * step)
        end_x = int(min(self._image_width, visible_scene.right()))
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)

        for x in range(start_x, int(end_x) + step, step):
            pos = self.mapFromScene(QtCore.QPointF(x, 0)).x()
            if pos < view_rect.left() - 20 or pos > view_rect.right() + 20:
                continue
            is_major = (x % (step * 2) == 0)
            tick_len = 10 if is_major else 6
            painter.drawLine(int(pos), ruler_height - tick_len, int(pos), ruler_height - 2)
            if is_major:
                painter.drawText(int(pos) + 2, ruler_height - 12, f"{x}")

        painter.restore()

        # Preview guide while dragging from ruler
        if self._ruler_preview_y is not None:
            painter.save()
            pen = QtGui.QPen(QtGui.QColor(42, 140, 255, 140), 1.5, QtCore.Qt.DashLine)
            painter.setPen(pen)
            painter.drawLine(0, self._ruler_preview_y, self._image_width, self._ruler_preview_y)
            painter.restore()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
