import logging
from pathlib import Path
from typing import Callable, Iterable, List

from PySide6 import QtCore, QtGui

from .models import ExportFormat, ExportResult, GuideLine
from .utils import ensure_directory

_LOG = logging.getLogger(__name__)


def export_image_segments(
    image: QtGui.QImage,
    lines: Iterable[GuideLine],
    output_dir: str,
    export_format: ExportFormat,
    jpeg_quality: int,
    original_suffix: str,
    tr: Callable[[str], str] = lambda x, **kwargs: x,
) -> ExportResult:
    errors: List[str] = []
    skipped: List[str] = []
    written: List[str] = []

    err = ensure_directory(output_dir)
    if err:
        errors.append(err)
        return ExportResult(written, skipped, errors)

    height = image.height()
    width = image.width()
    boundaries = [0] + [int(round(line.y)) for line in sorted(lines, key=lambda l: l.y)] + [height]
    # dedupe and clamp boundaries
    clean_boundaries: List[int] = []
    for b in boundaries:
        b = max(0, min(height, b))
        if clean_boundaries and b == clean_boundaries[-1]:
            continue
        clean_boundaries.append(b)

    segment_candidates = [(clean_boundaries[i], clean_boundaries[i + 1]) for i in range(len(clean_boundaries) - 1)]
    valid_segments = [(start, end) for start, end in segment_candidates if end - start > 0]
    pad_width = max(3, len(str(len(valid_segments) or 1)))

    ext = _resolve_extension(export_format, original_suffix)
    qt_format = _resolve_qt_format(export_format, original_suffix)

    index = 1
    for start, end in valid_segments:
        rect = QtCore.QRect(0, start, width, end - start)
        cropped = image.copy(rect)
        filename = f"{index:0{pad_width}d}.{ext}"
        output_path = Path(output_dir) / filename
        ok = cropped.save(str(output_path), qt_format, quality=jpeg_quality if qt_format == "JPEG" else -1)
        if ok:
            written.append(str(output_path))
        else:
            errors.append(tr("error.save_failed", path=str(output_path)))
        index += 1

    # mark skipped segments with zero or negative height
    skipped = [f"{s}-{e}" for s, e in segment_candidates if e - s <= 0]
    return ExportResult(written, skipped, errors)


def _resolve_extension(export_format: ExportFormat, original_suffix: str) -> str:
    if export_format == ExportFormat.KEEP:
        suffix = original_suffix.lower().lstrip(".") or "png"
        return suffix
    if export_format == ExportFormat.PNG:
        return "png"
    if export_format == ExportFormat.JPEG:
        return "jpg"
    return "png"


def _resolve_qt_format(export_format: ExportFormat, original_suffix: str) -> str:
    if export_format == ExportFormat.KEEP:
        suffix = original_suffix.lower().lstrip(".")
        if suffix in {"jpg", "jpeg"}:
            return "JPEG"
        if suffix == "png":
            return "PNG"
        return suffix.upper() if suffix else "PNG"
    if export_format == ExportFormat.PNG:
        return "PNG"
    if export_format == ExportFormat.JPEG:
        return "JPEG"
    return "PNG"
