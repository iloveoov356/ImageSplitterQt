import logging
from pathlib import Path
from typing import Optional

from PySide6 import QtGui

_LOG = logging.getLogger(__name__)


def load_image(path: str) -> Optional[QtGui.QImage]:
    image_path = Path(path)
    if not image_path.exists():
        _LOG.error("Image not found: %s", path)
        return None
    image = QtGui.QImage(str(image_path))
    if image.isNull():
        _LOG.error("Unsupported image: %s", path)
        return None
    return image
