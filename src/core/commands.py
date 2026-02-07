from __future__ import annotations

from typing import List, TYPE_CHECKING

from .models import GuideLine

if TYPE_CHECKING:
    from .controller import GuideController


class BaseCommand:
    def __init__(self, description: str) -> None:
        self.description = description

    def do(self) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def undo(self) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class CommandStack:
    def __init__(self) -> None:
        self._stack: List[BaseCommand] = []
        self._index: int = -1

    @property
    def can_undo(self) -> bool:
        return self._index >= 0

    @property
    def can_redo(self) -> bool:
        return self._index + 1 < len(self._stack)

    def push_and_execute(self, command: BaseCommand) -> None:
        # drop redoable commands
        if self._index + 1 < len(self._stack):
            self._stack = self._stack[: self._index + 1]
        self._stack.append(command)
        self._index += 1
        command.do()

    def undo(self) -> None:
        if not self.can_undo:
            return
        self._stack[self._index].undo()
        self._index -= 1

    def redo(self) -> None:
        if not self.can_redo:
            return
        self._index += 1
        self._stack[self._index].do()


class AddLineCommand(BaseCommand):
    def __init__(self, controller: "GuideController", line: GuideLine) -> None:
        super().__init__("Add line")
        self.controller = controller
        self.line = line

    def do(self) -> None:
        self.controller._add_line(self.line)

    def undo(self) -> None:
        self.controller._remove_line(self.line.id)


class DeleteLineCommand(BaseCommand):
    def __init__(self, controller: "GuideController", line: GuideLine) -> None:
        super().__init__("Delete line")
        self.controller = controller
        self.line = line

    def do(self) -> None:
        self.controller._remove_line(self.line.id)

    def undo(self) -> None:
        self.controller._add_line(self.line)


class MoveLineCommand(BaseCommand):
    def __init__(self, controller: "GuideController", line_id: str, old_y: float, new_y: float) -> None:
        super().__init__("Move line")
        self.controller = controller
        self.line_id = line_id
        self.old_y = old_y
        self.new_y = new_y

    def do(self) -> None:
        self.controller._move_line(self.line_id, self.new_y)

    def undo(self) -> None:
        self.controller._move_line(self.line_id, self.old_y)


class LockLineCommand(BaseCommand):
    def __init__(self, controller: "GuideController", line_id: str, locked: bool) -> None:
        super().__init__("Toggle lock")
        self.controller = controller
        self.line_id = line_id
        self.locked = locked

    def do(self) -> None:
        self.controller._set_locked(self.line_id, self.locked)

    def undo(self) -> None:
        self.controller._set_locked(self.line_id, not self.locked)


class ClearLinesCommand(BaseCommand):
    def __init__(self, controller: "GuideController", previous: List[GuideLine]) -> None:
        super().__init__("Clear lines")
        self.controller = controller
        self.previous = previous

    def do(self) -> None:
        self.controller._set_all_lines([])

    def undo(self) -> None:
        self.controller._set_all_lines(self.previous)
