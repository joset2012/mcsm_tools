import configparser
import os
from pathlib import Path
from dataclasses import dataclass, asdict


CONFIG_FILE = "mcsm_config.ini"


def _open_private(path: str):
    """Open a file for writing with owner-only (0600) permissions.

    The config stores credentials (token, cookie, password, apikey) in
    plaintext, so it must not be readable by other local users.
    """
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    return os.fdopen(fd, 'w', encoding='utf-8')


@dataclass
class AppConfig:
    base_url: str = "https://mcsm.rainyun.com"
    daemon_id: str = ""
    instance_uuid: str = ""
    instance_name: str = ""
    token: str = ""
    cookie: str = ""
    username: str = ""
    password: str = ""
    apikey: str = ""
    auto_connect: bool = True
    show_exit_dialog: bool = True
    terminal_memory: bool = True

    @property
    def is_instance_configured(self) -> bool:
        return bool(self.daemon_id and self.instance_uuid)

    @property
    def has_auth(self) -> bool:
        return bool(self.token and self.cookie) or bool(self.username and self.password) or bool(self.apikey)


def create_default_config() -> AppConfig:
    config = configparser.ConfigParser()
    config['Panel'] = {'base_url': 'https://mcsm.rainyun.com'}
    config['Instance'] = {'daemon_id': '', 'instance_uuid': '', 'instance_name': ''}
    config['Auth'] = {'token': '', 'cookie': '', 'username': '', 'password': '', 'apikey': ''}
    config['UI'] = {'auto_connect': 'yes', 'show_exit_dialog': 'yes', 'terminal_memory': 'yes'}
    with _open_private(CONFIG_FILE) as f:
        config.write(f)
    return AppConfig()


def load_config() -> AppConfig:
    if not os.path.exists(CONFIG_FILE):
        return create_default_config()
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding='utf-8')
    return AppConfig(
        base_url=config.get('Panel', 'base_url', fallback='https://mcsm.rainyun.com'),
        daemon_id=config.get('Instance', 'daemon_id', fallback=''),
        instance_uuid=config.get('Instance', 'instance_uuid', fallback=''),
        instance_name=config.get('Instance', 'instance_name', fallback=''),
        token=config.get('Auth', 'token', fallback=''),
        cookie=config.get('Auth', 'cookie', fallback=''),
        username=config.get('Auth', 'username', fallback=''),
        password=config.get('Auth', 'password', fallback=''),
        apikey=config.get('Auth', 'apikey', fallback=''),
        auto_connect=config.getboolean('UI', 'auto_connect', fallback=True),
        show_exit_dialog=config.getboolean('UI', 'show_exit_dialog', fallback=True),
        terminal_memory=config.getboolean('UI', 'terminal_memory', fallback=True),
    )


def save_config(cfg: AppConfig) -> None:
    config = configparser.ConfigParser()
    config['Panel'] = {'base_url': cfg.base_url}
    config['Instance'] = {
        'daemon_id': cfg.daemon_id,
        'instance_uuid': cfg.instance_uuid,
        'instance_name': cfg.instance_name,
    }
    config['Auth'] = {
        'token': cfg.token,
        'cookie': cfg.cookie,
        'username': cfg.username,
        'password': cfg.password,
        'apikey': cfg.apikey,
    }
    config['UI'] = {
        'auto_connect': 'yes' if cfg.auto_connect else 'no',
        'show_exit_dialog': 'yes' if cfg.show_exit_dialog else 'no',
        'terminal_memory': 'yes' if cfg.terminal_memory else 'no',
    }
    with _open_private(CONFIG_FILE) as f:
        config.write(f)
