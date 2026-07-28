import os
import sys
import traceback
import requests


HEADERS_TEMPLATE = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/json; charset=utf-8",
}


class _ProgressReader:
    def __init__(self, filepath: str, callback):
        self._file = open(filepath, 'rb')
        self._total = os.path.getsize(filepath)
        self._pos = 0
        self._callback = callback

    def read(self, size=-1):
        chunk = self._file.read(size)
        if chunk:
            self._pos += len(chunk)
            if self._callback:
                self._callback(self._pos, self._total)
        return chunk

    def __len__(self):
        return self._total

    def close(self):
        self._file.close()


class MCSManagerAPI:
    def __init__(self, base_url: str = "https://mcsm.rainyun.com"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.token = ""
        self.cookie = ""
        self.apikey = ""
        self.last_error = ""
        self._update_headers()

    def _update_headers(self):
        self.session.headers.update(HEADERS_TEMPLATE)
        self.session.headers["Origin"] = self.base_url
        self.session.headers["Referer"] = f"{self.base_url}/"
        self.session.headers["User-Agent"] = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0"
        )

    def _clear_auth_headers(self):
        self.session.headers.pop("Cookie", None)
        self.session.headers.pop("Authorization", None)
        self.session.headers.pop("x-request-api-key", None)

    def set_auth(self, token: str, cookie: str):
        """Use session token + cookie for auth"""
        self.token = token
        self.cookie = cookie
        self.apikey = ""
        self._clear_auth_headers()
        if cookie:
            self.session.headers["Cookie"] = cookie

    def set_apikey(self, apikey: str):
        """Use API Key for auth (query param + header)"""
        self.apikey = apikey
        self.token = ""
        self.cookie = ""
        self._clear_auth_headers()
        self.session.headers["x-request-api-key"] = apikey

    def refresh_auth_from_config(self, cfg) -> bool:
        if cfg.apikey:
            self.set_apikey(cfg.apikey)
            return True
        elif cfg.token and cfg.cookie:
            self.set_auth(cfg.token, cfg.cookie)
            return True
        elif cfg.username and cfg.password:
            return self.login(cfg.username, cfg.password)
        return False

    @property
    def is_authenticated(self) -> bool:
        return bool(self.apikey) or (bool(self.token) and bool(self.cookie))

    def _build_url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _merge_auth_params(self, params: dict | None = None) -> dict:
        params = dict(params or {})
        if self.apikey:
            params['apikey'] = self.apikey
            params['token'] = self.apikey
        elif self.token:
            params['token'] = self.token
        return params

    def _request(self, method: str, path: str, params: dict | None = None,
                 json_data: dict | None = None) -> dict | None:
        self.last_error = ""
        try:
            url = self._build_url(path)
            merged = self._merge_auth_params(params)
            resp = self.session.request(
                method,
                url,
                params=merged,
                json=json_data,
                timeout=15,
            )
            if resp.status_code >= 400:
                try:
                    body = resp.text[:2000]
                except Exception:
                    body = resp.content[:2000].hex()
                self.last_error = f"HTTP {resp.status_code}: {body}"
                return None
            ct = resp.headers.get('content-type', '')
            if 'json' in ct:
                return resp.json()
            return {"status": 200, "data": resp.text}
        except requests.ConnectionError:
            self.last_error = f"连接失败: {self._build_url(path)}"
            return None
        except requests.Timeout:
            self.last_error = "请求超时"
            return None
        except requests.RequestException as e:
            self.last_error = f"请求错误: {e}"
            return None
        except Exception as e:
            print(f"[MCSManagerAPI] 未知错误: {e}", file=sys.stderr)
            traceback.print_exc()
            self.last_error = f"未知错误: {e}"
            return None

    def _get(self, path: str, params: dict | None = None) -> dict | None:
        return self._request("GET", path, params=params)

    def _post(self, path: str, params: dict | None = None, json_data: dict | None = None) -> dict | None:
        return self._request("POST", path, params=params, json_data=json_data)

    def _put(self, path: str, params: dict | None = None, json_data: dict | None = None) -> dict | None:
        return self._request("PUT", path, params=params, json_data=json_data)

    def _delete(self, path: str, params: dict | None = None, json_data: dict | None = None) -> dict | None:
        return self._request("DELETE", path, params=params, json_data=json_data)

    # ==================== Auth ====================

    def login_with_apikey(self, apikey: str) -> bool:
        self.set_apikey(apikey)
        if self.validate_credentials():
            return True
        self.apikey = ""
        self.token = ""
        self.cookie = ""
        self._clear_auth_headers()
        return False

    def login(self, username: str, password: str) -> bool:
        self.last_error = ""
        self._clear_auth_headers()
        payload = {"username": username, "password": password}
        try:
            resp = self.session.post(
                self._build_url("/api/auth/login"),
                json=payload,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") != 200:
                self.last_error = f"登录被拒绝: {data.get('data') or data.get('status')}"
                return False

            token = None
            if "token" in data.get("data", {}):
                token = data["data"]["token"]
            elif "token" in data:
                token = data["token"]

            if not token:
                info_resp = self.session.get(
                    self._build_url("/api/auth/"),
                    params={"advanced": "true"},
                    timeout=15,
                )
                if info_resp.status_code == 200:
                    info_data = info_resp.json()
                    if info_data.get("status") == 200:
                        token = info_data.get("data", {}).get("token")

            if not token:
                self.last_error = "登录成功但未能获取 token（账号或密码可能有误）"
                return False

            cookie_str = "; ".join(f"{k}={v}" for k, v in self.session.cookies.get_dict().items())
            self.set_auth(token, cookie_str)
            return True
        except requests.ConnectionError:
            self.last_error = f"连接失败: {self._build_url('/api/auth/login')}"
            return False
        except requests.Timeout:
            self.last_error = "请求超时"
            return False
        except requests.RequestException as e:
            self.last_error = f"登录请求错误: {e}"
            return False
        except ValueError as e:
            self.last_error = f"登录响应解析失败: {e}"
            return False

    def validate_credentials(self) -> bool:
        data = self._get("/api/auth/", {"advanced": "true"})
        return data is not None and data.get("status") == 200

    # ==================== Instances ====================

    def list_instances(self) -> list[dict]:
        data = self._get("/api/auth/", {"advanced": "true"})
        if data and data.get("status") == 200:
            return data.get("data", {}).get("instances", [])
        return []

    def auto_discover_instance(self, target_name: str | None = None) -> tuple[str, str] | None:
        instances = self.list_instances()
        if not instances:
            return None

        target = None
        if target_name:
            for inst in instances:
                if inst.get("nickname") == target_name:
                    target = inst
                    break

        if not target:
            for inst in instances:
                if inst.get("status") in [1, 2, 3]:
                    target = inst
                    break

        if not target and instances:
            target = instances[0]

        if not target:
            return None

        daemon_id = target.get("daemonId")
        instance_uuid = target.get("instanceUuid")
        if daemon_id and instance_uuid:
            return daemon_id, instance_uuid
        return None

    def get_instance_info(self, daemon_id: str, instance_uuid: str) -> dict | None:
        data = self._get("/api/instance", {
            "uuid": instance_uuid,
            "daemonId": daemon_id,
        })
        if data and data.get("status") == 200:
            return data.get("data", {})
        return None

    def get_instance_status(self, daemon_id: str, instance_uuid: str) -> dict:
        result = {"status": -1, "text": "未知", "addr": ""}

        instances = self.list_instances()
        if instances:
            for inst in instances:
                if inst.get("instanceUuid") == instance_uuid and inst.get("daemonId") == daemon_id:
                    status_val = inst.get("status", -1)
                    ip = inst.get("ip", "")
                    port = inst.get("port", "")
                    result["addr"] = f"{ip}:{port}" if ip and port else ""
                    result["status"] = status_val
                    result["text"] = self._status_text(status_val)
                    return result

        info = self.get_instance_info(daemon_id, instance_uuid)
        if info:
            instance = info.get("instance", info)
            status_val = instance.get("status", -1)
            ip = instance.get("ip", "")
            port = instance.get("port", "")
            result["addr"] = f"{ip}:{port}" if ip and port else ""
            result["status"] = status_val
            result["text"] = self._status_text(status_val)

        return result

    @staticmethod
    def _status_text(status_val: int) -> str:
        if status_val == 0:
            return "已停止"
        if status_val == 1:
            return "运行中"
        if status_val == 2:
            return "启动中"
        if status_val == 3:
            return "停止中"
        return "未知"

    def kill_instance(self, daemon_id: str, instance_uuid: str) -> bool:
        data = self._get("/api/protected_instance/kill", {
            "uuid": instance_uuid,
            "daemonId": daemon_id,
        })
        return data is not None and data.get("status") == 200

    def open_instance(self, daemon_id: str, instance_uuid: str) -> bool:
        data = self._get("/api/protected_instance/open", {
            "uuid": instance_uuid,
            "daemonId": daemon_id,
        })
        return data is not None and data.get("status") == 200

    def stop_instance(self, daemon_id: str, instance_uuid: str) -> bool:
        data = self._get("/api/protected_instance/stop", {
            "uuid": instance_uuid,
            "daemonId": daemon_id,
        })
        return data is not None and data.get("status") == 200

    def restart_instance(self, daemon_id: str, instance_uuid: str) -> bool:
        data = self._get("/api/protected_instance/restart", {
            "uuid": instance_uuid,
            "daemonId": daemon_id,
        })
        return data is not None and data.get("status") == 200

    def get_websocket_password(self, daemon_id: str, instance_uuid: str) -> tuple[str, str] | None:
        data = self._post("/api/protected_instance/stream_channel", {
            "daemonId": daemon_id,
            "uuid": instance_uuid,
        })
        if data and data.get("status") == 200:
            d = data.get("data", {})
            password = d.get("password")
            addr = d.get("addr")
            if password and addr:
                return password, addr
        return None

    # ==================== Files ====================

    def list_files(self, daemon_id: str, instance_uuid: str, path: str = "/") -> list[dict] | None:
        data = self._get("/api/files/list", {
            "daemonId": daemon_id,
            "uuid": instance_uuid,
            "target": path,
            "page": 0,
            "page_size": 100,
            "file_name": "",
        })
        if data and data.get("status") == 200:
            d = data.get("data")
            if isinstance(d, list):
                return d
            if isinstance(d, dict):
                items = d.get("items")
                if items is not None:
                    return items
                return list(d.values())
        return None

    def upload_file(self, local_path: str, remote_dir: str,
                    daemon_id: str, instance_uuid: str,
                    progress_callback=None) -> bool:
        self.last_error = ""
        if not os.path.exists(local_path):
            self.last_error = f"本地文件不存在: {local_path}"
            return False

        file_name = os.path.basename(local_path)

        data = self._post("/api/files/upload", {
            "daemonId": daemon_id,
            "uuid": instance_uuid,
            "upload_dir": remote_dir,
        })
        if not data:
            return False
        if data.get("status") != 200:
            self.last_error = f"申请上传通道失败: {data.get('data') or data.get('status')}"
            return False

        d = data.get("data", {})
        upload_password = d.get("password")
        upload_addr = d.get("addr")
        if not upload_password or not upload_addr:
            self.last_error = "服务器未返回上传地址或密码"
            return False

        upload_url = upload_addr.replace("wss://", "https://")
        if not upload_url.startswith("http"):
            upload_url = f"https://{upload_url}"
        upload_url = f"{upload_url}/upload/{upload_password}"

        try:
            reader = _ProgressReader(local_path, progress_callback)
        except OSError as e:
            self.last_error = f"读取本地文件失败: {e}"
            return False
        try:
            files = {'file': (file_name, reader, 'application/octet-stream')}
            headers = {
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json, text/plain, */*",
            }
            resp = requests.post(upload_url, files=files, headers=headers, timeout=120)
            if resp.status_code != 200:
                self.last_error = f"上传失败 HTTP {resp.status_code}: {resp.text[:500]}"
                return False
            return True
        except requests.RequestException as e:
            self.last_error = f"上传请求错误: {e}"
            return False
        finally:
            reader.close()

    def download_file(self, daemon_id: str, instance_uuid: str,
                      file_path: str, local_path: str,
                      progress_callback=None) -> bool:
        self.last_error = ""
        data = self._post("/api/files/download", {
            "daemonId": daemon_id,
            "uuid": instance_uuid,
            "file_name": file_path,
        })
        if not data:
            return False
        if data.get("status") != 200:
            self.last_error = f"申请下载通道失败: {data.get('data') or data.get('status')}"
            return False

        d = data.get("data", {})
        password = d.get("password")
        addr = d.get("addr")
        if not password or not addr:
            self.last_error = "服务器未返回下载地址或密码"
            return False

        download_addr = addr.replace("wss://", "https://")
        if not download_addr.startswith("http"):
            download_addr = f"https://{download_addr}"

        file_name = os.path.basename(file_path)
        download_url = f"{download_addr}/download/{password}/{file_name}"

        try:
            resp = requests.get(download_url, timeout=60, stream=True)
            resp.raise_for_status()

            total = int(resp.headers.get('content-length', 0))
            downloaded = 0

            os.makedirs(os.path.dirname(local_path) or '.', exist_ok=True)
            with open(local_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            progress_callback(downloaded, total)
            return True
        except requests.RequestException as e:
            self.last_error = f"下载请求错误: {e}"
            return False
        except OSError as e:
            self.last_error = f"写入本地文件失败: {e}"
            return False

    def delete_files(self, daemon_id: str, instance_uuid: str, targets: list[str]) -> bool:
        data = self._delete("/api/files", {
            "daemonId": daemon_id,
            "uuid": instance_uuid,
        }, json_data={"targets": targets})
        return data is not None and data.get("status") == 200

    def create_directory(self, daemon_id: str, instance_uuid: str, dir_path: str) -> bool:
        data = self._post("/api/files/mkdir", {
            "daemonId": daemon_id,
            "uuid": instance_uuid,
        }, json_data={"target": dir_path})
        return data is not None and data.get("status") == 200

    def move_files(self, daemon_id: str, instance_uuid: str, targets: list[list[str]]) -> bool:
        data = self._put("/api/files/move", {
            "daemonId": daemon_id,
            "uuid": instance_uuid,
        }, json_data={"targets": targets})
        return data is not None and data.get("status") == 200

    def get_file_info(self, daemon_id: str, instance_uuid: str, file_path: str) -> dict | None:
        data = self._get("/api/files/info", {
            "daemonId": daemon_id,
            "uuid": instance_uuid,
            "target": file_path,
        })
        if data and data.get("status") == 200:
            return data.get("data", {})
        return None

    def touch_file(self, daemon_id: str, instance_uuid: str, file_path: str) -> bool:
        data = self._post("/api/files/touch", {
            "daemonId": daemon_id,
            "uuid": instance_uuid,
        }, json_data={"target": file_path})
        return data is not None and data.get("status") == 200

    def decompress_files(self, daemon_id: str, instance_uuid: str,
                         source: str, target_dir: str,
                         code: str = "utf-8") -> bool:
        data = self._post("/api/files/compress", {
            "daemonId": daemon_id,
            "uuid": instance_uuid,
        }, json_data={"type": 2, "code": code, "source": source, "targets": target_dir})
        return data is not None and data.get("status") == 200

    def compress_files(self, daemon_id: str, instance_uuid: str,
                       source: str, targets: list[str],
                       code: str = "utf-8") -> bool:
        data = self._post("/api/files/compress", {
            "daemonId": daemon_id,
            "uuid": instance_uuid,
        }, json_data={"type": 1, "code": code, "source": source, "targets": targets})
        return data is not None and data.get("status") == 200
