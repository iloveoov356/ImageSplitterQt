from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict

from PySide6 import QtCore

LANGUAGES: Dict[str, str] = {
    "en": "English",
    "zh": "简体中文",
}


class I18n(QtCore.QObject):
    language_changed = QtCore.Signal(str)

    def __init__(self, language: str = "en") -> None:
        super().__init__()
        self._language = language if language in LANGUAGES else "en"
        self._strings = self._load_all_locales()

    @property
    def language(self) -> str:
        return self._language

    def set_language(self, language: str) -> None:
        if language not in LANGUAGES:
            return
        if language == self._language:
            return
        self._language = language
        self.language_changed.emit(language)

    def tr(self, key: str, **kwargs) -> str:
        template = self._strings.get(self._language, {}).get(key) or self._strings.get("en", {}).get(key) or key
        try:
            return template.format(**kwargs)
        except Exception:
            return template

    def _load_all_locales(self) -> Dict[str, Dict[str, str]]:
        # Support both source layout (src/i18n/locales) and PyInstaller bundle where
        # datas may land under _MEIPASS/i18n/locales or _MEIPASS/locales.
        candidates = [
            Path(__file__).resolve().parent / "locales",
            Path(getattr(sys, "_MEIPASS", "")) / "i18n" / "locales",
            Path(getattr(sys, "_MEIPASS", "")) / "locales",
        ]

        strings: Dict[str, Dict[str, str]] = {}
        for code in LANGUAGES:
            for base in candidates:
                file_path = base / f"{code}.json"
                try:
                    if file_path.exists():
                        with file_path.open("r", encoding="utf-8") as f:
                            strings[code] = json.load(f)
                        break
                except Exception:
                    strings.setdefault(code, {})
        return strings
