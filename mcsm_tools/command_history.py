import os
from datetime import datetime

from .utils import app_data_dir, read_json, write_json


HISTORY_DIR = app_data_dir(create=False)
HISTORY_FILE = os.path.join(HISTORY_DIR, "command_history.json")
FAVORITES_FILE = os.path.join(HISTORY_DIR, "command_favorites.json")
MAX_HISTORY = 500


def _ensure_dir():
    app_data_dir()


class CommandHistory:
    def __init__(self):
        _ensure_dir()
        self._history: list[dict] = []
        self._favorites: list[dict] = []
        self._pos = -1
        self._load()

    def _load(self):
        history = read_json(HISTORY_FILE, [])
        self._history = history if isinstance(history, list) else []
        favorites = read_json(FAVORITES_FILE, [])
        self._favorites = favorites if isinstance(favorites, list) else []

    def _save(self):
        _ensure_dir()
        write_json(HISTORY_FILE, self._history[-MAX_HISTORY:])
        write_json(FAVORITES_FILE, self._favorites)

    def add(self, command: str):
        cmd = command.strip()
        if not cmd:
            return
        if self._history and self._history[-1]["cmd"] == cmd:
            self._history[-1]["time"] = datetime.now().isoformat()
            self._save()
            return
        self._history.append({"cmd": cmd, "time": datetime.now().isoformat()})
        self._pos = len(self._history)
        self._save()

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
