import json
import os
import threading
import tempfile
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog



SERVER_FILES = {
    "whitelist": "whitelist.json",
    "ops": "ops.json",
    "banned-players": "banned-players.json",
    "banned-ips": "banned-ips.json",
}


class PlayerManagerTab:
    def __init__(self, notebook, app):
        self.app = app
        self.frame = ttk.Frame(notebook)
        self._current_file = "whitelist"
        self._player_data: list[dict] = []
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        toolbar = ttk.Frame(self.frame)
        toolbar.pack(fill=tk.X, padx=8, pady=6)

        ttk.Label(toolbar, text="管理列表:").pack(side=tk.LEFT)
        self._file_var = tk.StringVar(value="whitelist")
        cb = ttk.Combobox(toolbar, textvariable=self._file_var,
                          values=list(SERVER_FILES.keys()),
                          state="readonly", width=16)
        cb.pack(side=tk.LEFT, padx=4)
        cb.bind("<<ComboboxSelected>>", lambda e: self._switch_file())

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        self._btn_add = ttk.Button(toolbar, text="添加", command=self._add_player)
        self._btn_add.pack(side=tk.LEFT, padx=2)
        self._btn_remove = ttk.Button(toolbar, text="移除", command=self._remove_player)
        self._btn_remove.pack(side=tk.LEFT, padx=2)
        self._btn_save = ttk.Button(toolbar, text="保存到服务器", command=self._save_to_server)
        self._btn_save.pack(side=tk.LEFT, padx=2)
        self._btn_refresh = ttk.Button(toolbar, text="刷新", command=self._load_data)
        self._btn_refresh.pack(side=tk.LEFT, padx=2)

        self._status_label = ttk.Label(toolbar, text="")
        self._status_label.pack(side=tk.RIGHT, padx=6)

        columns = ("name", "uuid", "created", "source")
        self._tree = ttk.Treeview(self.frame, columns=columns, show="headings")
        self._tree.heading("name", text="玩家名")
        self._tree.heading("uuid", text="UUID")
        self._tree.heading("created", text="添加时间")
        self._tree.heading("source", text="来源")
        self._tree.column("name", width=150)
        self._tree.column("uuid", width=220)
        self._tree.column("created", width=140)
        self._tree.column("source", width=100)
        self._tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 6))

        scroll = ttk.Scrollbar(self.frame, orient=tk.VERTICAL, command=self._tree.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._tree.configure(yscrollcommand=scroll.set)

        self._tree.bind("<Double-1>", lambda e: self._edit_player())

    def _switch_file(self):
        self._current_file = self._file_var.get()
        self._load_data()

    def _get_remote_path(self) -> str:
        return f"/{SERVER_FILES[self._current_file]}"

    def _load_data(self):
        if not self.app.api.is_authenticated:
            self._tree.delete(*self._tree.get_children())
            self._tree.insert("", tk.END, values=("请先登录", "", "", ""))
            return

        self._status_label.config(text="正在加载...")
        remote_path = self._get_remote_path()

        def do_load():
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
            tmp.close()
            try:
                ok = self.app.api.download_file(
                    self.app._daemon_id, self.app._instance_uuid,
                    remote_path, tmp.name
                )
                if ok:
                    try:
                        with open(tmp.name, encoding="utf-8") as f:
                            data = json.load(f)
                        self._player_data = data if isinstance(data, list) else []
                    except (json.JSONDecodeError, Exception):
                        self._player_data = []
                else:
                    self._player_data = []
            except Exception:
                self._player_data = []
            finally:
                os.unlink(tmp.name)
            self.app.root.after(0, self._refresh_display)

        threading.Thread(target=do_load, daemon=True).start()

    def _refresh_display(self):
        self._tree.delete(*self._tree.get_children())
        for entry in self._player_data:
            name = entry.get("name") or entry.get("uuid", "?")[:8]
            uuid_val = entry.get("uuid", "")
            created = entry.get("created", "")
            source = entry.get("source", "")
            self._tree.insert("", tk.END, values=(name, uuid_val, created, source))
        self._status_label.config(text=f"共 {len(self._player_data)} 条记录")

    def _add_player(self):
        name = simpledialog.askstring("添加", f"输入玩家名（{self._current_file}）:", parent=self.frame)
        if not name:
            return
        name = name.strip()
        new_entry = {"name": name, "uuid": ""}
        if self._current_file in ("whitelist", "ops"):
            from datetime import datetime
            new_entry["uuid"] = simpledialog.askstring("UUID", "输入 UUID（可选，留空自动生成）:", parent=self.frame) or ""
            new_entry["created"] = datetime.now().isoformat()[:19]
        if self._current_file == "ops":
            new_entry["level"] = 4
            new_entry["bypassesPlayerLimit"] = False
        self._player_data.append(new_entry)
        self._refresh_display()
        self._save_to_server()

    def _remove_player(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("选择", "请先选择要移除的玩家")
            return
        item = self._tree.item(sel[0])
        name = item["values"][0]
        if not messagebox.askyesno("确认", f"确定移除 '{name}' 吗？"):
            return
        self._player_data = [e for e in self._player_data
                             if e.get("name") != name and e.get("uuid", "")[:8] != name]
        self._refresh_display()
        self._save_to_server()

    def _edit_player(self):
        sel = self._tree.selection()
        if not sel:
            return
        idx = self._tree.index(sel[0])
        if idx >= len(self._player_data):
            return
        entry = self._player_data[idx]
        name = entry.get("name", "")

        new_name = simpledialog.askstring("编辑", f"修改玩家名（当前: {name}）:",
                                           initialvalue=name, parent=self.frame)
        if new_name is not None and new_name.strip():
            entry["name"] = new_name.strip()
            self._refresh_display()

    def _save_to_server(self):
        if not self.app.api.is_authenticated:
            messagebox.showwarning("未登录", "请先登录")
            return
        if not self._player_data:
            if not messagebox.askyesno("确认", "列表为空，确定要上传空文件覆盖吗？"):
                return

        self._status_label.config(text="正在保存...")
        remote_path = self._get_remote_path()

        def do_save():
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w", encoding="utf-8")
            try:
                json.dump(self._player_data, tmp, ensure_ascii=False, indent=2)
                tmp.close()
                ok = self.app.api.upload_file(
                    tmp.name, os.path.dirname(remote_path),
                    self.app._daemon_id, self.app._instance_uuid,
                )
                self.app.root.after(0, lambda: self._on_save_result(ok))
            except Exception:
                self.app.root.after(0, lambda: self._on_save_result(False))
            finally:
                try:
                    os.unlink(tmp.name)
                except Exception:
                    pass

        threading.Thread(target=do_save, daemon=True).start()

    def _on_save_result(self, ok: bool):
        if ok:
            self._status_label.config(text="保存成功")
            self.app._set_status("玩家列表已保存到服务器")
        else:
            self._status_label.config(text="保存失败")
            messagebox.showerror("保存失败", "无法保存到服务器")
