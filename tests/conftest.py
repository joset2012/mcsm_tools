import pytest


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Keep config/credentials/history writes inside the test's tmp dir."""
    home = tmp_path / "mcsm_home"
    monkeypatch.setenv("MCSM_TOOLS_HOME", str(home))
    monkeypatch.chdir(tmp_path)
    return home
