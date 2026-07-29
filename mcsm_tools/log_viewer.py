import gzip
import os
import tempfile
import threading
import tkinter as tk
from tkinter import ttk

from .theme import Nord
from .font_helper import MONO_FONT


class LogViewerTab:
    def __init__(self, notebook, app):
        self.app = app
        self.frame = ttk.Frame(notebook)
        self._auto_scroll = tk.BooleanVar(value=True)
        self._wrap_text = tk.BooleanVar(value=False)
        self._current_log = ""
        self._build_ui()
        self._refresh_file_list()

    def _build_ui(self):
        toolbar = ttk.Frame(self.frame)
        toolbar.pack(fill=tk.X, pady=2)

        ttk.Label(toolbar, text="日志文件:").pack(side=tk.LEFT)
        self._file_combo = ttk.Combobox(toolbar, width=30, state="readonly")
        self._file_combo.pack(side=tk.LEFT, padx=5)
        self._file_combo.bind("<<ComboboxSelected>>", lambda e: self._load_selected_log())

        ttk.Button(toolbar, text="刷新列表", command=self._refresh_file_list).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="刷新内容", command=self._refresh_content).pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)

        self._auto_scroll_check = ttk.Checkbutton(toolbar, text="自动滚动", variable=self._auto_scroll)
        self._auto_scroll_check.pack(side=tk.LEFT, padx=2)
        self._wrap_check = ttk.Checkbutton(toolbar, text="自动换行", variable=self._wrap_text,
                                           command=self._toggle_wrap)
        self._wrap_check.pack(side=tk.LEFT, padx=2)

        search_frame = ttk.Frame(self.frame)
        search_frame.pack(fill=tk.X, pady=2)

        ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT)
        self._search_var = tk.StringVar()
        self._search_entry = ttk.Entry(search_frame, textvariable=self._search_var, width=30)
        self._search_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self._search_entry.bind("<Return>", lambda e: self._do_search())
        ttk.Button(search_frame, text="查找", command=self._do_search).pack(side=tk.LEFT, padx=2)
        ttk.Button(search_frame, text="清除高亮", command=self._clear_highlight).pack(side=tk.LEFT, padx=2)
        
        # 添加多关键词提示
        hint_label = ttk.Label(search_frame, text="(多关键词用/分隔)", foreground=Nord.frost_4)
        hint_label.pack(side=tk.LEFT, padx=5)

        main_frame = ttk.Frame(self.frame)
        main_frame.pack(fill=tk.BOTH, expand=True, pady=2)

        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self._line_numbers = tk.Text(text_frame, width=6, padx=4, pady=0,
                                      font=(MONO_FONT, 10), bg=Nord.bg_alt, fg=Nord.frost_4,
                                      state=tk.DISABLED, relief=tk.FLAT, takefocus=0,
                                      highlightthickness=0, borderwidth=0)
        self._line_numbers.pack(side=tk.LEFT, fill=tk.Y)

        self._log_text = tk.Text(text_frame, wrap=tk.NONE, font=(MONO_FONT, 10),
                                 bg=Nord.bg, fg=Nord.fg, state=tk.DISABLED)
        self._log_text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        v_scroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self._on_vscroll)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll = ttk.Scrollbar(main_frame, orient=tk.HORIZONTAL, command=self._log_text.xview)
        h_scroll.pack(fill=tk.X)
        self._log_text.configure(yscrollcommand=self._sync_scroll, xscrollcommand=h_scroll.set)
        self._v_scroll = v_scroll

        self._log_text.tag_config("highlight", background=Nord.bg_sel)
        self._log_text.tag_config("info", foreground=Nord.aurora_green)
        self._log_text.tag_config("warn", foreground=Nord.aurora_yellow)
        self._log_text.tag_config("error", foreground=Nord.aurora_red)
        self._log_text.tag_config("fatal", foreground=Nord.aurora_red, font=(MONO_FONT, 10, "bold"))

        self._stats_label = ttk.Label(self.frame, text="行数: 0 | 大小: 0 B")
        self._stats_label.pack(fill=tk.X)

    def _on_vscroll(self, *args):
        if args[0] == "moveto":
            frac = float(args[1])
            self._log_text.yview_moveto(frac)
            self._line_numbers.yview_moveto(frac)
        elif args[0] == "scroll":
            self._log_text.yview_scroll(int(args[1]), args[2])
            self._line_numbers.yview_scroll(int(args[1]), args[2])

    def _sync_scroll(self, *args):
        self._v_scroll.set(*args)
        self._line_numbers.yview_moveto(args[0])

    def _update_line_numbers(self):
        self._line_numbers.config(state=tk.NORMAL)
        self._line_numbers.delete('1.0', tk.END)
        log_text = self._log_text
        total = log_text.get('1.0', tk.END).count('\n')
        wrap = log_text.cget('wrap') != tk.NONE
        if wrap:
            lines = []
            for i in range(1, total + 1):
                start = f'{i}.0'
                end = f'{i}.0 lineend'
                try:
                    vis = log_text.count(start, end, 'displaylines')
                    if vis and vis[0]:
                        vis = vis[0]
                    else:
                        vis = 1
                except Exception:
                    vis = 1
                lines.append(str(i))
                for _ in range(vis - 1):
                    lines.append('')
            self._line_numbers.insert('1.0', '\n'.join(lines))
        else:
            nums = '\n'.join(str(i) for i in range(1, total + 1))
            self._line_numbers.insert('1.0', nums)
        self._line_numbers.config(state=tk.DISABLED)

    def _set_log_text(self, text: str):
        self._current_log = text
        self._log_text.config(state=tk.NORMAL)
        self._log_text.delete('1.0', tk.END)
        self._log_text.insert('1.0', text)
        self._apply_syntax_highlight()
        self._update_line_numbers()
        if self._auto_scroll.get():
            self._log_text.see(tk.END)
        self._log_text.config(state=tk.DISABLED)

        lines = text.count('\n')
        size = len(text.encode('utf-8'))
        self._stats_label.config(text=f"行数: {lines} | 大小: {self._format_size(size)}")

    def _append_log_text(self, text: str):
        self._current_log += text
        self._log_text.config(state=tk.NORMAL)
        self._log_text.insert(tk.END, text)
        self._apply_syntax_highlight()
        if self._auto_scroll.get():
            self._log_text.see(tk.END)
        self._log_text.config(state=tk.DISABLED)

    def _apply_syntax_highlight(self):

        for pattern, tag in [
            (r'\[INFO\]|\[\d+:\d+:\d+\]\s*\[.*?/INFO\].*', 'info'),
            (r'\[WARN\]|\[\d+:\d+:\d+\]\s*\[.*?/WARN\].*', 'warn'),
            (r'\[ERROR\]|\[\d+:\d+:\d+\]\s*\[.*?/ERROR\].*', 'error'),
            (r'\[FATAL\]|\[\d+:\d+:\d+\]\s*\[.*?/FATAL\].*', 'fatal'),
        ]:
            self._log_text.tag_remove(tag, '1.0', tk.END)
            start = '1.0'
            while True:
                pos = self._log_text.search(pattern, start, tk.END, regexp=True)
                if not pos:
                    break
                line_end = f"{pos} lineend"
                self._log_text.tag_add(tag, pos, line_end)
                start = f"{pos} +1c"

    def _toggle_wrap(self):
        self._log_text.config(wrap=tk.WORD if self._wrap_text.get() else tk.NONE)
        self._update_line_numbers()

    def _do_search(self):
        query = self._search_var.get().strip()
        if not query:
            return

        # 支持多关键词过滤，用 / 分隔
        keywords = [k.strip() for k in query.split('/') if k.strip()]
        if not keywords:
            return

        self._log_text.tag_remove("highlight", '1.0', tk.END)
        
        # 获取所有文本内容
        content = self._log_text.get('1.0', tk.END)
        lines = content.split('\n')
        
        count = 0
        for i, line in enumerate(lines, 1):
            # 检查行是否包含所有关键词
            line_lower = line.lower()
            if all(keyword.lower() in line_lower for keyword in keywords):
                # 高亮整行
                start_pos = f"{i}.0"
                end_pos = f"{i}.0 lineend"
                self._log_text.tag_add("highlight", start_pos, end_pos)
                count += 1

        if count == 0:
            keyword_str = " / ".join(keywords)
            self.app._set_status(f"未找到包含所有关键词的行: {keyword_str}")
        else:
            keyword_str = " / ".join(keywords)
            self.app._set_status(f"找到 {count} 行包含所有关键词: {keyword_str}")

    def _clear_highlight(self):
        self._log_text.tag_remove("highlight", '1.0', tk.END)

    LOG_DIRS = ["/logs", "/crash-reports", "/"]

    def _refresh_file_list(self):
        if not self.app._daemon_id or not self.app._instance_uuid:
            self._file_combo["values"] = ["请先配置实例"]
            return
        if not self.app.api.is_authenticated:
            self.app.api.refresh_auth_from_config(self.app.cfg)
            if not self.app.api.is_authenticated:
                self._file_combo["values"] = ["请先登录"]
                return

        def do_list():
            try:
                all_files = {}
                for d in self.LOG_DIRS:
                    items = self.app.api.list_files(self.app._daemon_id, self.app._instance_uuid, d)
                    if items:
                        for item in items:
                            name = item.get("name", "")
                            full = d.rstrip('/') + '/' + name if d != '/' else '/' + name
                            # 使用更健壮的目录判断逻辑
                            if self._is_dir_from_item(item):
                                continue
                            if self._is_log_file(name):
                                all_files[full] = name
                names = list(all_files.values()) if not all_files else list(all_files.keys())
                self.app.root.after(0, lambda: self._on_file_list(names if all_files else None))
            except Exception as e:
                err_msg = str(e)
                self.app.root.after(0, lambda m=err_msg: self._file_combo.configure(values=[f"错误: {m}"]))

        threading.Thread(target=do_list, daemon=True).start()

    @staticmethod
    def _is_dir_from_item(item: dict) -> bool:
        """更健壮的目录判断逻辑，支持多种API返回格式"""
        # 检查多个可能的字段名称和格式
        # isFile: true=文件, false=目录
        if "isFile" in item:
            v = item["isFile"]
            if isinstance(v, bool):
                return not v
            if isinstance(v, int):
                return v == 0
            if isinstance(v, str):
                return v.lower() in ("false", "0", "no")
        
        # type: 0=目录, 1=文件 或 "directory"=目录
        if "type" in item:
            v = item["type"]
            if isinstance(v, bool):
                return not v
            if isinstance(v, int):
                return v == 0
            if isinstance(v, str):
                return v.lower() in ("directory", "0", "dir")
        
        # isDir: true=目录, false=文件
        if "isDir" in item:
            v = item["isDir"]
            if isinstance(v, bool):
                return v
            if isinstance(v, int):
                return v == 1
            if isinstance(v, str):
                return v.lower() in ("true", "1", "yes")
        
        # 默认情况下，如果没有明确标识，假设为文件
        return False

    @staticmethod
    def _is_log_file(name: str) -> bool:
        if name == "eula.txt":
            return False
        return name.endswith(".log") or name.endswith(".txt") or name.endswith(".gz") or "crash" in name.lower()

    def _on_file_list(self, files):
        if not files:
            self._file_combo["values"] = ["未找到日志文件"]
            self._set_log_text("")
            return

        files.sort()
        self._file_combo["values"] = files
        self._file_combo.set(files[0] if files else "")
        self._load_selected_log()

    def _load_selected_log(self):
        filename = self._file_combo.get()
        if not filename or filename in ("请先配置实例", "请先登录", "未找到日志文件"):
            return

        self.app._set_status(f"正在加载: {filename}")

        file_path = filename
        is_gz = file_path.endswith('.gz')

        def do_load():
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".log" if not is_gz else ".gz")
            tmp.close()
            ok = self.app.api.download_file(
                self.app._daemon_id, self.app._instance_uuid,
                file_path, tmp.name,
            )
            if ok:
                try:
                    if is_gz:
                        with gzip.open(tmp.name, 'rt', encoding='utf-8', errors='replace') as f:
                            text = f.read()
                    else:
                        with open(tmp.name, encoding='utf-8', errors='replace') as f:
                            text = f.read()
                except Exception:
                    text = "读取文件失败"
                os.unlink(tmp.name)
                self.app.root.after(0, lambda: self._set_log_text(text))
                self.app.root.after(0, lambda: self.app._set_status(f"已加载: {filename}"))
            else:
                os.unlink(tmp.name)
                self.app.root.after(0, lambda: self._set_log_text(f"加载日志失败: {filename}"))
                self.app.root.after(0, lambda: self.app._set_status("加载失败"))

        threading.Thread(target=do_load, daemon=True).start()

    def _refresh_content(self):
        self._load_selected_log()

    @staticmethod
    def _format_size(size: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
