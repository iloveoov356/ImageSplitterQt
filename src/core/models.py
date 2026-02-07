from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List


class SnapMode(str, Enum):
    OFF = "off"
    PIXEL = "pixel"
    GRID = "grid"


class ExportFormat(str, Enum):
    PNG = "png"
    JPEG = "jpeg"
    KEEP = "keep"


@dataclass
class GuideLine:
    id: str
    y: float
    locked: bool = False
    kind: str = "horizontal"


@dataclass
class ExportResult:
    written: List[str]
    skipped: List[str]
    errors: List[str]

    @property
    def success(self) -> bool:
        return not self.errors

    @property
    def summary(self) -> str:
        parts = []
        if self.written:
            parts.append(f"saved {len(self.written)} slice(s)")
        if self.skipped:
            parts.append(f"skipped {len(self.skipped)} slice(s)")
        if self.errors:
            parts.append(f"errors: {len(self.errors)}")
        return ", ".join(parts) if parts else "no work done"
