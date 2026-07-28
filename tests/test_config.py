import configparser

from mcsm_tools import config as config_mod
from mcsm_tools.config import AppConfig, create_default_config, load_config, save_config


def test_is_instance_configured():
    assert not AppConfig().is_instance_configured
    assert not AppConfig(daemon_id="d").is_instance_configured
    assert AppConfig(daemon_id="d", instance_uuid="u").is_instance_configured


def test_has_auth_accepts_each_credential_kind():
    assert not AppConfig().has_auth
    assert not AppConfig(token="t").has_auth
    assert AppConfig(token="t", cookie="c").has_auth
    assert AppConfig(username="u", password="p").has_auth
    assert AppConfig(apikey="k").has_auth


def test_create_default_config_writes_file(workdir):
    cfg = create_default_config()
    assert cfg == AppConfig()

    parser = configparser.ConfigParser()
    parser.read(workdir / config_mod.CONFIG_FILE, encoding="utf-8")
    assert parser.get("Panel", "base_url") == "https://mcsm.rainyun.com"
    assert parser.get("UI", "auto_connect") == "yes"


def test_load_config_creates_defaults_when_missing(workdir):
    cfg = load_config()
    assert cfg == AppConfig()
    assert (workdir / config_mod.CONFIG_FILE).exists()


def test_save_then_load_roundtrip(workdir):
    saved = AppConfig(
        base_url="https://panel.example.com",
        daemon_id="daemon-1",
        instance_uuid="uuid-1",
        instance_name="survival",
        token="tok",
        cookie="ck=1",
        username="admin",
        password="secret",
        apikey="key",
        auto_connect=False,
        show_exit_dialog=False,
        terminal_memory=False,
    )
    save_config(saved)
    assert load_config() == saved


def test_load_config_falls_back_on_missing_keys(workdir):
    (workdir / config_mod.CONFIG_FILE).write_text("[Panel]\n", encoding="utf-8")
    cfg = load_config()
    assert cfg.base_url == "https://mcsm.rainyun.com"
    assert cfg.daemon_id == ""
    assert cfg.auto_connect is True
    assert cfg.terminal_memory is True
