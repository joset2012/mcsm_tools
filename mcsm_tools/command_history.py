import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

from .config import config_dir

MAX_HISTORY = 500


def _history_dir() -> Path:
    return config_dir()


def _history_file() -> Path:
    return _history_dir() / "command_history.json"


def _favorites_file() -> Path:
    return _history_dir() / "command_favorites.json"


def _read_list(path: Path) -> list[dict]:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, OSError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict) and "cmd" in item]


def _write_list(path: Path, items: list[dict]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False)
            os.replace(tmp_name, path)
        except BaseException:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise
    except OSError:
        pass


class CommandHistory:
    def __init__(self):
        self._history: list[dict] = _read_list(_history_file())[-MAX_HISTORY:]
        self._favorites: list[dict] = _read_list(_favorites_file())
        self._pos = len(self._history)

    def _save(self):
        del self._history[:-MAX_HISTORY]
        _write_list(_history_file(), self._history)
        _write_list(_favorites_file(), self._favorites)

    def add(self, command: str):
        cmd = command.strip()
        if not cmd:
            return
        if self._history and self._history[-1]["cmd"] == cmd:
            self._history[-1]["time"] = datetime.now().isoformat()
        else:
            self._history.append({"cmd": cmd, "time": datetime.now().isoformat()})
        self._save()
        self._pos = len(self._history)

    def prev(self) -> str | None:
        if not self._history:
            return None
        if self._pos > 0:
            self._pos -= 1
        return self._history[self._pos]["cmd"] if 0 <= self._pos < len(self._history) else None

    def next(self) -> str | None:
        if self._pos < len(self._history) - 1:
            self._pos += 1
            return self._history[self._pos]["cmd"]
        self._pos = len(self._history)
        return None

    def reset_pos(self):
        self._pos = len(self._history)

    def search(self, query: str) -> list[str]:
        q = query.lower()
        return [h["cmd"] for h in reversed(self._history) if q in h["cmd"].lower()]

    def get_recent(self, count: int = 20) -> list[str]:
        return [h["cmd"] for h in self._history[-count:]]

    def add_favorite(self, command: str, label: str = ""):
        cmd = command.strip()
        if not cmd:
            return
        if cmd in (f["cmd"] for f in self._favorites):
            return
        self._favorites.append({"cmd": cmd, "label": label or cmd, "time": datetime.now().isoformat()})
        self._save()

    def remove_favorite(self, command: str):
        self._favorites = [f for f in self._favorites if f["cmd"] != command]
        self._save()

    @property
    def favorites(self) -> list[dict]:
        return list(self._favorites)
