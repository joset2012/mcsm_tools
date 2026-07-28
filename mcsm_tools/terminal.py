import json
import re
import socketio
import threading
from typing import Callable


PLAYER_PATTERNS = {
    'list': re.compile(r'There are \d+ of a max of \d+ players online:\s*(.+)', re.IGNORECASE),
    'join': re.compile(r'(\w+) joined the game'),
    'leave': re.compile(r'(\w+) left the game'),
}


class MCSMTerminal:
    def __init__(self):
        self.sio = socketio.Client(reconnection=False, logger=False, engineio_logger=False)
        self.online_players: set[str] = set()
        self._password: str = ""
        self._addr: str = ""
        self._connected = False
        self.last_error: str = ""

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

            match = PLAYER_PATTERNS['list'].search(text)
            if match:
                names = match.group(1).split(', ')
                cleaned = [re.sub(r'§[0-9a-fklmnor]', '', name).strip() for name in names]
                self.online_players = set(cleaned)
                if self.on_players_update:
                    self.on_players_update(self.online_players)
                if self.on_output:
                    self.on_output(text)
                return

            match = PLAYER_PATTERNS['join'].search(text)
            if match:
                self.online_players.add(match.group(1))
                if self.on_players_update:
                    self.on_players_update(self.online_players)
                if self.on_output:
                    self.on_output(text)
                return

            match = PLAYER_PATTERNS['leave'].search(text)
            if match:
                self.online_players.discard(match.group(1))
                if self.on_players_update:
                    self.on_players_update(self.online_players)
                if self.on_output:
                    self.on_output(text)
                return

            if self.on_output:
                self.on_output(text)

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self, addr: str, password: str, base_url: str) -> bool:
        self._addr = addr
        self._password = password
        self.last_error = ""
        ws_url = f"{addr}?password={password}"
        try:
            self.sio.connect(ws_url, transports=['websocket'], headers={
                "Origin": base_url,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            })
            return True
        except socketio.exceptions.ConnectionError as e:
            self.last_error = f"WebSocket 连接失败: {e}"
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
