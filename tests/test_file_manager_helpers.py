import pytest

from mcsm_tools.file_manager import (
    ICON_DIR,
    _display_name,
    _ext,
    _get_file_icon,
    _get_name,
    _is_dir,
    _join_path,
    _parent_path,
    _strip_icon,
)


@pytest.mark.parametrize(
    "name, expected",
    [("server.properties", "properties"), ("archive.tar.gz", "gz"), ("Makefile", ""), (".env", "env")],
)
def test_ext(name, expected):
    assert _ext(name) == expected


@pytest.mark.parametrize(
    "name, icon",
    [
        ("plugin.jar", "📦"),
        ("MAIN.PY", "🐍"),
        ("latest.log", "📜"),
        ("Dockerfile", "🐳"),
        ("README.md", "📖"),
        ("unknown.xyz", "📄"),
        ("noextension", "📄"),
    ],
)
def test_get_file_icon(name, icon):
    assert _get_file_icon(name) == icon


def test_display_name():
    assert _display_name("logs", is_dir=True) == f"{ICON_DIR} logs"
    assert _display_name("..") == f"{ICON_DIR} .."
    assert _display_name("app.py") == "🐍 app.py"


@pytest.mark.parametrize("name, is_dir", [("logs", True), ("..", False), ("app.py", False), ("Dockerfile", False)])
def test_strip_icon_reverses_display_name(name, is_dir):
    assert _strip_icon(_display_name(name, is_dir)) == name


def test_strip_icon_passes_through_plain_text():
    assert _strip_icon("plain.txt") == "plain.txt"


@pytest.mark.parametrize(
    "item, expected",
    [
        ({"isFile": False}, True),
        ({"isFile": True}, False),
        ({"type": 0}, True),
        ({"type": 1}, False),
        ({"type": "directory"}, True),
        ({"type": "file"}, False),
        ({}, False),
    ],
)
def test_is_dir(item, expected):
    assert _is_dir(item) is expected


def test_get_name_defaults_to_placeholder():
    assert _get_name({"name": "a.txt"}) == "a.txt"
    assert _get_name({}) == "?"


@pytest.mark.parametrize(
    "parent, child, expected",
    [("/", "a", "/a"), ("/logs", "a.log", "/logs/a.log"), ("/logs/", "a.log", "/logs/a.log")],
)
def test_join_path(parent, child, expected):
    assert _join_path(parent, child) == expected


@pytest.mark.parametrize(
    "path, expected",
    [("/logs/a.log", "/logs"), ("/logs/", "/"), ("/logs", "/"), ("/", "/"), ("", "/")],
)
def test_parent_path(path, expected):
    assert _parent_path(path) == expected
