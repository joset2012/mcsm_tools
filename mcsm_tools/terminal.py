import re
from collections.abc import Callable
from urllib.parse import urlencode

import socketio


PLAYER_PATTERNS = {
    'list': re.compile(r'There are \d+ of a max of \d+ players online:\s*(.+)', re.IGNORECASE),
    'join': re.compile(r'(\w+) joined the game'),
    'leave': re.compile(r'(\w+) left the game'),
}

COLOR_CODE = re.compile(r'§[0-9a-fklmnor]')


def apply_player_events(text: str, players: set[str]) -> bool:
    """Update `players` from a server output line; True when it changed."""
    match = PLAYER_PATTERNS['list'].search(text)
    if match:
        names = (COLOR_CODE.sub('', name).strip() for name in match.group(1).split(', '))
        players.clear()
        players.update(name for name in names if name)
        return True

    match = PLAYER_PATTERNS['join'].search(text)
    if match:
        players.add(match.group(1))
        return True

    match = PLAYER_PATTERNS['leave'].search(text)
    if match:
        players.discard(match.group(1))
        return True

    return False


class MCSMTerminal:
    def __init__(self):
        self.sio = socketio.Client(reconnection=False, logger=False, engineio_logger=False)
        self.online_players: set[str] = set()
        self._password: str = ""
        self._addr: str = ""
        self._connected = False
        self.last_error = ""

        self.on_output: Callable | None = None
        self.on_connect: Callable | None = None
        self.on_disconnect: Callable | None = None
        self.on_players_update: Callable | None = None
        self._register_events()

    def _register_events(self):
        sio = self.sio

        @sio.event
        def connect():
            self._connected = True
            sio.emit('stream/auth', {'data': {'password': self._password}})
            sio.emit('stream/resize', {'data': {'w': 120, 'h': 40}})
            sio.emit('stream/detail', {})
            sio.emit('stream/input', {'data': {'command': 'list'}})
            if self.on_connect:
                self.on_connect()

        @sio.event
        def disconnect():
            self._connected = False
            if self.on_disconnect:
                self.on_disconnect()

        @sio.on('instance/stdout')
        def on_stdout(data):
            text = data.get('data', {}).get('text', '')
            if not text:
                return

            if apply_player_events(text, self.online_players) and self.on_players_update:
                self.on_players_update(self.online_players)

            if self.on_output:
                self.on_output(text)

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self, addr: str, password: str, base_url: str) -> bool:
        self._addr = addr
        self._password = password
        self.last_error = ""
        ws_url = f"{addr}?{urlencode({'password': password})}"
        try:
            self.sio.connect(ws_url, transports=['websocket'], headers={
                "Origin": base_url,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            })
            return True
        except socketio.exceptions.SocketIOError as e:
            self.last_error = f"终端连接失败: {e}"
            return False

    def disconnect(self):
        if self._connected:
            self.sio.disconnect()
            self._connected = False

    def send_command(self, command: str):
        if self._connected:
            self.sio.emit('stream/input', {'data': {'command': command}})

    def send_raw(self, event: str, data: dict):
        if self._connected:
            self.sio.emit(event, data)

    def wait(self):
        if self._connected:
            self.sio.wait()
