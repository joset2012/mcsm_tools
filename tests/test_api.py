import json

import pytest
import requests

from mcsm_tools.api import MCSManagerAPI, _ProgressReader
from mcsm_tools.config import AppConfig


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=None, content_type="application/json"):
        self.status_code = status_code
        self._payload = payload
        self.text = text if text is not None else json.dumps(payload or {})
        self.headers = {"content-type": content_type}
        self.content = self.text.encode()

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class FakeSession:
    """Records outgoing calls and replays queued responses."""

    def __init__(self):
        self.headers = {}
        self.cookies = requests.cookies.RequestsCookieJar()
        self.calls = []
        self.responses = []

    def queue(self, response):
        self.responses.append(response)
        return response

    def _next(self):
        if not self.responses:
            raise AssertionError("unexpected request")
        return self.responses.pop(0)

    def request(self, method, url, params=None, json=None, timeout=None):
        self.calls.append({"method": method, "url": url, "params": params, "json": json})
        response = self._next()
        if isinstance(response, Exception):
            raise response
        return response

    def post(self, url, json=None, timeout=None, **kwargs):
        return self.request("POST", url, json=json, timeout=timeout)

    def get(self, url, params=None, timeout=None, **kwargs):
        return self.request("GET", url, params=params, timeout=timeout)


@pytest.fixture
def api():
    client = MCSManagerAPI("https://panel.example.com/")
    client.session = FakeSession()
    return client


def ok(data=None):
    return FakeResponse(payload={"status": 200, "data": data if data is not None else {}})


def test_base_url_is_normalised_and_headers_set():
    client = MCSManagerAPI("https://panel.example.com/")
    assert client.base_url == "https://panel.example.com"
    assert client.session.headers["Origin"] == "https://panel.example.com"
    assert client.session.headers["Referer"] == "https://panel.example.com/"
    assert client._build_url("/api/x") == "https://panel.example.com/api/x"


def test_set_auth_and_set_apikey_are_mutually_exclusive(api):
    api.set_auth("tok", "ck=1")
    assert api.session.headers["Cookie"] == "ck=1"
    assert api.is_authenticated

    api.set_apikey("key")
    assert "Cookie" not in api.session.headers
    assert api.session.headers["x-request-api-key"] == "key"
    assert api.token == "" and api.cookie == ""
    assert api.is_authenticated

    api.set_auth("tok", "")
    assert "x-request-api-key" not in api.session.headers
    assert not api.is_authenticated


def test_merge_auth_params(api):
    assert api._merge_auth_params({"a": 1}) == {"a": 1}

    api.set_auth("tok", "ck=1")
    assert api._merge_auth_params() == {"token": "tok"}

    api.set_apikey("key")
    assert api._merge_auth_params({"a": 1}) == {"a": 1, "apikey": "key", "token": "key"}


def test_refresh_auth_from_config_prefers_apikey(api):
    assert api.refresh_auth_from_config(AppConfig(apikey="key", token="t", cookie="c")) is True
    assert api.apikey == "key"

    assert api.refresh_auth_from_config(AppConfig(token="t", cookie="c")) is True
    assert api.token == "t"

    assert api.refresh_auth_from_config(AppConfig()) is False


def test_refresh_auth_from_config_falls_back_to_login(api, monkeypatch):
    called = {}

    def fake_login(username, password):
        called["creds"] = (username, password)
        return True

    monkeypatch.setattr(api, "login", fake_login)

    assert api.refresh_auth_from_config(AppConfig(username="u", password="p")) is True
    assert called["creds"] == ("u", "p")


def test_request_sends_merged_params(api):
    api.set_apikey("key")
    api.session.queue(ok({"hello": "world"}))

    assert api._get("/api/thing", {"uuid": "u"}) == {"status": 200, "data": {"hello": "world"}}
    call = api.session.calls[0]
    assert call["method"] == "GET"
    assert call["url"] == "https://panel.example.com/api/thing"
    assert call["params"] == {"uuid": "u", "apikey": "key", "token": "key"}


def test_request_returns_text_payload_for_non_json(api):
    api.session.queue(FakeResponse(text="plain", content_type="text/plain"))
    assert api._get("/api/thing") == {"status": 200, "data": "plain"}


@pytest.mark.parametrize(
    "error, expected",
    [
        (requests.ConnectionError(), "连接失败: https://panel.example.com/api/thing"),
        (requests.Timeout(), "请求超时"),
        (requests.RequestException("bad"), "请求错误: bad"),
    ],
)
def test_request_records_transport_errors(api, error, expected):
    api.session.queue(error)
    assert api._get("/api/thing") is None
    assert api.last_error == expected


def test_request_records_http_error_body(api):
    api.session.queue(FakeResponse(status_code=403, text="forbidden", content_type="text/plain"))
    assert api._get("/api/thing") is None
    assert api.last_error == "HTTP 403: forbidden"


def test_request_records_unknown_error(api, capsys):
    api.session.queue(RuntimeError("boom"))
    assert api._get("/api/thing") is None
    assert api.last_error == "未知错误: boom"


def test_login_with_apikey_clears_state_on_failure(api):
    api.session.queue(FakeResponse(payload={"status": 500}))
    assert api.login_with_apikey("key") is False
    assert api.apikey == ""
    assert "x-request-api-key" not in api.session.headers

    api.session.queue(ok())
    assert api.login_with_apikey("key") is True
    assert api.apikey == "key"


def test_login_uses_token_from_response_and_cookies(api):
    api.session.cookies.set("sid", "abc")
    api.session.queue(FakeResponse(payload={"status": 200, "data": {"token": "tok"}}))

    assert api.login("admin", "pw") is True
    assert api.token == "tok"
    assert api.cookie == "sid=abc"
    assert api.session.calls[0]["json"] == {"username": "admin", "password": "pw"}


def test_login_falls_back_to_auth_info_for_token(api):
    api.session.queue(FakeResponse(payload={"status": 200, "data": {}}))
    api.session.queue(FakeResponse(payload={"status": 200, "data": {"token": "tok2"}}))

    assert api.login("admin", "pw") is True
    assert api.token == "tok2"


def test_login_fails_without_token(api):
    api.session.queue(FakeResponse(payload={"status": 200, "data": {}}))
    api.session.queue(FakeResponse(payload={"status": 200, "data": {}}))
    assert api.login("admin", "pw") is False

    api.session.queue(FakeResponse(payload={"status": 500}))
    assert api.login("admin", "pw") is False

    api.session.queue(requests.ConnectionError())
    assert api.login("admin", "pw") is False


def test_validate_credentials(api):
    api.session.queue(ok())
    assert api.validate_credentials() is True

    api.session.queue(FakeResponse(payload={"status": 403}))
    assert api.validate_credentials() is False


def test_list_instances(api):
    api.session.queue(ok({"instances": [{"nickname": "a"}]}))
    assert api.list_instances() == [{"nickname": "a"}]

    api.session.queue(FakeResponse(payload={"status": 403}))
    assert api.list_instances() == []


def test_auto_discover_instance_prefers_named_match(api, monkeypatch):
    instances = [
        {"nickname": "creative", "status": 0, "daemonId": "d0", "instanceUuid": "u0"},
        {"nickname": "survival", "status": 1, "daemonId": "d1", "instanceUuid": "u1"},
    ]
    monkeypatch.setattr(api, "list_instances", lambda: instances)

    assert api.auto_discover_instance("creative") == ("d0", "u0")
    assert api.auto_discover_instance("missing") == ("d1", "u1")
    assert api.auto_discover_instance() == ("d1", "u1")


def test_auto_discover_instance_falls_back_to_first(api, monkeypatch):
    monkeypatch.setattr(api, "list_instances", lambda: [{"status": 0, "daemonId": "d", "instanceUuid": "u"}])
    assert api.auto_discover_instance() == ("d", "u")

    monkeypatch.setattr(api, "list_instances", list)
    assert api.auto_discover_instance() is None

    monkeypatch.setattr(api, "list_instances", lambda: [{"status": 0}])
    assert api.auto_discover_instance() is None


@pytest.mark.parametrize(
    "value, text",
    [(0, "已停止"), (1, "运行中"), (2, "启动中"), (3, "停止中"), (-1, "未知"), (99, "未知")],
)
def test_status_text(value, text):
    assert MCSManagerAPI._status_text(value) == text


def test_get_instance_status_from_instance_list(api, monkeypatch):
    monkeypatch.setattr(api, "list_instances", lambda: [
        {"instanceUuid": "u", "daemonId": "d", "status": 1, "ip": "1.2.3.4", "port": 25565},
    ])

    assert api.get_instance_status("d", "u") == {"status": 1, "text": "运行中", "addr": "1.2.3.4:25565"}


def test_get_instance_status_falls_back_to_instance_info(api, monkeypatch):
    monkeypatch.setattr(api, "list_instances", lambda: [{"instanceUuid": "other", "daemonId": "d"}])
    monkeypatch.setattr(api, "get_instance_info", lambda d, u: {"instance": {"status": 0, "ip": "", "port": ""}})

    assert api.get_instance_status("d", "u") == {"status": 0, "text": "已停止", "addr": ""}


def test_get_instance_status_unknown_when_nothing_found(api, monkeypatch):
    monkeypatch.setattr(api, "list_instances", list)
    monkeypatch.setattr(api, "get_instance_info", lambda d, u: None)

    assert api.get_instance_status("d", "u") == {"status": -1, "text": "未知", "addr": ""}


def test_get_instance_info(api):
    api.session.queue(ok({"instance": {"status": 1}}))
    assert api.get_instance_info("d", "u") == {"instance": {"status": 1}}

    api.session.queue(FakeResponse(payload={"status": 403}))
    assert api.get_instance_info("d", "u") is None


@pytest.mark.parametrize(
    "method, path",
    [
        ("kill_instance", "/api/protected_instance/kill"),
        ("open_instance", "/api/protected_instance/open"),
        ("stop_instance", "/api/protected_instance/stop"),
        ("restart_instance", "/api/protected_instance/restart"),
    ],
)
def test_power_actions(api, method, path):
    api.session.queue(ok())
    assert getattr(api, method)("d", "u") is True
    assert api.session.calls[-1]["url"].endswith(path)
    assert api.session.calls[-1]["params"] == {"uuid": "u", "daemonId": "d"}

    api.session.queue(FakeResponse(payload={"status": 500}))
    assert getattr(api, method)("d", "u") is False


def test_get_websocket_password(api):
    api.session.queue(ok({"password": "pw", "addr": "wss://node/x"}))
    assert api.get_websocket_password("d", "u") == ("pw", "wss://node/x")

    api.session.queue(ok({"password": "pw"}))
    assert api.get_websocket_password("d", "u") is None

    api.session.queue(FakeResponse(payload={"status": 500}))
    assert api.get_websocket_password("d", "u") is None


def test_list_files_normalises_payload_shapes(api):
    api.session.queue(ok([{"name": "a"}]))
    assert api.list_files("d", "u") == [{"name": "a"}]

    api.session.queue(ok({"items": [{"name": "b"}]}))
    assert api.list_files("d", "u", "/logs") == [{"name": "b"}]
    assert api.session.calls[-1]["params"]["target"] == "/logs"

    api.session.queue(ok({"0": {"name": "c"}}))
    assert api.list_files("d", "u") == [{"name": "c"}]

    api.session.queue(FakeResponse(payload={"status": 500}))
    assert api.list_files("d", "u") is None


def test_file_mutations(api):
    api.session.queue(ok())
    assert api.delete_files("d", "u", ["/a"]) is True
    assert api.session.calls[-1]["json"] == {"targets": ["/a"]}

    api.session.queue(ok())
    assert api.create_directory("d", "u", "/new") is True
    assert api.session.calls[-1]["json"] == {"target": "/new"}

    api.session.queue(ok())
    assert api.move_files("d", "u", [["/a", "/b"]]) is True
    assert api.session.calls[-1]["method"] == "PUT"

    api.session.queue(ok())
    assert api.touch_file("d", "u", "/a.txt") is True

    api.session.queue(FakeResponse(payload={"status": 500}))
    assert api.touch_file("d", "u", "/a.txt") is False


def test_get_file_info(api):
    api.session.queue(ok({"size": 12}))
    assert api.get_file_info("d", "u", "/a.txt") == {"size": 12}

    api.session.queue(FakeResponse(payload={"status": 500}))
    assert api.get_file_info("d", "u", "/a.txt") is None


def test_compress_and_decompress_use_matching_types(api):
    api.session.queue(ok())
    assert api.compress_files("d", "u", "/out.zip", ["/a"]) is True
    assert api.session.calls[-1]["json"] == {
        "type": 1, "code": "utf-8", "source": "/out.zip", "targets": ["/a"],
    }

    api.session.queue(ok())
    assert api.decompress_files("d", "u", "/out.zip", "/dest", code="gbk") is True
    assert api.session.calls[-1]["json"] == {
        "type": 2, "code": "gbk", "source": "/out.zip", "targets": "/dest",
    }


def test_progress_reader_reports_progress(tmp_path):
    path = tmp_path / "data.bin"
    path.write_bytes(b"0123456789")
    seen = []

    reader = _ProgressReader(str(path), lambda pos, total: seen.append((pos, total)))
    assert len(reader) == 10
    assert reader.read(4) == b"0123"
    assert reader.read() == b"456789"
    assert reader.read() == b""
    reader.close()

    assert seen == [(4, 10), (10, 10)]


def test_upload_file_missing_local_file(api, tmp_path):
    assert api.upload_file(str(tmp_path / "nope.txt"), "/", "d", "u") is False


def test_upload_file_requires_stream_channel(api, tmp_path):
    local = tmp_path / "a.txt"
    local.write_text("hi", encoding="utf-8")

    api.session.queue(FakeResponse(payload={"status": 500}))
    assert api.upload_file(str(local), "/", "d", "u") is False

    api.session.queue(ok({"password": "pw"}))
    assert api.upload_file(str(local), "/", "d", "u") is False


def test_upload_file_posts_to_stream_channel(api, tmp_path, monkeypatch):
    local = tmp_path / "a.txt"
    local.write_text("hi", encoding="utf-8")
    api.session.queue(ok({"password": "pw", "addr": "wss://node:1/x"}))

    posted = {}

    def fake_post(url, files=None, headers=None, timeout=None):
        posted["url"] = url
        posted["name"] = files["file"][0]
        return FakeResponse()

    monkeypatch.setattr("mcsm_tools.api.requests.post", fake_post)

    assert api.upload_file(str(local), "/plugins", "d", "u") is True
    assert posted["url"] == "https://node:1/x/upload/pw"
    assert posted["name"] == "a.txt"


def test_upload_file_returns_false_on_transport_error(api, tmp_path, monkeypatch):
    local = tmp_path / "a.txt"
    local.write_text("hi", encoding="utf-8")
    api.session.queue(ok({"password": "pw", "addr": "node:1"}))
    monkeypatch.setattr("mcsm_tools.api.requests.post", lambda *a, **k: (_ for _ in ()).throw(requests.ConnectionError()))

    assert api.upload_file(str(local), "/", "d", "u") is False


def test_download_file_writes_content(api, tmp_path, monkeypatch):
    api.session.queue(ok({"password": "pw", "addr": "wss://node:1"}))
    target = tmp_path / "nested" / "server.properties"
    seen = []

    class StreamResponse(FakeResponse):
        def iter_content(self, chunk_size=None):
            yield b"abc"
            yield b""
            yield b"def"

    def fake_get(url, timeout=None, stream=False):
        seen.append(url)
        response = StreamResponse(text="")
        response.headers["content-length"] = "6"
        return response

    monkeypatch.setattr("mcsm_tools.api.requests.get", fake_get)
    progress = []

    assert api.download_file("d", "u", "/server.properties", str(target),
                             lambda done, total: progress.append((done, total))) is True
    assert seen == ["https://node:1/download/pw/server.properties"]
    assert target.read_bytes() == b"abcdef"
    assert progress == [(3, 6), (6, 6)]


def test_download_file_requires_stream_channel(api, tmp_path):
    api.session.queue(FakeResponse(payload={"status": 500}))
    assert api.download_file("d", "u", "/a", str(tmp_path / "a")) is False

    api.session.queue(ok({"addr": "node"}))
    assert api.download_file("d", "u", "/a", str(tmp_path / "a")) is False


def test_download_file_returns_false_on_transport_error(api, tmp_path, monkeypatch):
    api.session.queue(ok({"password": "pw", "addr": "node:1"}))
    monkeypatch.setattr("mcsm_tools.api.requests.get", lambda *a, **k: (_ for _ in ()).throw(requests.Timeout()))

    assert api.download_file("d", "u", "/a", str(tmp_path / "a")) is False
