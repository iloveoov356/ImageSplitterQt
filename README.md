# ImageSplitterQt

Desktop GUI to split an image into slices using horizontal guide lines. Built with Python and PySide6.

## Features
- Open images via button or drag-and-drop.
- Add, drag, lock/unlock, delete horizontal guides; snap modes: Off / Pixel / Grid (configurable).
- Undo/redo for add, move, delete, lock operations.
- Zoom and pan canvas; coordinates shown in status bar.
- Top ruler with zoom-aware ticks; drag from the ruler downward to create a new horizontal guide.
- Precise edits via guide list (editable Y, lock toggle).
- One-click clear all guides; close current image.
- Export slices between guides to PNG/JPEG/Keep-original; JPEG quality control; files named 001, 002, ...
- User settings persisted (directories, snap, format, quality, window layout).
- Language toggle: menu `Language` → English / 简体中文 (persists next launch).
- Translations stored in JSON files (`src/i18n/locales/en.json`, `zh.json`) for easy editing/extension.

## Quick start
1. Install Python 3.11+.
2. Create env and install deps:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
   pip install -r requirements.txt
   ```
3. Run:
   ```bash
   python main.py
   ```

## Shortcuts
- Open: Ctrl+O
- Undo / Redo: Ctrl+Z / Ctrl+Y (or Ctrl+Shift+Z)
- Delete selected guide: Delete
- Pan: Middle mouse drag
- Zoom: Mouse wheel

## Project layout
```
.
├─ main.py                # app entrypoint
├─ image_splitter.spec    # PyInstaller spec
├─ requirements.txt
├─ README.md
├─ src/
│  ├─ core/
│  │  ├─ commands.py      # command stack & concrete commands
│  │  ├─ controller.py    # guide + image state, signals, undo/redo
│  │  ├─ exporter.py      # slicing/export logic
│  │  ├─ image_loader.py  # safe image loading
│  │  ├─ models.py        # dataclasses/enums
│  │  ├─ settings.py      # QSettings wrapper
│  │  └─ utils.py         # logging, snapping, helpers
│  └─ ui/
│     ├─ canvas.py        # graphics view, drag/drop, line items
│     ├─ line_list.py     # editable table of guides
│     └─ main_window.py   # wiring, panels, status bar
└─ .github/workflows/build.yml
```

## Architecture notes
- `GuideController` owns image, guides, snap mode, command stack; emits signals consumed by the UI.
- Commands implement add/move/delete/lock with undo/redo via `CommandStack`.
- Canvas uses `QGraphicsView` + custom `GuideLineItem` for precise y-only dragging; snapping applied in controller to keep math in image space.
- Exporter builds boundaries `[0, lines..., image_height]`, skips zero-height slices, saves sequential files with zero padding.
- Settings use `QSettings` to remember recent directories, snap/grid, export format, JPEG quality, and window layout.

## Packaging (PyInstaller)
Recommended one-folder builds. Use the spec to include PySide6 hooks.
- Windows (one-folder):
  ```bash
  pyinstaller --clean --noconfirm image_splitter.spec
  # artifact in dist/ImageSplitterQt/
  ```
- macOS (.app inside dist):
  ```bash
  pyinstaller --clean --noconfirm image_splitter.spec
  # dist/ImageSplitterQt/ImageSplitterQt.app
  ```
Notes:
- Run the app from inside the dist folder (Windows: double-click ImageSplitterQt.exe; macOS: open the .app). Gatekeeper may block unsigned apps; allow via System Settings > Privacy & Security.
- If file dialogs fail after packaging, ensure Qt platform plugins are present (PyInstaller should collect them via hooks).

## GitHub Actions CI
Workflow: [.github/workflows/build.yml](.github/workflows/build.yml)
- Triggers: push to main, pull_request, tags `v*`, manual.
- Matrix: windows-latest, macos-latest.
- Steps: install deps, `python -m compileall src`, `pyinstaller --clean --noconfirm image_splitter.spec`, zip dist output, upload artifact.
- Artifacts: `ImageSplitterQt-windows-x64.zip` or `ImageSplitterQt-macos-universal.zip` (download from Actions run summary).

## Usage tips
- Guides snap to the chosen mode; grid size default 10px.
- Duplicate y positions are rejected; guides clamp to `[0, image_height]`.
- Export format `Keep original` uses the source file extension; JPEG quality slider only affects JPEG.
- Invalid slices (height <= 0) are skipped and reported.

## Extensibility
The model and exporter are ready for additional guide types (vertical/grid). Add new guide kinds in `models.py`, extend canvas drawing, and update exporter to split in two axes.
