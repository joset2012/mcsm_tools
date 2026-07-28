import pickle

import requests

from mcsm_tools import auth as auth_mod
from mcsm_tools.auth import (
    MCSMCredentials,
    clear_credentials,
    load_credentials,
    save_credentials,
)


def _session_with_cookies(**cookies) -> requests.Session:
    session = requests.Session()
    for key, value in cookies.items():
        session.cookies.set(key, value)
    return session


def test_save_and_load_credentials_roundtrip(workdir):
    save_credentials("tok", "ck=1", _session_with_cookies(sid="abc"))

    creds = load_credentials()
    assert isinstance(creds, MCSMCredentials)
    assert creds.token == "tok"
    assert creds.cookie == "ck=1"
    assert creds.session_cookies == {"sid": "abc"}


def test_load_credentials_returns_none_when_absent(workdir):
    assert load_credentials() is None


def test_load_credentials_returns_none_on_corrupt_file(workdir, capsys):
    (workdir / auth_mod.CREDENTIALS_FILE).write_bytes(b"not-a-pickle")

    assert load_credentials() is None
    assert "加载凭证失败" in capsys.readouterr().out


def test_save_credentials_reports_failure_instead_of_raising(workdir, capsys):
    class BrokenSession:
        @property
        def cookies(self):
            raise RuntimeError("boom")

    save_credentials("tok", "ck=1", BrokenSession())

    assert not (workdir / auth_mod.CREDENTIALS_FILE).exists()
    assert "保存凭证失败" in capsys.readouterr().out


def test_clear_credentials_removes_file_and_is_idempotent(workdir):
    path = workdir / auth_mod.CREDENTIALS_FILE
    path.write_bytes(pickle.dumps(MCSMCredentials("t", "c", {})))

    clear_credentials()
    assert not path.exists()

    clear_credentials()
