import json
import pickle
import stat
from pathlib import Path

import requests

from mcsm_tools.auth import (
    clear_credentials,
    credentials_path,
    load_credentials,
    save_credentials,
)


def _session_with_cookie() -> requests.Session:
    session = requests.Session()
    session.cookies.set("sid", "abc", domain="example.com")
    return session


def test_credentials_roundtrip(isolated_home):
    save_credentials("token", "sid=abc", _session_with_cookie())

    creds = load_credentials()
    assert creds is not None
    assert creds.token == "token"
    assert creds.cookie == "sid=abc"
    assert creds.session_cookies == {"sid": "abc"}


def test_credentials_are_json_and_owner_only(isolated_home):
    save_credentials("token", "sid=abc", _session_with_cookie())

    path = credentials_path()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert json.loads(path.read_text(encoding="utf-8"))["token"] == "token"


def test_legacy_pickle_credentials_are_never_loaded(isolated_home, tmp_path):
    legacy = Path(tmp_path / ".mcsm_credentials")
    legacy.write_bytes(pickle.dumps({"token": "pwned"}))

    assert load_credentials() is None
    assert not legacy.exists()


def test_clear_credentials_is_idempotent(isolated_home):
    save_credentials("token", "cookie", _session_with_cookie())
    clear_credentials()
    clear_credentials()

    assert load_credentials() is None


def test_corrupt_credentials_return_none(isolated_home):
    path = credentials_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json", encoding="utf-8")

    assert load_credentials() is None
