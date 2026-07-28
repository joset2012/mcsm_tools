import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from .font_helper import MONO_FONT
from .theme import Nord


PLUGIN_FOLDERS = ["plugins", "mods"]


class Plugin:
    def __init__(self, name: str, path: str, is_dir: bool = False):
        self.name = name
        self.path = path
        self.is_dir = is_dir
        self.is_disabled = name.endswith(".disabled") or name.lower().endswith(".jar.disabled")
        self.is_jar = name.lower().endswith(".jar") or name.lower().endswith(".litemod") or name.lower().endswith(".zip")

    @property
    def display_name(self) -> str:
        if self.is_disabled:
            return f"{self.name} ⛔"
        return self.name

    @property
    def is_active(self) -> bool:
        return not self.is_disabled and (self.is_jar or self.is_dir)

    @property
    def file_name(self) -> str:
        if self.is_disabled:
            base, ext = os.path.splitext(self.name)
            if base.endswith(".disabled"):
                base = base[: -len(".disabled")]
                return base
            return self.name
        return self.name


class PluginManagerTab:
    def __init__(self, notebook, app):
        self.app = app
        self.frame = ttk.Frame(notebook)
        self._current_folder = "plugins"
        self._plugins: list[Plugin] = []
        self._detected = False
        self._build_ui()
        self._auto_detect_folder()

    def _build_ui(self):
        toolbar = ttk.Frame(self.frame)
        toolbar.pack(fill=tk.X, padx=8, pady=6)

        ttk.Label(toolbar, text="目录:").pack(side=tk.LEFT)
        self._folder_var = tk.StringVar(value="plugins")
        cb = ttk.Combobox(toolbar, textvariable=self._folder_var,
                          values=PLUGIN_FOLDERS,
                          state="readonly", width=14)
        cb.pack(side=tk.LEFT, padx=4)
        cb.bind("<<ComboboxSelected>>", lambda e: self._switch_folder())

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        ttk.Button(toolbar, text="上传插件", command=self._upload_plugin).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="启用", command=self._enable_plugin).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="禁用", command=self._disable_plugin).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="删除", command=self._delete_plugin).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="创建目录", command=self._create_folder).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="刷新", command=self._refresh_list).pack(side=tk.LEFT, padx=2)

        self._status_label = ttk.Label(toolbar, text="")
        self._status_label.pack(side=tk.RIGHT, padx=6)

        columns = ("name", "status", "path")
        self._tree = ttk.Treeview(self.frame, columns=columns, show="headings")
        self._tree.heading("name", text="名称")
        self._tree.heading("status", text="状态")
        self._tree.heading("path", text="路径")
        self._tree.column("name", width=250)
        self._tree.column("status", width=80, anchor=tk.CENTER)
        self._tree.column("path", width=300)
        self._tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 6))

        scroll = ttk.Scrollbar(self.frame, orient=tk.VERTICAL, command=self._tree.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._tree.configure(yscrollcommand=scroll.set)

        self._tree.bind("<Double-1>", lambda e: self._toggle_plugin())

    def _set_status(self, text: str):
        self._status_label.config(text=text)

    def _auto_detect_folder(self):
        if not self.app.api.is_authenticated or not self.app._daemon_id:
            self._detected = True
            self._refresh_list()
            return

        def do_detect():
            detected = None
            for folder in ["plugins", "mods"]:
                try:
                    items = self.app.api.list_files(
                        self.app._daemon_id, self.app._instance_uuid, f"/{folder}"
                    )
                    if items is not None:
                        detected = folder
                        break
                except Exception:
                    pass
            self.app.root.after(0, lambda f=detected: self._on_detected(f))

        threading.Thread(target=do_detect, daemon=True).start()

    def _on_detected(self, folder: str | None):
        self._detected = True
        if folder:
            self._current_folder = folder
            self._folder_var.set(folder)
            self._set_status(f"检测到服务器目录: /{folder}")
        self._refresh_list()

    def _switch_folder(self):
        self._current_folder = self._folder_var.get()
        self._refresh_list()

    def _refresh_list(self):
        if not self.app.api.is_authenticated:
            self._tree.delete(*self._tree.get_children())
            self._tree.insert("", tk.END, values=("请先登录", "", ""))
            return

        self._status_label.config(text="正在加载...")

        def do_list():
            try:
                folder = f"/{self._current_folder}"
                items = self.app.api.list_files(
                    self.app._daemon_id, self.app._instance_uuid, folder
                )
                self.app.root.after(0, lambda: self._on_listed(items))
            except Exception as e:
                self.app.root.after(0, lambda: self._on_list_error(str(e)))

        threading.Thread(target=do_list, daemon=True).start()

    def _on_listed(self, items):
        self._tree.delete(*self._tree.get_children())
        if items is None:
            self._tree.insert("", tk.END,
                              values=(f"无法读取 /{self._current_folder}", "",
                                      "目录可能不存在，点击「创建目录」新建"))
            self._status_label.config(text="目录不存在")
            return

        self._plugins = []
        for item in items:
            name = item.get("name", "")
            if name in (".", ".."):
                continue
            is_dir = item.get("isFile", True) is False or item.get("type", "") == "directory"
            if is_dir:
                continue
            plugin = Plugin(name, f"/{self._current_folder}/{name}")
            self._plugins.append(plugin)

        self._plugins.sort(key=lambda p: (p.is_disabled, p.name.lower()))

        for plugin in self._plugins:
            status = "⛔ 已禁用" if plugin.is_disabled else "✅ 启用"
            tag = "disabled" if plugin.is_disabled else "enabled"
            self._tree.insert("", tk.END,
                              values=(plugin.display_name, status, plugin.path),
                              tags=(tag,))

        self._tree.tag_configure("disabled", foreground=Nord.polar_night_4)
        self._tree.tag_configure("enabled", foreground=Nord.aurora_green)

        total = len(self._plugins)
        active = sum(1 for p in self._plugins if p.is_active)
        self._status_label.config(text=f"{total} 个文件, {active} 个已启用")

    def _on_list_error(self, err: str):
        self._tree.delete(*self._tree.get_children())
        self._tree.insert("", tk.END, values=("加载失败", "", err))
        self._status_label.config(text="加载失败")

    def _get_selected_plugin(self) -> Plugin | None:
        sel = self._tree.selection()
        if not sel:
            return None
        item = self._tree.item(sel[0])
        path = item["values"][2]
        for p in self._plugins:
            if p.path == path:
                return p
        return None

    def _toggle_plugin(self):
        plugin = self._get_selected_plugin()
        if not plugin:
            return
        if plugin.is_disabled:
            self._enable_plugin()
        else:
            self._disable_plugin()

    def _enable_plugin(self):
        plugin = self._get_selected_plugin()
        if not plugin:
            messagebox.showwarning("选择插件", "请先选择一个插件")
            return
        if not plugin.is_disabled:
            messagebox.showinfo("提示", "该插件已启用")
            return

        self._status_label.config(text="正在启用...")
        old_name = plugin.name
        new_name = old_name
        if old_name.endswith(".disabled"):
            new_name = old_name[: -len(".disabled")]
        elif old_name.lower().endswith(".jar.disabled"):
            new_name = old_name[: -len(".disabled")]

        src = plugin.path
        dst = f"/{self._current_folder}/{new_name}"

        def do_rename():
            ok = self.app.api.move_files(
                self.app._daemon_id, self.app._instance_uuid,
                [[src, dst]]
            )
            self.app.root.after(0, lambda: self._on_toggle_result(ok, new_name, "启用"))

        threading.Thread(target=do_rename, daemon=True).start()

    def _disable_plugin(self):
        plugin = self._get_selected_plugin()
        if not plugin:
            messagebox.showwarning("选择插件", "请先选择一个插件")
            return
        if plugin.is_disabled:
            messagebox.showinfo("提示", "该插件已禁用")
            return
        if plugin.is_dir:
            messagebox.showwarning("不支持", "不支持禁用目录")
            return

        self._status_label.config(text="正在禁用...")
        src = plugin.path
        new_name = plugin.name + ".disabled"
        dst = f"/{self._current_folder}/{new_name}"

        def do_rename():
            ok = self.app.api.move_files(
                self.app._daemon_id, self.app._instance_uuid,
                [[src, dst]]
            )
            self.app.root.after(0, lambda: self._on_toggle_result(ok, plugin.name, "禁用"))

        threading.Thread(target=do_rename, daemon=True).start()

    def _on_toggle_result(self, ok: bool, name: str, action: str):
        if ok:
            self._status_label.config(text=f"{action}成功: {name}")
            self._refresh_list()
        else:
            self._status_label.config(text=f"{action}失败")
            messagebox.showerror("操作失败", f"{action} '{name}' 失败")

    def _upload_plugin(self):
        file_path = filedialog.askopenfilename(
            title="选择插件文件",
            filetypes=[("插件文件", "*.jar *.litemod *.zip *.py *.js"),
                       ("所有文件", "*.*")]
        )
        if not file_path:
            return

        name = os.path.basename(file_path)
        remote_dir = f"/{self._current_folder}"
        self._status_label.config(text=f"正在上传: {name}")

        def do_upload():
            ok = self.app.api.upload_file(
                file_path, remote_dir,
                self.app._daemon_id, self.app._instance_uuid,
            )
            self.app.root.after(0, lambda: self._on_upload_result(ok, name))

        threading.Thread(target=do_upload, daemon=True).start()

    def _on_upload_result(self, ok: bool, name: str):
        if ok:
            self._status_label.config(text=f"上传成功: {name}")
            self._refresh_list()
        else:
            self._status_label.config(text=f"上传失败: {name}")
            messagebox.showerror("上传失败", f"文件 '{name}' 上传失败")

    def _delete_plugin(self):
        plugin = self._get_selected_plugin()
        if not plugin:
            messagebox.showwarning("选择插件", "请先选择一个插件")
            return
        if not messagebox.askyesno("确认删除",
                                    f"确定要删除 '{plugin.name}' 吗？\n此操作不可恢复。"):
            return

        self._status_label.config(text="正在删除...")

        def do_delete():
            ok = self.app.api.delete_files(
                self.app._daemon_id, self.app._instance_uuid,
                [plugin.path]
            )
            self.app.root.after(0, lambda: self._on_delete_result(ok, plugin.name))

        threading.Thread(target=do_delete, daemon=True).start()

    def _on_delete_result(self, ok: bool, name: str):
        if ok:
            self._status_label.config(text=f"已删除: {name}")
            self._refresh_list()
        else:
            self._status_label.config(text=f"删除失败: {name}")
            messagebox.showerror("删除失败", f"删除 '{name}' 失败")

    def _create_folder(self):
        folder = f"/{self._current_folder}"
        self._status_label.config(text=f"正在创建目录 {folder}...")
        def do_create():
            ok = self.app.api.create_directory(
                self.app._daemon_id, self.app._instance_uuid, folder
            )
            self.app.root.after(0, lambda: self._on_create_result(ok))
        threading.Thread(target=do_create, daemon=True).start()

    def _on_create_result(self, ok: bool):
        if ok:
            self._status_label.config(text="目录创建成功")
            self._refresh_list()
        else:
            self._status_label.config(text="目录创建失败")
            messagebox.showerror("创建失败", "无法创建目录，请检查权限")
