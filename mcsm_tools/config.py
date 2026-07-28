import configparser
import os
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path


CONFIG_FILE_NAME = "mcsm_config.ini"
HOME_ENV_VAR = "MCSM_TOOLS_HOME"
# Pre-2.1 releases kept the config next to the working directory.
LEGACY_CONFIG_FILE = Path(CONFIG_FILE_NAME)

DEFAULT_BASE_URL = "https://mcsm.rainyun.com"


@dataclass
class AppConfig:
    base_url: str = DEFAULT_BASE_URL
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


def config_dir() -> Path:
    """Directory holding config, credentials and command history."""
    return Path(os.environ.get(HOME_ENV_VAR) or Path.home() / ".mcsm_tools")


def config_path() -> Path:
    return config_dir() / CONFIG_FILE_NAME


def _to_parser(cfg: AppConfig) -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    parser['Panel'] = {'base_url': cfg.base_url}
    parser['Instance'] = {
        'daemon_id': cfg.daemon_id,
        'instance_uuid': cfg.instance_uuid,
        'instance_name': cfg.instance_name,
    }
    parser['Auth'] = {
        'token': cfg.token,
        'cookie': cfg.cookie,
        'username': cfg.username,
        'password': cfg.password,
        'apikey': cfg.apikey,
    }
    parser['UI'] = {
        'auto_connect': 'yes' if cfg.auto_connect else 'no',
        'show_exit_dialog': 'yes' if cfg.show_exit_dialog else 'no',
        'terminal_memory': 'yes' if cfg.terminal_memory else 'no',
    }
    return parser


def _from_parser(parser: configparser.ConfigParser) -> AppConfig:
    def get(section: str, option: str, fallback: str = '') -> str:
        return parser.get(section, option, fallback=fallback)

    def get_bool(section: str, option: str, fallback: bool = True) -> bool:
        try:
            return parser.getboolean(section, option, fallback=fallback)
        except ValueError:
            return fallback

    return AppConfig(
        base_url=get('Panel', 'base_url', DEFAULT_BASE_URL) or DEFAULT_BASE_URL,
        daemon_id=get('Instance', 'daemon_id'),
        instance_uuid=get('Instance', 'instance_uuid'),
        instance_name=get('Instance', 'instance_name'),
        token=get('Auth', 'token'),
        cookie=get('Auth', 'cookie'),
        username=get('Auth', 'username'),
        password=get('Auth', 'password'),
        apikey=get('Auth', 'apikey'),
        auto_connect=get_bool('UI', 'auto_connect'),
        show_exit_dialog=get_bool('UI', 'show_exit_dialog'),
        terminal_memory=get_bool('UI', 'terminal_memory'),
    )


def create_default_config() -> AppConfig:
    cfg = AppConfig()
    save_config(cfg)
    return cfg


def load_config() -> AppConfig:
    path = config_path()
    if not path.exists():
        legacy = LEGACY_CONFIG_FILE
        if legacy.is_file():
            cfg = _read(legacy)
            save_config(cfg)
            return cfg
        return create_default_config()
    return _read(path)


def _read(path: Path) -> AppConfig:
    parser = configparser.ConfigParser()
    try:
        parser.read(path, encoding='utf-8')
    except (OSError, configparser.Error):
        return AppConfig()
    return _from_parser(parser)


def save_config(cfg: AppConfig) -> None:
    """Write the config atomically with owner-only permissions.

    Credentials live in this file, so it must never be world readable and a
    crash mid-write must not leave a truncated file behind.
    """
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    parser = _to_parser(cfg)

    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            parser.write(f)
        os.chmod(tmp_name, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
