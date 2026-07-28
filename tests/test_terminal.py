import pytest

from mcsm_tools.terminal import PLAYER_PATTERNS, MCSMTerminal


class FakeSio:
    """Minimal socketio.Client stand-in that captures handlers and emits."""

    def __init__(self, *args, **kwargs):
        self.handlers = {}
        self.emitted = []
        self.connect_calls = []
        self.disconnected = False
        self.waited = False

    def event(self, func):
        self.handlers[func.__name__] = func
        return func

    def on(self, name):
        def decorator(func):
            self.handlers[name] = func
            return func
        return decorator

    def emit(self, event, data=None):
        self.emitted.append((event, data))

    def connect(self, url, transports=None, headers=None):
        self.connect_calls.append({"url": url, "transports": transports, "headers": headers})

    def disconnect(self):
        self.disconnected = True

    def wait(self):
        self.waited = True


@pytest.fixture
def terminal(monkeypatch):
    monkeypatch.setattr("mcsm_tools.terminal.socketio.Client", FakeSio)
    return MCSMTerminal()


def stdout(terminal, text):
    terminal.sio.handlers["instance/stdout"]({"data": {"text": text}})


def test_connect_success_builds_ws_url(terminal):
    assert terminal.connect("wss://node/socket", "pw", "https://panel.example.com") is True
    call = terminal.sio.connect_calls[0]
    assert call["url"] == "wss://node/socket?password=pw"
    assert call["transports"] == ["websocket"]
    assert call["headers"]["Origin"] == "https://panel.example.com"


def test_connect_failure_is_reported(terminal, monkeypatch):
    monkeypatch.setattr(terminal.sio, "connect", lambda *a, **k: (_ for _ in ()).throw(OSError("down")))
    assert terminal.connect("wss://node", "pw", "https://panel.example.com") is False
    assert terminal.is_connected is False


def test_connect_handler_authenticates_and_primes_state(terminal):
    events = []
    terminal.on_connect = lambda: events.append("connected")
    terminal._password = "pw"

    terminal.sio.handlers["connect"]()

    assert terminal.is_connected is True
    assert events == ["connected"]
    assert terminal.sio.emitted[0] == ("stream/auth", {"data": {"password": "pw"}})
    assert ("stream/input", {"data": {"command": "list"}}) in terminal.sio.emitted


def test_disconnect_handler_and_method(terminal):
    events = []
    terminal.on_disconnect = lambda: events.append("bye")

    terminal.sio.handlers["connect"]()
    terminal.sio.handlers["disconnect"]()

    assert terminal.is_connected is False
    assert events == ["bye"]

    terminal.disconnect()
    assert terminal.sio.disconnected is False

    terminal.sio.handlers["connect"]()
    terminal.disconnect()
    assert terminal.sio.disconnected is True
    assert terminal.is_connected is False


def test_commands_only_sent_while_connected(terminal):
    terminal.send_command("stop")
    terminal.send_raw("stream/resize", {"data": {"w": 1, "h": 2}})
    terminal.wait()
    assert terminal.sio.emitted == []
    assert terminal.sio.waited is False

    terminal.sio.handlers["connect"]()
    terminal.sio.emitted.clear()
    terminal.send_command("stop")
    terminal.send_raw("stream/resize", {"data": {"w": 1, "h": 2}})
    terminal.wait()

    assert terminal.sio.emitted == [
        ("stream/input", {"data": {"command": "stop"}}),
        ("stream/resize", {"data": {"w": 1, "h": 2}}),
    ]
    assert terminal.sio.waited is True


def test_stdout_forwards_plain_output(terminal):
    lines = []
    terminal.on_output = lines.append

    stdout(terminal, "[Server] Done (1.2s)!")
    stdout(terminal, "")

    assert lines == ["[Server] Done (1.2s)!"]


def test_player_list_output_replaces_online_players(terminal):
    updates = []
    terminal.on_players_update = lambda players: updates.append(set(players))
    terminal.online_players = {"stale"}

    stdout(terminal, "There are 2 of a max of 20 players online: §aAlice, Bob")

    assert terminal.online_players == {"Alice", "Bob"}
    assert updates == [{"Alice", "Bob"}]


def test_join_and_leave_update_online_players(terminal):
    stdout(terminal, "Alice joined the game")
    stdout(terminal, "Bob joined the game")
    assert terminal.online_players == {"Alice", "Bob"}

    stdout(terminal, "Alice left the game")
    assert terminal.online_players == {"Bob"}

    stdout(terminal, "Carol left the game")
    assert terminal.online_players == {"Bob"}


def test_player_patterns_ignore_unrelated_lines():
    assert PLAYER_PATTERNS["join"].search("Alice joined the server") is None
    assert PLAYER_PATTERNS["list"].search("There are no players") is None
