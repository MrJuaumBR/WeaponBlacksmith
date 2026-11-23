"""Small, versioned JSON save repository for the example game."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any

if __package__:
    from .domain import GameError, GameState
else:
    from domain import GameError, GameState


class SaveCorruptionError(RuntimeError):
    """A present save could not be decoded or failed domain validation."""


class JsonSaveRepository:
    """Persist a complete roster using write-then-replace semantics."""

    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser()

    def load(self) -> GameState:
        if not self.path.exists():
            return GameState()
        try:
            raw: Any = json.loads(self.path.read_text(encoding="utf-8"))
            return GameState.from_dict(raw)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError, GameError, TypeError, ValueError) as exc:
            raise SaveCorruptionError(
                f"Could not load save file {self.path}: {exc}. Keep a copy before replacing it."
            ) from exc

    def save(self, state: GameState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(state.to_dict(), indent=2, ensure_ascii=False) + "\n"
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=self.path.parent,
                prefix=f".{self.path.name}.", suffix=".tmp", delete=False
            ) as temporary:
                temp_path = Path(temporary.name)
                temporary.write(payload)
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temp_path, self.path)
        except OSError:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
            raise
