import pytest

from mcsm_tools.plugin_manager import Plugin


@pytest.mark.parametrize(
    "name, is_jar",
    [("a.jar", True), ("A.JAR", True), ("mod.litemod", True), ("pack.zip", True), ("config.yml", False)],
)
def test_is_jar_detection(name, is_jar):
    assert Plugin(name, f"/plugins/{name}").is_jar is is_jar


def test_disabled_detection_and_display_name():
    enabled = Plugin("essentials.jar", "/plugins/essentials.jar")
    disabled = Plugin("essentials.jar.disabled", "/plugins/essentials.jar.disabled")

    assert enabled.is_disabled is False
    assert enabled.display_name == "essentials.jar"
    assert disabled.is_disabled is True
    assert disabled.display_name == "essentials.jar.disabled ⛔"


def test_is_active_requires_enabled_jar_or_directory():
    assert Plugin("essentials.jar", "/p/essentials.jar").is_active is True
    assert Plugin("essentials.jar.disabled", "/p/essentials.jar.disabled").is_active is False
    assert Plugin("worldedit", "/p/worldedit", is_dir=True).is_active is True
    assert Plugin("config.yml", "/p/config.yml").is_active is False


def test_file_name_of_enabled_plugin_is_the_name():
    assert Plugin("essentials.jar", "/p/essentials.jar").file_name == "essentials.jar"
    assert Plugin("worldedit", "/p/worldedit", is_dir=True).file_name == "worldedit"


def test_file_name_strips_a_trailing_disabled_segment():
    assert Plugin("essentials.disabled.disabled", "/p/x").file_name == "essentials"
    # ".jar.disabled" keeps its suffix: splitext leaves "essentials.jar" as the base
    assert Plugin("essentials.jar.disabled", "/p/x").file_name == "essentials.jar.disabled"
