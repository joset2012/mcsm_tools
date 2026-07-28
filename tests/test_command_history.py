import json

import pytest

from mcsm_tools import command_history as history_mod
from mcsm_tools.command_history import CommandHistory


@pytest.fixture
def history_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(history_mod, "HISTORY_DIR", str(tmp_path))
    monkeypatch.setattr(history_mod, "HISTORY_FILE", str(tmp_path / "command_history.json"))
    monkeypatch.setattr(history_mod, "FAVORITES_FILE", str(tmp_path / "command_favorites.json"))
    return tmp_path


def test_add_persists_across_instances(history_dir):
    history = CommandHistory()
    history.add("list")
    history.add("  say hi  ")

    assert CommandHistory().get_recent() == ["list", "say hi"]


def test_add_ignores_blank_and_deduplicates_consecutive(history_dir):
    history = CommandHistory()
    history.add("   ")
    history.add("stop")
    history.add("stop")

    assert history.get_recent() == ["stop"]


def test_get_recent_limits_count(history_dir):
    history = CommandHistory()
    for i in range(5):
        history.add(f"cmd{i}")

    assert history.get_recent(2) == ["cmd3", "cmd4"]


def test_save_truncates_to_max_history(history_dir, monkeypatch):
    monkeypatch.setattr(history_mod, "MAX_HISTORY", 3)
    history = CommandHistory()
    for i in range(5):
        history.add(f"cmd{i}")

    stored = json.loads((history_dir / "command_history.json").read_text(encoding="utf-8"))
    assert [entry["cmd"] for entry in stored] == ["cmd2", "cmd3", "cmd4"]


def test_prev_and_next_walk_the_history(history_dir):
    history = CommandHistory()
    for cmd in ("a", "b", "c"):
        history.add(cmd)

    assert history.prev() == "c"
    assert history.prev() == "b"
    assert history.prev() == "a"
    assert history.prev() == "a"
    assert history.next() == "b"
    assert history.next() == "c"
    assert history.next() is None


def test_prev_returns_none_when_empty(history_dir):
    assert CommandHistory().prev() is None


def test_reset_pos_returns_to_end(history_dir):
    history = CommandHistory()
    history.add("a")
    history.add("b")
    history.prev()
    history.reset_pos()

    assert history.prev() == "b"


def test_search_is_case_insensitive_and_newest_first(history_dir):
    history = CommandHistory()
    history.add("say hello")
    history.add("list")
    history.add("Say bye")

    assert history.search("say") == ["Say bye", "say hello"]
    assert history.search("nope") == []


def test_favorites_add_dedupe_remove(history_dir):
    history = CommandHistory()
    history.add_favorite("  ")
    history.add_favorite("op devin", "grant op")
    history.add_favorite("op devin", "duplicate")

    favorites = history.favorites
    assert [f["cmd"] for f in favorites] == ["op devin"]
    assert favorites[0]["label"] == "grant op"

    assert CommandHistory().favorites[0]["cmd"] == "op devin"

    history.remove_favorite("op devin")
    assert history.favorites == []


def test_favorite_label_defaults_to_command(history_dir):
    history = CommandHistory()
    history.add_favorite("stop")

    assert history.favorites[0]["label"] == "stop"


def test_corrupt_files_are_ignored(history_dir):
    (history_dir / "command_history.json").write_text("{not json", encoding="utf-8")
    (history_dir / "command_favorites.json").write_text('{"cmd": "x"}', encoding="utf-8")

    history = CommandHistory()
    assert history.get_recent() == []
    assert history.favorites == []
