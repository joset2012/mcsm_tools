import json
import os
import stat
import sys
import tempfile
from dataclasses import dataclass, asdict
from pathlib import Path

import requests

from .config import config_dir


CREDENTIALS_FILE_NAME = ".mcsm_credentials"
LEGACY_CREDENTIALS_FILE = Path(CREDENTIALS_FILE_NAME)


def credentials_path() -> Path:
    return config_dir() / CREDENTIALS_FILE_NAME


@dataclass
class MCSMCredentials:
    token: str
    cookie: str
    session_cookies: dict


def save_credentials(token: str, cookie: str, session: requests.Session) -> None:
    path = credentials_path()
    creds = MCSMCredentials(token, cookie, dict(session.cookies.get_dict()))
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f"{path.name}.", suffix=".tmp")
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(asdict(creds), f, ensure_ascii=False)
            os.chmod(tmp_name, stat.S_IRUSR | stat.S_IWUSR)
            os.replace(tmp_name, path)
        except BaseException:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise
    except OSError as e:
        print(f"保存凭证失败: {e}", file=sys.stderr)


def load_credentials() -> MCSMCredentials | None:
    path = credentials_path()
    if not path.exists():
        # Credentials used to be pickled next to the working directory; that
        # format is unsafe to deserialize, so it is dropped instead of read.
        _clear_legacy()
        return None
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        print(f"加载凭证失败: {e}", file=sys.stderr)
        return None
    if not isinstance(data, dict):
        return None
    cookies = data.get("session_cookies")
    return MCSMCredentials(
        token=str(data.get("token", "")),
        cookie=str(data.get("cookie", "")),
        session_cookies=cookies if isinstance(cookies, dict) else {},
    )


def clear_credentials() -> None:
    path = credentials_path()
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    except OSError as e:
        print(f"删除凭证失败: {e}", file=sys.stderr)
    _clear_legacy()


def _clear_legacy() -> None:
    try:
        LEGACY_CREDENTIALS_FILE.unlink()
    except (FileNotFoundError, OSError):
        pass


def secure_input(prompt="密码: ", mask_char='*') -> str:
    if sys.platform == 'win32':
        return _secure_input_windows(prompt, mask_char)
    return _secure_input_posix(prompt, mask_char)


def _secure_input_windows(prompt: str, mask_char: str) -> str:
    import msvcrt

    sys.stdout.write(prompt)
    sys.stdout.flush()
    password: list[str] = []
    while True:
        ch = msvcrt.getch()
        if ch in (b'\r', b'\n'):
            sys.stdout.write('\n')
            sys.stdout.flush()
            break
        if ch == b'\x08':
            if password:
                password.pop()
                sys.stdout.write('\b \b')
                sys.stdout.flush()
        elif ch == b'\x03':
            raise KeyboardInterrupt
        else:
            try:
                char = ch.decode('utf-8')
            except UnicodeDecodeError:
                continue
            sys.stdout.write(mask_char)
            sys.stdout.flush()
            password.append(char)
    return ''.join(password)


def _secure_input_posix(prompt: str, mask_char: str) -> str:
    import termios
    import tty

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        sys.stdout.write(prompt)
        sys.stdout.flush()
        password: list[str] = []
        while True:
            ch = sys.stdin.read(1)
            if ch in ('\r', '\n'):
                sys.stdout.write('\n')
                sys.stdout.flush()
                break
            if ch in ('\x7f', '\b'):
                if password:
                    password.pop()
                    sys.stdout.write('\b \b')
                    sys.stdout.flush()
            elif ch == '\x03':
                raise KeyboardInterrupt
            else:
                sys.stdout.write(mask_char)
                sys.stdout.flush()
                password.append(ch)
        return ''.join(password)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
