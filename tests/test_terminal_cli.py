import pytest

from mcsm_tools import terminal_cli
from mcsm_tools.auth import MCSMCredentials
from mcsm_tools.config import AppConfig


class FakeAPI:
    def __init__(self, valid=True):
        self.session = object()
        self.token = ""
        self.cookie = ""
        self.apikey = ""
        self.valid = valid
        self.login_calls = []
        self.login_result = True

    def set_apikey(self, apikey):
        self.apikey = apikey
        self.token = ""
        self.cookie = ""

    def set_auth(self, token, cookie):
        self.token = token
        self.cookie = cookie
        self.apikey = ""

    def validate_credentials(self):
        return self.valid

    def login(self, username, password):
        self.login_calls.append((username, password))
        if self.login_result:
            self.token = "new-token"
            self.cookie = "new-cookie"
        return self.login_result


@pytest.fixture
def no_saved_credentials(monkeypatch):
    monkeypatch.setattr(terminal_cli, "save_config", lambda cfg: None)
    monkeypatch.setattr(terminal_cli, "clear_credentials", lambda: None)
    monkeypatch.setattr(terminal_cli, "save_credentials", lambda *a: None)
    monkeypatch.setattr("mcsm_tools.auth.load_credentials", lambda: None)


def test_valid_apikey_from_config_is_used(no_saved_credentials):
    api = FakeAPI()
    cfg = AppConfig(apikey="key")

    assert terminal_cli._get_credentials(api, cfg) == ("", "", api.session)
    assert api.apikey == "key"


def test_valid_token_from_config_is_used(no_saved_credentials):
    api = FakeAPI()
    cfg = AppConfig(token="tok", cookie="ck")

    assert terminal_cli._get_credentials(api, cfg) == ("tok", "ck", api.session)


def test_saved_credentials_are_reused(monkeypatch):
    monkeypatch.setattr(terminal_cli, "save_config", lambda cfg: None)
    monkeypatch.setattr("mcsm_tools.auth.load_credentials",
                        lambda: MCSMCredentials("saved-tok", "saved-ck", {}))
    api = FakeAPI()

    assert terminal_cli._get_credentials(api, cfg=AppConfig()) == ("saved-tok", "saved-ck", api.session)


def test_stale_saved_credentials_are_cleared_before_prompting(monkeypatch):
    cleared = []
    monkeypatch.setattr(terminal_cli, "save_config", lambda cfg: None)
    monkeypatch.setattr(terminal_cli, "clear_credentials", lambda: cleared.append(True))
    monkeypatch.setattr("mcsm_tools.auth.load_credentials",
                        lambda: MCSMCredentials("stale", "stale", {}))
    monkeypatch.setattr("builtins.input", lambda prompt="": "2")
    api = FakeAPI(valid=False)

    with pytest.raises(SystemExit):
        terminal_cli._get_credentials(api, AppConfig())

    assert cleared == [True]


def test_interactive_apikey_login_updates_config(no_saved_credentials, monkeypatch):
    answers = iter(["2", "typed-key"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    api = FakeAPI()
    cfg = AppConfig(token="old", cookie="old")
    api.valid = True

    def validate():
        return api.apikey == "typed-key"

    api.validate_credentials = validate

    terminal_cli._get_credentials(api, cfg)

    assert cfg.apikey == "typed-key"
    assert cfg.token == "" and cfg.cookie == ""


def test_interactive_password_login_saves_tokens(no_saved_credentials, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt="": "1")
    monkeypatch.setattr(terminal_cli, "secure_input", lambda prompt="": "pw")
    api = FakeAPI(valid=False)
    cfg = AppConfig(username="admin")

    assert terminal_cli._get_credentials(api, cfg) == ("new-token", "new-cookie", api.session)
    assert api.login_calls == [("admin", "pw")]
    assert cfg.token == "new-token"
    assert cfg.password == "pw"


def test_failed_password_login_exits(no_saved_credentials, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt="": "1")
    monkeypatch.setattr(terminal_cli, "secure_input", lambda prompt="": "pw")
    api = FakeAPI(valid=False)
    api.login_result = False

    with pytest.raises(SystemExit):
        terminal_cli._get_credentials(api, AppConfig(username="admin"))
