from mcsm_tools.command_history import MAX_HISTORY, CommandHistory


def test_history_persists_between_instances(isolated_home):
    history = CommandHistory()
    history.add("say hi")
    history.add("list")

    assert CommandHistory().get_recent() == ["say hi", "list"]


def test_repeated_command_is_not_duplicated(isolated_home):
    history = CommandHistory()
    history.add("list")
    history.add("list")

    assert history.get_recent() == ["list"]


def test_blank_command_is_ignored(isolated_home):
    history = CommandHistory()
    history.add("   ")

    assert history.get_recent() == []


def test_navigation_walks_backwards_then_forwards(isolated_home):
    history = CommandHistory()
    history.add("one")
    history.add("two")

    assert history.prev() == "two"
    assert history.prev() == "one"
    assert history.next() == "two"
    assert history.next() is None


def test_history_is_capped(isolated_home):
    history = CommandHistory()
    for i in range(MAX_HISTORY + 10):
        history.add(f"cmd{i}")

    reloaded = CommandHistory()
    assert len(reloaded.get_recent(MAX_HISTORY + 50)) == MAX_HISTORY
    assert reloaded.get_recent(1) == [f"cmd{MAX_HISTORY + 9}"]


def test_favorites_roundtrip(isolated_home):
    history = CommandHistory()
    history.add_favorite("say hello", "greet")
    history.add_favorite("say hello")

    assert [f["cmd"] for f in CommandHistory().favorites] == ["say hello"]

    history.remove_favorite("say hello")
    assert CommandHistory().favorites == []


def test_search_is_case_insensitive_and_newest_first(isolated_home):
    history = CommandHistory()
    history.add("Say one")
    history.add("say two")

    assert history.search("SAY") == ["say two", "Say one"]


def test_corrupt_history_file_is_ignored(isolated_home):
    isolated_home.mkdir(parents=True, exist_ok=True)
    (isolated_home / "command_history.json").write_text("{oops", encoding="utf-8")

    assert CommandHistory().get_recent() == []
