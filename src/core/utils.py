import logging
import sys
from pathlib import Path
from typing import Optional

from .models import SnapMode


def setup_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    )


def resource_path(relative_path: str) -> str:
    base_path = getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)
    return str(Path(base_path).joinpath(relative_path))


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def apply_snap(y: float, snap_mode: SnapMode, grid_size: int) -> float:
    if snap_mode == SnapMode.OFF:
        return y
    if snap_mode == SnapMode.PIXEL:
        return round(y)
    if snap_mode == SnapMode.GRID and grid_size > 0:
        return round(y / grid_size) * grid_size
    return y


def ensure_directory(path: str) -> Optional[str]:
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return None
    except OSError as exc:
        logging.exception("Failed to create directory %s", path)
        return str(exc)
