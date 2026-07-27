import os
import pickle
import requests
from dataclasses import dataclass
from .config import AppConfig


CREDENTIALS_FILE = ".mcsm_credentials"


@dataclass
class MCSMCredentials:
    token: str
    cookie: str
    session_cookies: dict


def save_credentials(token: str, cookie: str, session: requests.Session) -> None:
    try:
        cookies_dict = session.cookies.get_dict()
        creds = MCSMCredentials(token, cookie, cookies_dict)
        with open(CREDENTIALS_FILE, 'wb') as f:
            pickle.dump(creds, f)
    except Exception as e:
        print(f"保存凭证失败: {e}")


def load_credentials() -> MCSMCredentials | None:
    if not os.path.exists(CREDENTIALS_FILE):
        return None
    try:
        with open(CREDENTIALS_FILE, 'rb') as f:
            creds = pickle.load(f)
        session = requests.Session()
        session.cookies.update(creds.session_cookies)
        return creds
    except Exception as e:
        print(f"加载凭证失败: {e}")
        return None


def clear_credentials() -> None:
    if os.path.exists(CREDENTIALS_FILE):
        os.remove(CREDENTIALS_FILE)


def secure_input(prompt="密码: ", mask_char='*') -> str:
    import sys
    if sys.platform == 'win32':
        import msvcrt
        sys.stdout.write(prompt)
        sys.stdout.flush()
        password = []
        while True:
            ch = msvcrt.getch()
            if ch in (b'\r', b'\n'):
                sys.stdout.write('\n')
                sys.stdout.flush()
                break
            elif ch == b'\x08':
                if password:
                    password.pop()
                    sys.stdout.write('\b \b')
                    sys.stdout.flush()
            elif ch == b'\x03':
                raise KeyboardInterrupt
            else:
                try:
                    char = ch.decode('utf-8')
                    sys.stdout.write(char)
                    sys.stdout.flush()
                    sys.stdout.write('\b' + mask_char)
                    sys.stdout.flush()
                    password.append(char)
                except UnicodeDecodeError:
                    continue
        return ''.join(password)
    else:
        import termios
        import tty
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            sys.stdout.write(prompt)
            sys.stdout.flush()
            password = []
            while True:
                ch = sys.stdin.read(1)
                if ch in ('\r', '\n'):
                    sys.stdout.write('\n')
                    sys.stdout.flush()
                    break
                elif ch in ('\x7f', '\b'):
                    if password:
                        password.pop()
                        sys.stdout.write('\b \b')
                        sys.stdout.flush()
                elif ch == '\x03':
                    raise KeyboardInterrupt
                else:
                    sys.stdout.write(ch)
                    sys.stdout.flush()
                    sys.stdout.write('\b' + mask_char)
                    sys.stdout.flush()
                    password.append(ch)
            return ''.join(password)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
