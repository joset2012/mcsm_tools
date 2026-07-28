import os
import shutil
import subprocess
import tarfile
import tempfile
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

from .font_helper import MONO_FONT
from .system_check import seven_zip_path
from .theme import Nord


EDITABLE_EXTS = {".txt", ".log", ".json", ".yml", ".yaml", ".xml", ".toml",
                 ".cfg", ".conf", ".ini", ".properties", ".sh", ".bat",
                  ".py", ".js", ".ts", ".java", ".html", ".css", ".md",
                  ".env", ".gitignore", ".dockerfile"}

ARCHIVE_EXTS = {".zip", ".tar", ".tar.gz", ".tgz", ".gz", ".7z", ".rar", ".xz", ".bz2"}


ICON_DIR = "📁"
ICON_PARENT = "📁 .."

_EXT_ICONS = {
    "py": "🐍", "js": "🟨", "ts": "🟦", "java": "☕", "jar": "📦",
    "json": "⚙", "yml": "⚙", "yaml": "⚙", "xml": "⚙", "properties": "⚙",
    "toml": "⚙", "cfg": "⚙", "conf": "⚙", "ini": "⚙",
    "log": "📜", "txt": "📄", "md": "📝", "readme": "📖",
    "zip": "🗜", "tar": "🗜", "gz": "🗜", "7z": "🗜", "rar": "🗜",
    "png": "🖼", "jpg": "🖼", "jpeg": "🖼", "gif": "🖼", "svg": "🖼", "ico": "🖼",
    "mp3": "🎵", "ogg": "🎵", "wav": "🎵", "flac": "🎵",
    "mp4": "🎬", "mov": "🎬", "avi": "🎬",
    "html": "🌐", "css": "🎨", "scss": "🎨",
    "sh": "📜", "bat": "📜", "ps1": "📜",
    "db": "🗄", "sql": "🗄", "sqlite": "🗄",
    "pdf": "📕", "doc": "📕", "docx": "📕",
    "exe": "⚡", "msi": "⚡",
    "dll": "🔧", "so": "🔧", "dylib": "🔧",
    "gitignore": "🙈", "gitkeep": "🙈",
    "lock": "🔒",
}

_DEFAULT_ICONS = {
    "dockerfile": "🐳", "makefile": "🔨",
    "license": "📋", "copying": "📋",
    "readme": "📖", "changelog": "📖",
}


def _ext(name: str) -> str:
    _, dot, ext = name.rpartition(".")
    if dot:
        return ext
    return ""


def _get_file_icon(name: str) -> str:
    name_lower = name.lower()
    base, _, _ = name_lower.rpartition(".")
    if base in _DEFAULT_ICONS:
        return _DEFAULT_ICONS[base]
    if name_lower in _DEFAULT_ICONS:
        return _DEFAULT_ICONS[name_lower]
    e = _ext(name_lower)
    return _EXT_ICONS.get(e, "📄")


def _display_name(name: str, is_dir: bool = False) -> str:
    if is_dir or name == "..":
        return f"{ICON_DIR} {name}"
    return f"{_get_file_icon(name)} {name}"


ICON_PREFIXES = tuple(f"{v} " for v in set(list(_EXT_ICONS.values()) + list(_DEFAULT_ICONS.values()) + [ICON_DIR]))


def _strip_icon(display: str) -> str:
    for prefix in (f"{ICON_DIR} ", f"{ICON_PARENT} "):
        if display.startswith(prefix):
            return display[len(prefix):]
    for icon_char in _EXT_ICONS.values():
        p = f"{icon_char} "
        if display.startswith(p):
            return display[len(p):]
    for icon_char in _DEFAULT_ICONS.values():
        p = f"{icon_char} "
        if display.startswith(p):
            return display[len(p):]
    return display


def _is_dir(item: dict) -> bool:
    v = item.get("isFile", item.get("type", ""))
    if isinstance(v, bool):
        return not v
    if isinstance(v, int):
        return v == 0
    return v == "directory"


def _get_name(item: dict) -> str:
    return item.get("name", "?")


def _join_path(parent: str, child: str) -> str:
    if parent.endswith('/'):
        return parent + child
    return parent + '/' + child


def _parent_path(path: str) -> str:
    path = path.rstrip('/')
    if not path:
        return "/"
    parent = os.path.dirname(path)
    return parent if parent else "/"


class FileManagerTab:
    def __init__(self, notebook, app):
        self.app = app
        self.frame = ttk.Frame(notebook)
        self._current_remote_dir = "/"
        self._local_dir = os.path.expanduser("~")
        self._clipboard = None  # {"action": "cut", "path": "..."} or None
        self._remote_items: list[dict] = []
        self._context_menu_open = None
        self._build_ui()
        self.app.root.bind("<Button-1>", self._close_context_menu, "+")

    def _build_ui(self):
        toolbar = ttk.Frame(self.frame)
        toolbar.pack(fill=tk.X, pady=2)

        ttk.Button(toolbar, text="上传", command=self._upload_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="下载", command=self._download_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="编辑", command=self._edit_file).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(toolbar, text="本地编辑", command=self._edit_local_file_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="新建目录", command=self._mkdir).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="删除", command=self._delete_item).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(toolbar, text="下载世界", command=self._download_world).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="返回上级", command=self._go_up).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="刷新", command=self._refresh_remote).pack(side=tk.LEFT, padx=2)

        paned = ttk.Frame(self.frame)
        paned.pack(fill=tk.BOTH, expand=True)
        paned.rowconfigure(0, weight=1)
        paned.columnconfigure(0, weight=1)
        paned.columnconfigure(1, weight=1)

        left_frame = ttk.LabelFrame(paned, text="本地文件")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 2))

        local_path_frame = ttk.Frame(left_frame)
        local_path_frame.pack(fill=tk.X)
        ttk.Label(local_path_frame, text="路径:").pack(side=tk.LEFT)
        self._local_path_label = ttk.Label(local_path_frame, text=self._local_dir, foreground="blue")
        self._local_path_label.pack(side=tk.LEFT, padx=5)

        self._local_tree = ttk.Treeview(left_frame, columns=("size", "modified"), show="tree headings")
        self._local_tree.heading("#0", text="文件名")
        self._local_tree.heading("size", text="大小")
        self._local_tree.heading("modified", text="修改时间")
        self._local_tree.column("#0", width=250)
        self._local_tree.column("size", width=80, anchor=tk.E)
        self._local_tree.column("modified", width=140)
        self._local_tree.pack(fill=tk.BOTH, expand=True)
        self._local_tree.bind("<Double-1>", self._on_local_double_click)
        self._local_tree.bind("<Button-3>", self._on_local_right_click)

        local_scroll = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self._local_tree.yview)
        local_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._local_tree.configure(yscrollcommand=local_scroll.set)

        right_frame = ttk.LabelFrame(paned, text="远程文件")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(2, 0))

        path_frame = ttk.Frame(right_frame)
        path_frame.pack(fill=tk.X)

        ttk.Label(path_frame, text="路径:").pack(side=tk.LEFT)
        self._remote_path_var = tk.StringVar(value="/")
        self._remote_path_entry = ttk.Entry(path_frame, textvariable=self._remote_path_var)
        self._remote_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self._remote_path_entry.bind("<Return>", lambda e: self._navigate_to(self._remote_path_var.get()))
        ttk.Button(path_frame, text="跳转", command=lambda: self._navigate_to(self._remote_path_var.get())).pack(side=tk.LEFT, padx=2)

        self._remote_tree = ttk.Treeview(right_frame, columns=("size", "modified"), show="tree headings")
        self._remote_tree.heading("#0", text="文件名")
        self._remote_tree.heading("size", text="大小")
        self._remote_tree.heading("modified", text="修改时间")
        self._remote_tree.column("#0", width=250)
        self._remote_tree.column("size", width=80, anchor=tk.E)
        self._remote_tree.column("modified", width=140)
        self._remote_tree.pack(fill=tk.BOTH, expand=True)
        self._remote_tree.bind("<Double-1>", self._on_remote_double_click)
        self._remote_tree.bind("<Button-3>", self._on_remote_right_click)

        remote_scroll = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self._remote_tree.yview)
        remote_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._remote_tree.configure(yscrollcommand=remote_scroll.set)

        self._progress_bar = None
        self._progress_label = None

        self._refresh_local()
        self._refresh_remote()

    def _show_progress(self):
        if not self._progress_bar:
            self._progress_bar = ttk.Progressbar(self.frame, mode='determinate')
            self._progress_label = ttk.Label(self.frame, text="")
        self._progress_bar.pack(fill=tk.X, pady=1)
        self._progress_label.pack()

    def _hide_progress(self):
        if self._progress_bar:
            self._progress_bar.pack_forget()
            self._progress_label.pack_forget()

    def _refresh_local(self):
        self._local_tree.delete(*self._local_tree.get_children())
        self._local_path_label.config(text=self._local_dir)
        if self._local_dir != "/":
            self._local_tree.insert("", tk.END, text=ICON_PARENT, values=("", ""))
        try:
            items = os.listdir(self._local_dir)
            dirs = sorted(n for n in items if os.path.isdir(os.path.join(self._local_dir, n)))
            files = sorted(n for n in items if not os.path.isdir(os.path.join(self._local_dir, n)))
            for name in dirs:
                full = os.path.join(self._local_dir, name)
                try:
                    s = os.stat(full)
                    size = self._format_size(s.st_size)
                    mtime = self._format_time(s.st_mtime)
                except OSError:
                    size = "-"
                    mtime = "-"
                self._local_tree.insert("", tk.END, text=_display_name(name, is_dir=True), values=(size, mtime))
            for name in files:
                full = os.path.join(self._local_dir, name)
                try:
                    s = os.stat(full)
                    size = self._format_size(s.st_size)
                    mtime = self._format_time(s.st_mtime)
                except OSError:
                    size = "-"
                    mtime = "-"
                self._local_tree.insert("", tk.END, text=_display_name(name), values=(size, mtime))
        except OSError as e:
            self._local_tree.insert("", tk.END, text=f"错误: {e}")

    def _cut_remote_file(self):
        sel = self._remote_tree.selection()
        if not sel:
            return
        item = self._remote_tree.item(sel[0])
        name = _strip_icon(item["text"])
        if name == "..":
            return
        path = _join_path(self._current_remote_dir, name)
        self._clipboard = {"action": "cut", "path": path}
        self.app._set_status(f"已剪切: {path}")

    def _paste_remote_file(self):
        if not self._clipboard:
            return
        src = self._clipboard["path"]
        dst = _join_path(self._current_remote_dir, os.path.basename(src))
        if src == dst:
            self._clipboard = None
            self._refresh_remote()
            return
        action = self._clipboard["action"]

        def do_paste():
            if action == "cut":
                ok = self.app.api.move_files(
                    self.app._daemon_id, self.app._instance_uuid, [[src, dst]]
                )
            else:
                ok = False
            self.app.root.after(0, lambda: self._on_paste_result(ok))

        self.app._set_status(f"正在粘贴: {os.path.basename(src)}")
        threading.Thread(target=do_paste, daemon=True).start()

    def _on_paste_result(self, ok: bool):
        self._clipboard = None
        if ok:
            self.app._set_status("粘贴成功")
        else:
            self.app._set_status("粘贴失败")
            messagebox.showerror("粘贴失败", "无法移动到目标位置")
        self._refresh_remote()

    def _get_archive_ext(self, name: str) -> str | None:
        lower = name.lower()
        for ext in (".tar.gz", ".tgz"):
            if lower.endswith(ext):
                return ext
        _, ext = os.path.splitext(lower)
        return ext if ext in ARCHIVE_EXTS else None

    def _extract_archive(self):
        sel = self._remote_tree.selection()
        if not sel:
            return
        item = self._remote_tree.item(sel[0])
        name = _strip_icon(item["text"])
        if name == "..":
            return
        ext = self._get_archive_ext(name)
        if not ext:
            return

        remote_path = _join_path(self._current_remote_dir, name)

        if ext == ".zip":
            self._show_progress()
            self._progress_label.config(text=f"正在解压: {name}")
            self._progress_bar["value"] = 0

            def do_zip():
                try:
                    ok = self.app.api.decompress_files(
                        self.app._daemon_id, self.app._instance_uuid,
                        remote_path, self._current_remote_dir
                    )
                    self.app.root.after(0, lambda: self._on_remote_unzip_result(ok, name))
                except Exception as e:
                    self.app.root.after(0, lambda err=str(e): self._on_extract_result(False, err, None))

            threading.Thread(target=do_zip, daemon=True).start()
            return

        seven_zip = seven_zip_path()
        if not seven_zip:
            self._on_extract_result(False, "7-Zip 未安装，无法解压非 .zip 格式", None)
            return

        self._show_progress()
        self._progress_label.config(text=f"正在下载: {name}")
        self._progress_bar["value"] = 0

        tmp_dir = tempfile.mkdtemp(prefix="mcsm_extract_")
        local_archive = os.path.join(tmp_dir, name)

        def do_extract():
            try:
                def progress(current, total):
                    pct = int(current / total * 100) if total > 0 else 0
                    self.app.root.after(0, lambda: self._progress_bar.configure(value=pct))

                ok = self.app.api.download_file(
                    self.app._daemon_id, self.app._instance_uuid,
                    remote_path, local_archive,
                    progress_callback=progress
                )
                if not ok:
                    self.app.root.after(0, lambda: self._on_extract_result(False, "下载失败", tmp_dir))
                    return

                self.app.root.after(0, lambda: self._progress_label.config(text=f"正在解压: {name}"))

                extract_dir = os.path.join(tmp_dir, "extracted")
                os.makedirs(extract_dir, exist_ok=True)

                cmd = [seven_zip, "x", local_archive, f"-o{extract_dir}", "-y"]
                result = subprocess.run(cmd, capture_output=True, timeout=300)
                if result.returncode != 0:
                    err = result.stderr.decode("utf-8", errors="replace").strip()
                    self.app.root.after(0, lambda: self._on_extract_result(False, f"7z解压失败: {err}", tmp_dir))
                    return

                self.app.root.after(0, lambda: self._progress_label.config(text=f"正在上传解压文件: {name}"))
                self._upload_extracted(extract_dir, self._current_remote_dir, tmp_dir)

            except Exception as e:
                self.app.root.after(0, lambda err=str(e): self._on_extract_result(False, err, tmp_dir))

        threading.Thread(target=do_extract, daemon=True).start()

    def _upload_extracted(self, extract_dir, remote_dir, tmp_dir):
        try:
            file_count = 0
            dir_count = 0
            for root, _dirs, files in os.walk(extract_dir):
                rel_root = os.path.relpath(root, extract_dir)
                if rel_root == ".":
                    rel_root = ""
                remote_rel = rel_root.replace("\\", "/") if rel_root else ""
                remote_subdir = _join_path(remote_dir, remote_rel) if remote_rel else remote_dir

                if remote_rel:
                    try:
                        self.app.api.create_directory(
                            self.app._daemon_id, self.app._instance_uuid, remote_subdir
                        )
                    except Exception:
                        pass
                    dir_count += 1

                for f in files:
                    local_path = os.path.join(root, f)
                    def pcb(cur, tot, fname=f):
                        pct = int(cur / tot * 100) if tot > 0 else 0
                        self.app.root.after(0, lambda v=pct, fn=fname: (
                            self._progress_label.config(text=f"正在上传: {fn} ({v}%)"),
                            self._progress_bar.configure(value=v)
                        ))
                    ok = self.app.api.upload_file(
                        local_path, remote_subdir,
                        self.app._daemon_id, self.app._instance_uuid,
                        progress_callback=pcb
                    )
                    if ok:
                        file_count += 1
                    else:
                        self.app.root.after(0, lambda fname=f: self._on_extract_result(False, f"上传失败: {fname}", tmp_dir))
                        return

            self.app.root.after(0, lambda: self._on_extract_result(
                True, f"解压完成：{file_count} 个文件, {dir_count} 个目录", tmp_dir
            ))
        except Exception as e:
            self.app.root.after(0, lambda err=str(e): self._on_extract_result(False, err, tmp_dir))

    def _on_extract_result(self, ok: bool, msg: str, tmp_dir: str | None):
        if tmp_dir is not None:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        self._hide_progress()
        if ok:
            self.app._set_status(msg)
            self._refresh_remote()
        else:
            self.app._set_status(f"解压失败: {msg}")
            messagebox.showerror("解压失败", msg)

    def _on_remote_unzip_result(self, ok: bool, name: str):
        self._hide_progress()
        if ok:
            self.app._set_status(f"解压完成: {name}")
            self._refresh_remote()
        else:
            err = self.app.api.last_error or "服务器解压失败"
            self.app._set_status(f"解压失败: {err}")
            messagebox.showerror("解压失败", err)

    def _compress_remote_files(self):
        sel = self._remote_tree.selection()
        if not sel:
            messagebox.showwarning("选择文件", "请先选择要压缩的文件")
            return
        names = []
        is_dir_map = {}
        for item_id in sel:
            item = self._remote_tree.item(item_id)
            text = item["text"]
            if text == ICON_PARENT:
                continue
            name = _strip_icon(text)
            names.append(name)
            is_dir_map[name] = text.startswith(f"{ICON_DIR} ")

        if not names:
            return

        fmt = self._compress_format_dialog()
        if not fmt:
            return

        if fmt == ".zip":
            self._compress_remote_zip(names)
        else:
            self._compress_remote_local(names, fmt, is_dir_map)

    def _compress_format_dialog(self) -> str | None:
        dialog = tk.Toplevel(self.app.root)
        dialog.title("选择压缩格式")
        dialog.transient(self.app.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        dialog.config(bg=Nord.bg)
        w, h = 300, 150
        sw = dialog.winfo_screenwidth()
        sh = dialog.winfo_screenheight()
        dialog.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="选择压缩格式:").pack(pady=(0, 10))
        result = [None]
        formats = [".zip", ".tar.gz", ".tar", ".7z"]
        var = tk.StringVar(value=".zip")
        cb = ttk.Combobox(frame, textvariable=var, values=formats, state="readonly", width=15)
        cb.pack(pady=(0, 15))
        btn_frame = ttk.Frame(frame)
        btn_frame.pack()

        def on_ok():
            result[0] = var.get()
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        ttk.Button(btn_frame, text="确定", command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=on_cancel).pack(side=tk.LEFT, padx=5)
        dialog.protocol("WM_DELETE_WINDOW", on_cancel)
        dialog.wait_window()
        return result[0]

    def _compress_remote_zip(self, names: list[str]):
        name = simpledialog.askstring("压缩文件名", "输入压缩文件名:", initialvalue="archive.zip")
        if not name:
            return
        if not name.endswith(".zip"):
            name += ".zip"
        archive_path = _join_path(self._current_remote_dir, name)
        targets = [_join_path(self._current_remote_dir, n) for n in names]
        self._show_progress()
        self._progress_label.config(text=f"正在压缩: {name}")
        self._progress_bar["value"] = 0

        def do_zip():
            try:
                ok = self.app.api.compress_files(
                    self.app._daemon_id, self.app._instance_uuid,
                    archive_path, targets
                )
                self.app.root.after(0, lambda: self._on_compress_result(ok, name, True))
            except Exception as e:
                self.app.root.after(0, lambda err=str(e): self._on_compress_result(False, err, True))

        threading.Thread(target=do_zip, daemon=True).start()

    def _compress_remote_local(self, names: list[str], fmt: str, is_dir_map: dict[str, bool]):
        ext_map = {".tar.gz": "tar.gz", ".tar": "tar", ".7z": "7z"}
        default_ext = ext_map.get(fmt, fmt.lstrip("."))
        default_name = f"archive.{default_ext}"
        name = simpledialog.askstring("压缩文件名", "输入压缩文件名:", initialvalue=default_name)
        if not name:
            return

        seven_zip = seven_zip_path()
        if fmt not in (".tar.gz", ".tar") and not seven_zip:
            messagebox.showerror("压缩失败", "7-Zip 未安装，无法压缩为 .7z 格式")
            return

        compressed_dir = os.path.join(os.getcwd(), "Compressed")
        os.makedirs(compressed_dir, exist_ok=True)
        local_path = os.path.join(compressed_dir, name)
        self._show_progress()
        self._progress_label.config(text=f"正在下载: {name}")
        self._progress_bar["value"] = 0
        tmp_dir = tempfile.mkdtemp(prefix="mcsm_compress_")
        download_dir = os.path.join(tmp_dir, "files")
        os.makedirs(download_dir, exist_ok=True)

        def do_compress():
            try:
                total = len(names)
                for i, n in enumerate(names):
                    remote_full = _join_path(self._current_remote_dir, n)
                    local_target = os.path.join(download_dir, n)
                    if is_dir_map.get(n):
                        os.makedirs(local_target, exist_ok=True)
                        ok = self._download_remote_dir(remote_full, local_target)
                    else:
                        parent = os.path.dirname(local_target)
                        if parent:
                            os.makedirs(parent, exist_ok=True)
                        def dl_progress(cur, tot, fname=n):
                            p = int(cur / tot * 100) if tot > 0 else 0
                            self.app.root.after(0, lambda v=p: self._progress_bar.configure(value=int(v / total * 50)))
                        ok = self.app.api.download_file(
                            self.app._daemon_id, self.app._instance_uuid,
                            remote_full, local_target,
                            progress_callback=dl_progress
                        )
                    if not ok:
                        err_name = n
                        self.app.root.after(0, lambda fname=err_name: self._on_compress_result(False, f"下载失败: {fname}", False))
                        return
                    pct = int((i + 1) / total * 50)
                    self.app.root.after(0, lambda v=pct: self._progress_bar.configure(value=v))

                self.app.root.after(0, lambda: self._progress_label.config(text=f"正在压缩: {name}"))

                if fmt == ".tar.gz" or fmt == ".tar":
                    mode = "w:gz" if fmt == ".tar.gz" else "w"
                    with tarfile.open(local_path, mode) as tar:
                        for item_name in os.listdir(download_dir):
                            item_path = os.path.join(download_dir, item_name)
                            tar.add(item_path, arcname=item_name)
                else:
                    fmt_7z = fmt.lstrip(".")
                    cmd = [seven_zip, "a", f"-t{fmt_7z}", local_path, download_dir + os.sep + "*"]
                    result = subprocess.run(cmd, capture_output=True, timeout=600)
                    if result.returncode != 0:
                        err = result.stderr.decode("utf-8", errors="replace").strip()
                        self.app.root.after(0, lambda err_msg=err: self._on_compress_result(False, f"压缩失败: {err_msg}", False))
                        return

                self.app.root.after(0, lambda: self._on_compress_result(True, name, False))
            except Exception as e:
                self.app.root.after(0, lambda err=str(e): self._on_compress_result(False, err, False))
            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)

        threading.Thread(target=do_compress, daemon=True).start()

    def _download_remote_dir(self, remote_dir: str, local_dir: str) -> bool:
        try:
            items = self.app.api.list_files(self.app._daemon_id, self.app._instance_uuid, remote_dir)
            if items is None:
                return False
            for item in items:
                name = _get_name(item)
                if name in (".", ".."):
                    continue
                remote_path = _join_path(remote_dir, name)
                local_path = os.path.join(local_dir, name)
                if _is_dir(item):
                    os.makedirs(local_path, exist_ok=True)
                    if not self._download_remote_dir(remote_path, local_path):
                        return False
                else:
                    ok = self.app.api.download_file(
                        self.app._daemon_id, self.app._instance_uuid,
                        remote_path, local_path
                    )
                    if not ok:
                        return False
            return True
        except Exception:
            return False

    def _on_compress_result(self, ok: bool, msg: str, is_remote: bool):
        self._hide_progress()
        if ok:
            self.app._set_status(f"压缩完成: {msg}")
            if is_remote:
                self._refresh_remote()
        else:
            self.app._set_status(f"压缩失败: {msg}")
            messagebox.showerror("压缩失败", msg)

    def _refresh_remote(self):
        self._remote_tree.delete(*self._remote_tree.get_children())
        if not self.app._daemon_id or not self.app._instance_uuid:
            self._remote_tree.insert("", tk.END, text="请先在设置中配置实例")
            return
        if not self.app.api.is_authenticated:
            self.app.api.refresh_auth_from_config(self.app.cfg)
            if not self.app.api.is_authenticated:
                self._remote_tree.insert("", tk.END, text="请先在设置中登录")
                return

        self.app._set_status("正在加载文件列表...")
        path = self._current_remote_dir
        def do_list():
            try:
                items = self.app.api.list_files(self.app._daemon_id, self.app._instance_uuid, path)
                self.app.root.after(0, lambda: self._on_remote_listed(items))
            except Exception as e:
                self.app.root.after(0, lambda err=str(e): self._remote_tree.insert("", tk.END, text=f"错误: {err}"))
        threading.Thread(target=do_list, daemon=True).start()

    def _on_remote_listed(self, items):
        self._remote_tree.delete(*self._remote_tree.get_children())
        if items is None:
            err = self.app.api.last_error or "未知错误"
            display = err[:120] + "..." if len(err) > 120 else err
            self._remote_tree.insert("", tk.END, text=display)
            self.app._set_status(f"文件列表加载失败: {err}")
            return
        if not items:
            self._remote_tree.insert("", tk.END, text="(空目录)")
            self.app._set_status(f"文件列表为空: {self._current_remote_dir}")
            return
        self._remote_items = items
        self.app._set_status(f"已加载 {len(items)} 个文件")

        if self._current_remote_dir != "/":
            self._remote_tree.insert("", tk.END, text=ICON_PARENT, values=("", ""))
        dirs = []
        files = []
        for item in items:
            name = _get_name(item)
            if name in (".", ".."):
                continue
            if _is_dir(item):
                dirs.append(item)
            else:
                files.append(item)
        dirs.sort(key=_get_name)
        files.sort(key=_get_name)
        for d in dirs:
            name = _get_name(d)
            self._remote_tree.insert("", tk.END, text=_display_name(name, is_dir=True), values=("", ""))
        for f in files:
            name = _get_name(f)
            size = self._format_size(f.get("size", 0) or 0)
            mtime = self._format_timestamp(f.get("mtime", 0) or 0)
            self._remote_tree.insert("", tk.END, text=_display_name(name), values=(size, mtime))

    def _navigate_to(self, path: str):
        self._current_remote_dir = path
        self._remote_path_var.set(path)
        self._refresh_remote()

    def _download_world(self):
        self.app._download_world()

    def _go_up(self):
        self._navigate_to(_parent_path(self._current_remote_dir))

    def _on_local_double_click(self, event):
        sel = self._local_tree.selection()
        if not sel:
            return
        item = self._local_tree.item(sel[0])
        text = item["text"]
        if text == ICON_PARENT:
            self._local_dir = os.path.dirname(self._local_dir.rstrip('/')) or "/"
            self._refresh_local()
            return
        name = _strip_icon(text)
        full = os.path.join(self._local_dir, name)
        if os.path.isdir(full):
            self._local_dir = full
            self._refresh_local()
        else:
            ext = os.path.splitext(name)[1].lower()
            if ext in EDITABLE_EXTS or any(name.lower().endswith(e) for e in EDITABLE_EXTS):
                self._edit_local_file(full, name)
            else:
                self._upload_file()

    def _on_remote_double_click(self, event):
        sel = self._remote_tree.selection()
        if not sel:
            return
        item = self._remote_tree.item(sel[0])
        text = item["text"]
        if text == ICON_PARENT:
            self._go_up()
            return
        name = _strip_icon(text)
        if text.startswith(f"{ICON_DIR} "):
            self._navigate_to(_join_path(self._current_remote_dir, name))
        else:
            ext = os.path.splitext(name)[1].lower()
            if ext in EDITABLE_EXTS or any(name.lower().endswith(e) for e in EDITABLE_EXTS):
                self._edit_file()
            else:
                self._download_file()

    def _make_context_menu(self, tree, items):
        menu = tk.Menu(tree, tearoff=0, bg=Nord.bg_alt, fg=Nord.fg,
                       activebackground=Nord.bg_sel, activeforeground=Nord.fg)
        for label, cmd in items:
            menu.add_command(label=label, command=cmd)
        return menu

    def _show_context_menu(self, event, menu):
        self._close_context_menu()
        self._context_menu_open = menu
        menu.tk_popup(event.x_root, event.y_root)
        menu.grab_release()

    def _close_context_menu(self, event=None):
        if self._context_menu_open:
            try:
                self._context_menu_open.grab_release()
            except Exception:
                pass
            try:
                self._context_menu_open.unpost()
            except Exception:
                pass
            self._context_menu_open = None

    def _on_local_right_click(self, event):
        tree = self._local_tree
        sel = tree.identify_row(event.y)
        if sel:
            tree.selection_set(sel)
            item = tree.item(sel)
            text = item["text"]
            is_dir = text.startswith(f"{ICON_DIR} ") or text == ICON_PARENT
            items = []
            if not is_dir and text != ICON_PARENT:
                items.append(("编辑", self._edit_local_file_selected))
            if is_dir and text != ICON_PARENT:
                items.append(("进入", lambda: self._local_double_click_on(sel)))
            items.append(("上传", self._upload_file_selected))
            items.append(("刷新", self._refresh_local))
            menu = self._make_context_menu(tree, items)
            self._show_context_menu(event, menu)

    def _local_double_click_on(self, item_id):
        self._local_tree.selection_set(item_id)
        self._on_local_double_click(None)

    def _upload_file_selected(self):
        self._upload_file()

    def _on_remote_right_click(self, event):
        tree = self._remote_tree
        sel = tree.identify_row(event.y)
        if not sel:
            return
        if sel not in tree.selection():
            tree.selection_set(sel)
        item = tree.item(sel)
        text = item["text"]
        is_dir = text.startswith(f"{ICON_DIR} ")
        is_parent = text == ICON_PARENT
        multi = len(tree.selection()) > 1
        items = []
        if is_parent:
            items.append(("返回上级", self._go_up))
        elif multi:
            items.append(("压缩", self._compress_remote_files))
            items.append(("删除", self._delete_item))
        elif is_dir:
            items.append(("进入", lambda: self._remote_double_click_on(sel)))
            items.append(("剪切", self._cut_remote_file))
            items.append(("删除", self._delete_item))
        else:
            ext = os.path.splitext(_strip_icon(text))[1].lower()
            name = _strip_icon(text).lower()
            if name.endswith(".tar.gz"):
                ext = ".tar.gz"
            elif name.endswith(".tgz"):
                ext = ".tgz"
            if ext in EDITABLE_EXTS:
                items.append(("编辑", self._edit_file))
            items.append(("下载", self._download_file))
            items.append(("剪切", self._cut_remote_file))
            items.append(("删除", self._delete_item))
            if ext in ARCHIVE_EXTS:
                items.append(("解压", self._extract_archive))
        if not multi:
            items.append(("压缩", self._compress_remote_files))
        if self._clipboard:
            items.append(("粘贴", self._paste_remote_file))
        items.append(("刷新", self._refresh_remote))
        menu = self._make_context_menu(tree, items)
        self._show_context_menu(event, menu)

    def _remote_double_click_on(self, item_id):
        self._remote_tree.selection_set(item_id)
        self._on_remote_double_click(None)

    def _upload_file(self):
        sel = self._local_tree.selection()
        if not sel:
            messagebox.showwarning("选择文件", "请先在本地文件列表中选择文件")
            return
        item = self._local_tree.item(sel[0])
        name = _strip_icon(item["text"])
        local_path = os.path.join(self._local_dir, name)
        if os.path.isdir(local_path):
            messagebox.showwarning("不支持", "不支持上传目录，请选择文件")
            return
        remote_dir = self._current_remote_dir

        self._show_progress()
        self._progress_label.config(text=f"正在上传: {name}")
        self._progress_bar["value"] = 0

        def do_upload():
            def progress(current, total):
                pct = int(current / total * 100) if total > 0 else 0
                self.app.root.after(0, lambda: self._progress_bar.configure(value=pct))

            ok = self.app.api.upload_file(
                local_path, remote_dir,
                self.app._daemon_id, self.app._instance_uuid,
                progress_callback=progress
            )
            self.app.root.after(0, lambda: self._on_upload_result(ok, name))

        threading.Thread(target=do_upload, daemon=True).start()

    def _on_upload_result(self, ok: bool, name: str):
        self._hide_progress()
        if ok:
            self.app._set_status(f"上传成功: {name}")
            self._refresh_remote()
        else:
            self.app._set_status(f"上传失败: {name}")
            messagebox.showerror("上传失败", f"文件 {name} 上传失败")

    def _download_file(self):
        sel = self._remote_tree.selection()
        if not sel:
            messagebox.showwarning("选择文件", "请先在远程文件列表中选择文件")
            return
        item = self._remote_tree.item(sel[0])
        text = item["text"]
        if text == ICON_PARENT:
            return
        name = _strip_icon(text)
        if text.startswith(f"{ICON_DIR} "):
            messagebox.showwarning("不支持", "暂不支持下载目录")
            return

        remote_path = _join_path(self._current_remote_dir, name)
        save_path = filedialog.asksaveasfilename(
            initialdir=self._local_dir,
            initialfile=name,
            title="保存到本地"
        )
        if not save_path:
            return

        self._show_progress()
        self._progress_label.config(text=f"正在下载: {name}")
        self._progress_bar["value"] = 0

        def do_download():
            def progress(current, total):
                pct = int(current / total * 100) if total > 0 else 0
                self.app.root.after(0, lambda: self._progress_bar.configure(value=pct))

            ok = self.app.api.download_file(
                self.app._daemon_id, self.app._instance_uuid,
                remote_path, save_path,
                progress_callback=progress
            )
            self.app.root.after(0, lambda: self._on_download_result(ok, name))

        threading.Thread(target=do_download, daemon=True).start()

    def _edit_file(self):
        sel = self._remote_tree.selection()
        if not sel:
            messagebox.showwarning("选择文件", "请先在远程文件列表中选择文件")
            return
        item = self._remote_tree.item(sel[0])
        text = item["text"]
        if text == ICON_PARENT or text.startswith(f"{ICON_DIR} "):
            return
        name = _strip_icon(text)
        remote_path = _join_path(self._current_remote_dir, name)

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(name)[1] or ".tmp")
        tmp.close()
        self._editing = {"remote_path": remote_path, "name": name, "tmp": tmp.name}

        self.app._set_status(f"正在加载: {name}")

        def do_load():
            ok = self.app.api.download_file(
                self.app._daemon_id, self.app._instance_uuid,
                remote_path, tmp.name,
            )
            self.app.root.after(0, lambda: self._on_remote_file_loaded(ok, name, tmp.name))

        threading.Thread(target=do_load, daemon=True).start()

    def _on_remote_file_loaded(self, ok: bool, name: str, tmp_path: str):
        if not ok:
            os.unlink(tmp_path)
            messagebox.showerror("加载失败", f"无法加载文件: {name}")
            return
        try:
            with open(tmp_path, encoding='utf-8', errors='replace') as f:
                content = f.read()
        except Exception:
            content = "读取文件失败"

        self._open_editor_window(
            title=f"编辑远程: {name}",
            content=content,
            on_save=lambda text: self._save_remote_file(text, name, tmp_path),
        )

    def _save_remote_file(self, content: str, name: str, tmp_path: str):
        try:
            with open(tmp_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            messagebox.showerror("写入失败", f"无法写入临时文件: {e}")
            return False

        self.app._set_status(f"正在保存: {name}")

        def do_upload():
            remote_dir = os.path.dirname(self._editing["remote_path"])
            ok = self.app.api.upload_file(
                tmp_path, remote_dir,
                self.app._daemon_id, self.app._instance_uuid,
            )
            self.app.root.after(0, lambda: self._on_remote_saved(ok, name, tmp_path))

        threading.Thread(target=do_upload, daemon=True).start()
        return True

    def _on_remote_saved(self, ok: bool, name: str, tmp_path: str):
        os.unlink(tmp_path)
        if ok:
            self.app._set_status(f"保存成功: {name}")
            self._refresh_remote()
        else:
            self.app._set_status(f"保存失败: {name}")
            messagebox.showerror("保存失败", f"文件 {name} 上传到服务器失败")

    def _edit_local_file_selected(self):
        sel = self._local_tree.selection()
        if not sel:
            messagebox.showwarning("选择文件", "请先在本地文件列表中选择文件")
            return
        item = self._local_tree.item(sel[0])
        text = item["text"]
        if text == ICON_PARENT or text.startswith(f"{ICON_DIR} "):
            return
        name = _strip_icon(text)
        full = os.path.join(self._local_dir, name)
        self._edit_local_file(full, name)

    def _edit_local_file(self, full_path: str, name: str):
        self.app._set_status(f"正在编辑本地: {name}")
        try:
            with open(full_path, encoding='utf-8', errors='replace') as f:
                content = f.read()
        except Exception as e:
            messagebox.showerror("读取失败", f"无法读取文件: {e}")
            return

        def on_save(text: str):
            try:
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                self.app._set_status(f"本地文件已保存: {name}")
                return True
            except Exception as e:
                messagebox.showerror("保存失败", f"无法写入文件: {e}")
                return False

        self._open_editor_window(
            title=f"编辑本地: {name}",
            content=content,
            on_save=on_save,
        )

    def _open_editor_window(self, title: str, content: str, on_save):
        win = tk.Toplevel(self.frame)
        win.title(title)
        win.geometry("800x600")
        win.minsize(500, 300)
        win.transient(self.frame)
        win.grab_set()
        win.config(bg=Nord.bg)

        top = ttk.Frame(win)
        top.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(top, text="保存",
                   command=lambda: self._editor_save(win, txt, on_save)).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="取消", command=win.destroy).pack(side=tk.LEFT, padx=2)

        text_frame = ttk.Frame(win)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))

        txt = tk.Text(text_frame, wrap=tk.WORD, font=(MONO_FONT, 10),
                      bg=Nord.bg, fg=Nord.fg, insertbackground=Nord.fg,
                      undo=True)
        txt.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        scroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=txt.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        txt.configure(yscrollcommand=scroll.set)

        txt.insert('1.0', content)
        txt.edit_reset()
        txt.focus_set()

    @staticmethod
    def _editor_save(win, txt, on_save):
        content = txt.get('1.0', tk.END)
        if content.endswith('\n'):
            content = content[:-1]
        ok = on_save(content)
        if ok:
            win.destroy()

    def _on_download_result(self, ok: bool, name: str):
        self._hide_progress()
        if ok:
            self.app._set_status(f"下载成功: {name}")
            self._refresh_local()
        else:
            self.app._set_status(f"下载失败: {name}")
            messagebox.showerror("下载失败", f"文件 {name} 下载失败")

    def _mkdir(self):
        name = simpledialog.askstring("新建目录", "目录名称:", parent=self.frame)
        if not name:
            return
        path = _join_path(self._current_remote_dir, name)

        def do_mkdir():
            ok = self.app.api.create_directory(self.app._daemon_id, self.app._instance_uuid, path)
            self.app.root.after(0, lambda: self._on_mkdir_result(ok))

        threading.Thread(target=do_mkdir, daemon=True).start()

    def _on_mkdir_result(self, ok: bool):
        if ok:
            self.app._set_status("目录创建成功")
            self._refresh_remote()
        else:
            messagebox.showerror("创建失败", "目录创建失败")

    def _delete_item(self):
        sel = self._remote_tree.selection()
        if not sel:
            messagebox.showwarning("选择文件", "请先在远程文件列表中选择文件")
            return
        item = self._remote_tree.item(sel[0])
        text = item["text"]
        if text == ICON_PARENT:
            return
        is_dir = text.startswith(f"{ICON_DIR} ")
        name = _strip_icon(text)

        if not messagebox.askyesno("确认删除", f"确定要删除 {'目录' if is_dir else '文件'} '{name}' 吗？"):
            return

        remote_path = _join_path(self._current_remote_dir, name)

        def do_delete():
            ok = self.app.api.delete_files(self.app._daemon_id, self.app._instance_uuid, [remote_path])
            self.app.root.after(0, lambda: self._on_delete_result(ok, name))

        threading.Thread(target=do_delete, daemon=True).start()

    def _on_delete_result(self, ok: bool, name: str):
        if ok:
            self.app._set_status(f"已删除: {name}")
            self._refresh_remote()
        else:
            messagebox.showerror("删除失败", f"删除 '{name}' 失败")

    @staticmethod
    def _format_size(size: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    @staticmethod
    def _format_time(timestamp: float) -> str:
        from datetime import datetime
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")

    @staticmethod
    def _format_timestamp(ts) -> str:
        if not ts or ts == 0:
            return "-"
        from datetime import datetime
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(ts / 1000 if ts > 1e10 else ts).strftime("%Y-%m-%d %H:%M")
        return str(ts)[:19].replace("GMT", "").strip() if isinstance(ts, str) else "-"
