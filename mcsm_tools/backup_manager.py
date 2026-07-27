import json
import os
import shutil
import tempfile
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime

from .font_helper import MONO_FONT
from .theme import Nord


BACKUP_DIR = os.path.expanduser(os.path.join("~", ".mcsm_tools", "backups"))
BACKUP_INDEX = os.path.join(BACKUP_DIR, "index.json")


def _ensure_dir():
    os.makedirs(BACKUP_DIR, exist_ok=True)


def _load_index() -> list[dict]:
    _ensure_dir()
    if not os.path.exists(BACKUP_INDEX):
        return []
    try:
        with open(BACKUP_INDEX, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_index(index: list[dict]):
    _ensure_dir()
    try:
        with open(BACKUP_INDEX, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _format_size(size: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


class BackupManagerTab:
    def __init__(self, notebook, app):
        self.app = app
        self.frame = ttk.Frame(notebook)
        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        toolbar = ttk.Frame(self.frame)
        toolbar.pack(fill=tk.X, padx=8, pady=6)

        ttk.Button(toolbar, text="创建备份", command=self._create_backup).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="删除备份", command=self._delete_backup).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="刷新列表", command=self._refresh_list).pack(side=tk.LEFT, padx=2)

        self._status_label = ttk.Label(toolbar, text="")
        self._status_label.pack(side=tk.RIGHT, padx=6)

        self._tree = ttk.Treeview(self.frame,
                                   columns=("name", "size", "time", "desc"),
                                   show="headings")
        self._tree.heading("name", text="文件名")
        self._tree.heading("size", text="大小")
        self._tree.heading("time", text="备份时间")
        self._tree.heading("desc", text="描述")
        self._tree.column("name", width=200)
        self._tree.column("size", width=80, anchor=tk.E)
        self._tree.column("time", width=140)
        self._tree.column("desc", width=200)
        self._tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 6))

        scroll = ttk.Scrollbar(self.frame, orient=tk.VERTICAL, command=self._tree.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._tree.configure(yscrollcommand=scroll.set)

        self._progress_bar = ttk.Progressbar(self.frame, mode='determinate')
        self._progress_bar.pack(fill=tk.X, padx=8, pady=(0, 2))

        self._progress_label = ttk.Label(self.frame, text="")
        self._progress_label.pack(pady=(0, 6))

    def _refresh_list(self):
        self._tree.delete(*self._tree.get_children())
        index = _load_index()
        for entry in reversed(index):
            name = entry.get("name", "?")
            size = entry.get("size", 0)
            time_str = entry.get("time", "")
            desc = entry.get("desc", "")
            self._tree.insert("", tk.END,
                              values=(name, _format_size(size), time_str, desc))
        self._status_label.config(text=f"共 {len(index)} 个备份")

    def _create_backup(self):
        if not self.app._daemon_id or not self.app._instance_uuid:
            messagebox.showwarning("未配置", "请先配置实例")
            return
        if not self.app.api.is_authenticated:
            messagebox.showwarning("未登录", "请先登录")
            return

        dialog = tk.Toplevel(self.app.root)
        dialog.title("创建备份")
        dialog.transient(self.app.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        dialog.config(bg=Nord.bg)
        w, h = 400, 220
        sw = dialog.winfo_screenwidth()
        sh = dialog.winfo_screenheight()
        dialog.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="选择需要备份的目录（可多选）:").pack(anchor=tk.W, pady=(0, 8))

        options = ["world", "worlds", "plugins", "mods", "backups", "config", "scripts"]
        vars = {}
        for opt in options:
            v = tk.BooleanVar(value=(opt == "world"))
            cb = ttk.Checkbutton(frame, text=opt, variable=v)
            cb.pack(anchor=tk.W, padx=12)
            vars[opt] = v

        ttk.Label(frame, text="描述:").pack(anchor=tk.W, pady=(4, 0))
        desc_var = tk.StringVar()
        ttk.Entry(frame, textvariable=desc_var).pack(fill=tk.X, pady=(2, 8))

        btn_frame = ttk.Frame(frame)
        btn_frame.pack()

        result = [None]

        def on_ok():
            selected = [k for k, v in vars.items() if v.get()]
            if not selected:
                messagebox.showwarning("选择目录", "请至少选择一个目录", parent=dialog)
                return
            result[0] = (selected, desc_var.get().strip())
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        ttk.Button(btn_frame, text="开始备份", command=on_ok).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="取消", command=on_cancel).pack(side=tk.LEFT, padx=4)
        dialog.protocol("WM_DELETE_WINDOW", on_cancel)
        dialog.wait_window()

        if result[0] is None:
            return

        selected, desc = result[0]
        self._do_backup(selected, desc)

    def _do_backup(self, selected_dirs: list[str], desc: str):
        self._progress_label.config(text="正在创建压缩包...")
        self._progress_bar["value"] = 0

        def progress(cur, total):
            pct = int(cur / total * 100) if total > 0 else 0
            self.app.root.after(0, lambda: self._progress_bar.configure(value=pct))

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"backup_{timestamp}.zip"
        archive_name = f"backup_{timestamp}"
        remote_dir = "/"
        archive_path = f"/{archive_name}"

        def do_backup():
            try:
                targets = [f"/{d}" for d in selected_dirs]
                ok = self.app.api.compress_files(
                    self.app._daemon_id, self.app._instance_uuid,
                    archive_path, targets
                )
                if not ok:
                    self.app.root.after(0, lambda: self._on_backup_error("压缩失败: 服务器返回错误"))
                    return

                self.app.root.after(0, lambda: self._progress_label.config(text="正在下载备份..."))
                self.app.root.after(0, lambda: self._progress_bar.configure(value=0))

                _ensure_dir()
                local_path = os.path.join(BACKUP_DIR, name)

                ok = self.app.api.download_file(
                    self.app._daemon_id, self.app._instance_uuid,
                    archive_path, local_path,
                    progress_callback=progress
                )

                self.app.api.delete_files(
                    self.app._daemon_id, self.app._instance_uuid,
                    [archive_path]
                )

                if not ok:
                    self.app.root.after(0, lambda: self._on_backup_error("下载失败"))
                    return

                size = os.path.getsize(local_path)
                index = _load_index()
                index.append({
                    "name": name,
                    "size": size,
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "desc": desc,
                    "dirs": selected_dirs,
                })
                _save_index(index)

                self.app.root.after(0, lambda: self._on_backup_done(name))
            except Exception as e:
                self.app.root.after(0, lambda err=str(e): self._on_backup_error(err))

        threading.Thread(target=do_backup, daemon=True).start()

    def _on_backup_done(self, name: str):
        self._progress_label.config(text="")
        self._progress_bar["value"] = 0
        self._refresh_list()
        self.app._set_status(f"备份完成: {name}")
        messagebox.showinfo("备份完成", f"备份已保存到本地\n文件名: {name}")

    def _on_backup_error(self, msg: str):
        self._progress_label.config(text="")
        self._progress_bar["value"] = 0
        self.app._set_status(f"备份失败: {msg}")
        messagebox.showerror("备份失败", msg)

    def _delete_backup(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("选择备份", "请先选择一个备份")
            return
        item = self._tree.item(sel[0])
        name = item["values"][0]
        if not messagebox.askyesno("确认删除", f"确定要删除备份 '{name}' 吗？\n此操作不可恢复。"):
            return
        index = _load_index()
        index = [e for e in index if e.get("name") != name]
        _save_index(index)
        local_path = os.path.join(BACKUP_DIR, name)
        if os.path.exists(local_path):
            os.remove(local_path)
        self._refresh_list()
        self.app._set_status(f"已删除备份: {name}")
