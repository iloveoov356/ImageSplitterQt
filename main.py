import logging
import sys
from pathlib import Path

from PySide6 import QtCore, QtWidgets

from src.core.utils import setup_logging
from src.i18n.locale import I18n
from src.ui.main_window import MainWindow


def main() -> int:
    # Enable crisp rendering on high DPI displays
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    setup_logging()

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("ImageSplitterQt")
    app.setOrganizationName("ImageSplitter")
    app.setOrganizationDomain("imagesplitter.local")

    i18n = I18n()
    window = MainWindow(i18n)
    window.show()

    exit_code = app.exec()
    logging.shutdown()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
