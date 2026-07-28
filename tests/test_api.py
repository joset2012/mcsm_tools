import pytest
import requests_mock as rm_module

from mcsm_tools.api import LIST_PAGE_SIZE, MCSManagerAPI

BASE = "https://panel.test"
DAEMON = "daemon-1"
UUID = "uuid-1"


@pytest.fixture
def api():
    return MCSManagerAPI(BASE)


@pytest.fixture
def mock(api):
    with rm_module.Mocker(session=api.session) as m:
        with rm_module.Mocker(session=api.transfer_session) as t:
            m.transfer = t
            yield m


def test_base_url_is_normalized():
    assert MCSManagerAPI("https://panel.test/").base_url == BASE


def test_set_base_url_updates_origin_headers(api):
    api.set_base_url("https://other.test/")
    assert api.base_url == "https://other.test"
    assert api.session.headers["Origin"] == "https://other.test"


def test_apikey_auth_sets_header_and_query_param(api, mock):
    api.set_apikey("k")
    mock.get(f"{BASE}/api/auth/", json={"status": 200, "data": {}})

    assert api.validate_credentials()
    assert mock.last_request.qs["apikey"] == ["k"]
    assert mock.last_request.headers["x-request-api-key"] == "k"


def test_switching_auth_clears_previous_headers(api):
    api.set_apikey("k")
    api.set_auth("token", "sid=1")
    assert "x-request-api-key" not in api.session.headers
    assert api.session.headers["Cookie"] == "sid=1"


def test_http_error_is_reported_in_last_error(api, mock):
    mock.get(f"{BASE}/api/auth/", status_code=403, text="forbidden")

    assert api.validate_credentials() is False
    assert "403" in api.last_error


def test_login_without_token_fails_with_error(api, mock):
    mock.post(f"{BASE}/api/auth/login", json={"status": 200, "data": {}})
    mock.get(f"{BASE}/api/auth/", json={"status": 200, "data": {}})

    assert api.login("u", "p") is False
    assert api.last_error


def test_login_failure_sets_last_error(api, mock):
    mock.post(f"{BASE}/api/auth/login", json={"status": 500, "data": "bad password"})

    assert api.login("u", "p") is False
    assert api.last_error


def test_login_stores_token_and_session_cookies(api, mock):
    api.session.cookies.set("sid", "abc")
    mock.post(f"{BASE}/api/auth/login", json={"status": 200, "data": {"token": "t"}})

    assert api.login("u", "p") is True
    assert api.token == "t"
    assert "sid=abc" in api.cookie
    assert api.is_authenticated


def test_instance_actions_hit_expected_endpoints(api, mock):
    for action, method in [("kill", api.kill_instance), ("open", api.open_instance),
                           ("stop", api.stop_instance), ("restart", api.restart_instance)]:
        mock.get(f"{BASE}/api/protected_instance/{action}", json={"status": 200})
        assert method(DAEMON, UUID) is True
        assert mock.last_request.qs["daemonid"] == [DAEMON]
        assert mock.last_request.qs["uuid"] == [UUID]


def test_list_files_follows_pagination(api, mock):
    first = [{"name": f"f{i}"} for i in range(LIST_PAGE_SIZE)]
    second = [{"name": "last"}]
    mock.get(f"{BASE}/api/files/list", [
        {"json": {"status": 200, "data": {"items": first}}},
        {"json": {"status": 200, "data": {"items": second}}},
    ])

    items = api.list_files(DAEMON, UUID, "/plugins")

    assert len(items) == LIST_PAGE_SIZE + 1
    assert items[-1]["name"] == "last"


def test_list_files_returns_none_on_error(api, mock):
    mock.get(f"{BASE}/api/files/list", status_code=500)
    assert api.list_files(DAEMON, UUID) is None


def test_list_files_accepts_plain_list_payload(api, mock):
    mock.get(f"{BASE}/api/files/list", json={"status": 200, "data": [{"name": "a"}]})
    assert api.list_files(DAEMON, UUID) == [{"name": "a"}]


def test_download_writes_file_and_uses_transfer_session(api, mock, tmp_path):
    mock.post(f"{BASE}/api/files/download",
              json={"status": 200, "data": {"password": "pw", "addr": "wss://daemon.test"}})
    mock.transfer.get("https://daemon.test/download/pw/world.zip", content=b"payload")

    target = tmp_path / "nested" / "world.zip"
    assert api.download_file(DAEMON, UUID, "/world.zip", str(target)) is True
    assert target.read_bytes() == b"payload"
    assert "x-request-api-key" not in mock.transfer.last_request.headers


def test_failed_download_leaves_no_partial_file(api, mock, tmp_path):
    mock.post(f"{BASE}/api/files/download",
              json={"status": 200, "data": {"password": "pw", "addr": "https://daemon.test"}})
    mock.transfer.get("https://daemon.test/download/pw/world.zip", status_code=404)

    target = tmp_path / "world.zip"
    assert api.download_file(DAEMON, UUID, "/world.zip", str(target)) is False
    assert not target.exists()
    assert not (tmp_path / "world.zip.part").exists()
    assert api.last_error


def test_upload_reports_progress_and_closes_file(api, mock, tmp_path):
    local = tmp_path / "plugin.jar"
    local.write_bytes(b"x" * 2048)
    mock.post(f"{BASE}/api/files/upload",
              json={"status": 200, "data": {"password": "pw", "addr": "daemon.test"}})
    mock.transfer.post("https://daemon.test/upload/pw", json={"status": 200})

    seen = []
    assert api.upload_file(str(local), "/plugins", DAEMON, UUID,
                           progress_callback=lambda cur, total: seen.append((cur, total))) is True
    assert seen and seen[-1] == (2048, 2048)


def test_upload_missing_file_reports_error(api, tmp_path):
    assert api.upload_file(str(tmp_path / "nope.jar"), "/plugins", DAEMON, UUID) is False
    assert "不存在" in api.last_error


def test_auto_discover_prefers_named_instance(api, mock):
    mock.get(f"{BASE}/api/auth/", json={"status": 200, "data": {"instances": [
        {"nickname": "other", "daemonId": "d1", "instanceUuid": "u1", "status": 1},
        {"nickname": "target", "daemonId": "d2", "instanceUuid": "u2", "status": 0},
    ]}})

    assert api.auto_discover_instance("target") == ("d2", "u2")


def test_auto_discover_falls_back_to_running_instance(api, mock):
    mock.get(f"{BASE}/api/auth/", json={"status": 200, "data": {"instances": [
        {"nickname": "a", "daemonId": "d1", "instanceUuid": "u1", "status": 0},
        {"nickname": "b", "daemonId": "d2", "instanceUuid": "u2", "status": 1},
    ]}})

    assert api.auto_discover_instance() == ("d2", "u2")


def test_instance_status_text(api, mock):
    mock.get(f"{BASE}/api/auth/", json={"status": 200, "data": {"instances": [
        {"daemonId": DAEMON, "instanceUuid": UUID, "status": 1, "ip": "1.2.3.4", "port": 25565},
    ]}})

    status = api.get_instance_status(DAEMON, UUID)
    assert status["text"] == "运行中"
    assert status["addr"] == "1.2.3.4:25565"
