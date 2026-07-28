import sys
from unittest.mock import MagicMock

import pytest


def _stub_gui_modules():
    """Allow importing GUI modules for their pure helpers on headless installs."""
    for name in ("tkinter", "tkinter.ttk", "tkinter.messagebox",
                 "tkinter.filedialog", "tkinter.simpledialog"):
        try:
            __import__(name)
        except ImportError:
            sys.modules[name] = MagicMock(name=name)


_stub_gui_modules()


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    """Run a test in an empty directory (config/credentials are cwd-relative)."""
    monkeypatch.chdir(tmp_path)
    return tmp_path
