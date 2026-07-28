import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime

from .theme import Nord


REMOTE_BACKUP_DIR = "/backups"


def _format_size(size: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _parse_mtime(mtime) -> str:
    if not mtime:
        return "-"
    from datetime import datetime
    if isinstance(mtime, (int, float)):
        return datetime.fromtimestamp(mtime / 1000 if mtime > 1e10 else mtime).strftime("%Y-%m-%d %H:%M:%S")
    return str(mtime)[:19]


def _get_name(item: dict) -> str:
    return item.get("name", "?")


def _is_file(item: dict) -> bool:
    v = item.get("isFile", item.get("type", ""))
    if isinstance(v, bool):
        return v
    if isinstance(v, int):
        return v == 1
    return v == "file"


class BackupManagerTab:
    def __init__(self, notebook, app):
        self.app = app
        self.frame = ttk.Frame(notebook)
        self._remote_items: list[dict] = []
        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        toolbar = ttk.Frame(self.frame)
        toolbar.pack(fill=tk.X, padx=8, pady=6)

        ttk.Button(toolbar, text="创建备份", command=self._create_backup).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="下载", command=self._download_backup).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="删除", command=self._delete_backup).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="刷新", command=self._refresh_list).pack(side=tk.LEFT, padx=2)

        self._status_label = ttk.Label(toolbar, text="")
        self._status_label.pack(side=tk.RIGHT, padx=6)

        self._tree = ttk.Treeview(self.frame,
                                   columns=("name", "size", "time"),
                                   show="headings")
        self._tree.heading("name", text="文件名")
        self._tree.heading("size", text="大小")
        self._tree.heading("time", text="修改时间")
        self._tree.column("name", width=280)
        self._tree.column("size", width=100, anchor=tk.E)
        self._tree.column("time", width=160)
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
        if not self.app._daemon_id or not self.app._instance_uuid:
            self._tree.insert("", tk.END, values=("请先配置实例", "", ""))
            return
        if not self.app.api.is_authenticated:
            self._tree.insert("", tk.END, values=("请先登录", "", ""))
            return

        self._status_label.config(text="正在读取...")

        def do_list():
            try:
                items = self.app.api.list_files(
                    self.app._daemon_id, self.app._instance_uuid,
                    REMOTE_BACKUP_DIR
                )
                self.app.root.after(0, lambda: self._on_listed(items))
            except Exception as e:
                self.app.root.after(0, lambda err=str(e): self._on_list_error(err))

        threading.Thread(target=do_list, daemon=True).start()

    def _on_listed(self, items):
        self._tree.delete(*self._tree.get_children())
        if items is None:
            self._tree.insert("", tk.END,
                              values=(f"无法读取 {REMOTE_BACKUP_DIR}", "", "目录可能不存在"))
            self._status_label.config(text="目录不存在")
            return

        self._remote_items = [it for it in items if _is_file(it) and _get_name(it) not in (".", "..")]
        self._remote_items.sort(key=lambda it: it.get("mtime", 0), reverse=True)

        for item in self._remote_items:
            name = _get_name(item)
            size = _format_size(item.get("size", 0) or 0)
            mtime = _parse_mtime(item.get("mtime", 0))
            self._tree.insert("", tk.END, values=(name, size, mtime))

        self._status_label.config(text=f"{REMOTE_BACKUP_DIR}  —  共 {len(self._remote_items)} 个备份")

    def _on_list_error(self, err: str):
        self._tree.delete(*self._tree.get_children())
        self._tree.insert("", tk.END, values=("加载失败", "", err))
        self._status_label.config(text="加载失败")

    def _get_selected_name(self) -> str | None:
        sel = self._tree.selection()
        if not sel:
            return None
        return self._tree.item(sel[0])["values"][0]

    def _get_selected_remote_path(self) -> str | None:
        name = self._get_selected_name()
        if not name:
            return None
        return f"{REMOTE_BACKUP_DIR}/{name}"

    def _create_backup(self):
        if not self.app._daemon_id or not self.app._instance_uuid:
            messagebox.showwarning("未配置", "请先配置实例")
            return
        if not self.app.api.is_authenticated:
            messagebox.showwarning("未登录", "请先登录")
            return

        dialog = tk.Toplevel(self.app.root)
        dialog.title("创建服务端备份")
        dialog.transient(self.app.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        dialog.config(bg=Nord.bg)
        w, h = 420, 260
        sw = dialog.winfo_screenwidth()
        sh = dialog.winfo_screenheight()
        dialog.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="选择需要备份的目录（可多选）:").pack(anchor=tk.W, pady=(0, 8))

        options = ["world", "worlds", "plugins", "mods", "config", "scripts"]
        vars = {}
        for opt in options:
            v = tk.BooleanVar(value=(opt == "world"))
            cb = ttk.Checkbutton(frame, text=opt, variable=v)
            cb.pack(anchor=tk.W, padx=12)
            vars[opt] = v

        ttk.Label(frame, text="备份文件名:").pack(anchor=tk.W, pady=(4, 0))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name_var = tk.StringVar(value=f"backup_{timestamp}.zip")
        ttk.Entry(frame, textvariable=name_var).pack(fill=tk.X, pady=(2, 8))

        btn_frame = ttk.Frame(frame)
        btn_frame.pack()

        result = [None]

        def on_ok():
            selected = [k for k, v in vars.items() if v.get()]
            if not selected:
                messagebox.showwarning("选择目录", "请至少选择一个目录", parent=dialog)
                return
            result[0] = (selected, name_var.get().strip())
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        ttk.Button(btn_frame, text="开始备份", command=on_ok).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="取消", command=on_cancel).pack(side=tk.LEFT, padx=4)
        dialog.protocol("WM_DELETE_WINDOW", on_cancel)
        dialog.wait_window()

        if result[0] is None:
            return

        selected, name = result[0]
        if not name.endswith(".zip"):
            name += ".zip"

        self._do_backup(selected, name)

    def _do_backup(self, selected_dirs: list[str], name: str):
        self._progress_label.config(text="正在创建压缩包...")
        self._progress_bar["value"] = 0

        archive_path = f"{REMOTE_BACKUP_DIR}/{name}"
        targets = [f"/{d}" for d in selected_dirs]

        def do_backup():
            try:
                ok = self.app.api.compress_files(
                    self.app._daemon_id, self.app._instance_uuid,
                    archive_path, targets
                )
                if ok:
                    self.app.root.after(0, lambda: self._on_backup_done(name))
                else:
                    self.app.root.after(0, lambda: self._on_backup_error("压缩失败: 服务器返回错误"))
            except Exception as e:
                self.app.root.after(0, lambda err=str(e): self._on_backup_error(err))

        threading.Thread(target=do_backup, daemon=True).start()

    def _on_backup_done(self, name: str):
        self._progress_label.config(text="")
        self._progress_bar["value"] = 0
        self._refresh_list()
        self.app._set_status(f"备份完成: {name}")
        messagebox.showinfo("备份完成", f"备份已保存到服务器 {REMOTE_BACKUP_DIR}/{name}")

    def _on_backup_error(self, msg: str):
        self._progress_label.config(text="")
        self._progress_bar["value"] = 0
        self.app._set_status(f"备份失败: {msg}")
        messagebox.showerror("备份失败", msg)

    def _download_backup(self):
        remote_path = self._get_selected_remote_path()
        if not remote_path:
            messagebox.showwarning("选择备份", "请先选择一个备份")
            return

        name = self._get_selected_name()
        save_path = filedialog.asksaveasfilename(
            initialdir=os.path.expanduser("~"),
            initialfile=name,
            title="下载备份到本地"
        )
        if not save_path:
            return

        self._progress_label.config(text=f"正在下载: {name}")
        self._progress_bar["value"] = 0

        def do_download():
            def progress(cur, total):
                pct = int(cur / total * 100) if total > 0 else 0
                self.app.root.after(0, lambda: self._progress_bar.configure(value=pct))

            ok = self.app.api.download_file(
                self.app._daemon_id, self.app._instance_uuid,
                remote_path, save_path, progress_callback=progress
            )
            self.app.root.after(0, lambda: self._on_download_result(ok, name))

        threading.Thread(target=do_download, daemon=True).start()

    def _on_download_result(self, ok: bool, name: str):
        self._progress_label.config(text="")
        self._progress_bar["value"] = 0
        if ok:
            self.app._set_status(f"下载成功: {name}")
            messagebox.showinfo("下载完成", f"备份已保存到本地\n{name}")
        else:
            self.app._set_status(f"下载失败: {name}")
            messagebox.showerror("下载失败", f"文件 {name} 下载失败")

    def _delete_backup(self):
        remote_path = self._get_selected_remote_path()
        if not remote_path:
            messagebox.showwarning("选择备份", "请先选择一个备份")
            return

        name = self._get_selected_name()
        if not messagebox.askyesno("确认删除", f"确定要删除服务器上的备份 '{name}' 吗？\n此操作不可恢复。"):
            return

        self._status_label.config(text="正在删除...")

        def do_delete():
            ok = self.app.api.delete_files(
                self.app._daemon_id, self.app._instance_uuid,
                [remote_path]
            )
            self.app.root.after(0, lambda: self._on_delete_result(ok, name))

        threading.Thread(target=do_delete, daemon=True).start()

    def _on_delete_result(self, ok: bool, name: str):
        if ok:
            self._status_label.config(text=f"已删除: {name}")
            self._refresh_list()
        else:
            self._status_label.config(text=f"删除失败: {name}")
            messagebox.showerror("删除失败", f"删除 '{name}' 失败")
