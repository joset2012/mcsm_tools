import stat
from pathlib import Path

from mcsm_tools.config import AppConfig, config_path, load_config, save_config


def test_save_and_load_roundtrip(isolated_home):
    cfg = AppConfig(
        base_url="https://panel.example.com/",
        daemon_id="daemon",
        instance_uuid="uuid",
        apikey="key",
        auto_connect=False,
    )
    save_config(cfg)

    loaded = load_config()
    assert loaded.base_url == "https://panel.example.com/"
    assert loaded.daemon_id == "daemon"
    assert loaded.apikey == "key"
    assert loaded.auto_connect is False
    assert loaded.is_instance_configured
    assert loaded.has_auth


def test_config_is_written_to_user_dir_with_owner_only_permissions(isolated_home):
    save_config(AppConfig(password="secret"))

    path = config_path()
    assert path == isolated_home / "mcsm_config.ini"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_missing_config_creates_defaults(isolated_home):
    cfg = load_config()
    assert cfg.base_url.startswith("https://")
    assert not cfg.has_auth
    assert config_path().exists()


def test_legacy_config_in_cwd_is_migrated(isolated_home, tmp_path):
    Path(tmp_path / "mcsm_config.ini").write_text(
        "[Panel]\nbase_url = https://legacy.example.com\n"
        "[Auth]\napikey = legacy-key\n",
        encoding="utf-8",
    )

    cfg = load_config()

    assert cfg.base_url == "https://legacy.example.com"
    assert cfg.apikey == "legacy-key"
    assert config_path().exists()


def test_corrupt_config_falls_back_to_defaults(isolated_home):
    config_path().parent.mkdir(parents=True, exist_ok=True)
    config_path().write_text("not an ini file\n= = =", encoding="utf-8")

    cfg = load_config()

    assert cfg == AppConfig()


def test_save_does_not_leave_temp_files(isolated_home):
    save_config(AppConfig())
    save_config(AppConfig(username="u"))

    assert [p.name for p in isolated_home.iterdir()] == ["mcsm_config.ini"]
