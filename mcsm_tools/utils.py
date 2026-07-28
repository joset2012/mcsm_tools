"""Shared helpers used across the API client, CLI and GUI front-ends."""

import json
import os
from datetime import datetime

APP_DIR_NAME = ".mcsm_tools"

DATETIME_FMT = "%Y-%m-%d %H:%M"
DATETIME_SEC_FMT = "%Y-%m-%d %H:%M:%S"
FILENAME_STAMP_FMT = "%Y%m%d_%H%M%S"

_SIZE_UNITS = ["B", "KB", "MB", "GB"]


def app_data_dir(*parts: str, create: bool = True) -> str:
    """Return a path inside the per-user application directory (~/.mcsm_tools)."""
    path = os.path.join(os.path.expanduser("~"), APP_DIR_NAME, *parts)
    if create:
        os.makedirs(path, exist_ok=True)
    return path


def format_size(size) -> str:
    """Format a byte count as a human readable string."""
    size = float(size or 0)
    for unit in _SIZE_UNITS:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def format_time(timestamp: float, fmt: str = DATETIME_FMT) -> str:
    """Format an epoch timestamp expressed in seconds."""
    return datetime.fromtimestamp(timestamp).strftime(fmt)


def format_timestamp(ts, fmt: str = DATETIME_FMT) -> str:
    """Format a timestamp of unknown shape (seconds, milliseconds or string)."""
    if not ts:
        return "-"
    if isinstance(ts, (int, float)):
        return format_time(ts / 1000 if ts > 1e10 else ts, fmt)
    if isinstance(ts, str):
        return ts[:19].replace("GMT", "").strip()
    return "-"


def filename_timestamp() -> str:
    """Current time as a filename-safe stamp, e.g. 20240131_235959."""
    return datetime.now().strftime(FILENAME_STAMP_FMT)


def read_json(path: str, default=None):
    """Read JSON from a file, returning ``default`` on any failure."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def write_json(path: str, data, indent: int | None = None) -> bool:
    """Write JSON to a file, returning whether it succeeded."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
        return True
    except Exception:
        return False


def to_http_url(addr: str) -> str:
    """Normalize a daemon stream address (``wss://host``/``host``) to an http URL."""
    url = addr.replace("wss://", "https://").replace("ws://", "http://")
    if not url.startswith("http"):
        url = f"https://{url}"
    return url.rstrip("/")
