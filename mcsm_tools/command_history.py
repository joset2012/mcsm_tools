import json
import os
from datetime import datetime


HISTORY_DIR = os.path.expanduser(os.path.join("~", ".mcsm_tools"))
HISTORY_FILE = os.path.join(HISTORY_DIR, "command_history.json")
FAVORITES_FILE = os.path.join(HISTORY_DIR, "command_favorites.json")
MAX_HISTORY = 500


def _ensure_dir():
    os.makedirs(HISTORY_DIR, exist_ok=True)


class CommandHistory:
    def __init__(self):
        _ensure_dir()
        self._history: list[dict] = []
        self._favorites: list[dict] = []
        self._pos = -1
        self._load()

    def _load(self):
        try:
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._history = data if isinstance(data, list) else []
        except Exception:
            self._history = []
        try:
            if os.path.exists(FAVORITES_FILE):
                with open(FAVORITES_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._favorites = data if isinstance(data, list) else []
        except Exception:
            self._favorites = []

    def _save(self):
        _ensure_dir()
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self._history[-MAX_HISTORY:], f, ensure_ascii=False)
        except Exception:
            pass
        try:
            with open(FAVORITES_FILE, "w", encoding="utf-8") as f:
                json.dump(self._favorites, f, ensure_ascii=False)
        except Exception:
            pass

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
