from mcsm_tools.terminal import apply_player_events


def test_list_output_replaces_player_set():
    players = {"stale"}
    changed = apply_player_events(
        "There are 2 of a max of 20 players online: §aAlice, Bob", players)

    assert changed
    assert players == {"Alice", "Bob"}


def test_join_and_leave_update_players():
    players = set()
    assert apply_player_events("Alice joined the game", players)
    assert players == {"Alice"}

    assert apply_player_events("Alice left the game", players)
    assert players == set()


def test_unrelated_output_does_not_change_players():
    players = {"Alice"}
    assert apply_player_events("[Server thread/INFO]: Saving worlds", players) is False
    assert players == {"Alice"}


def test_empty_player_list_is_handled():
    players = {"Alice"}
    apply_player_events("There are 0 of a max of 20 players online: ", players)
    assert players == set()
