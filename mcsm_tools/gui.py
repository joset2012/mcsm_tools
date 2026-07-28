import json
import os
import re
import shutil
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from datetime import datetime


from .config import AppConfig, load_config, save_config
from .api import MCSManagerAPI
from .terminal import MCSMTerminal
from .auth import save_credentials, load_credentials, clear_credentials
from .command_history import CommandHistory
from . import __version__
from .theme import Nord
from .font_helper import MONO_FONT, ensure_font_installed


_ANSI_RE = re.compile(r'\x1b\[([\d;]*)m')


def parse_ansi(text: str):
    parts = _ANSI_RE.split(text)
    segments = []
    fg = None
    bg = None
    bold = False
    for i, part in enumerate(parts):
        if i % 2 == 0:
            segments.append((fg, bg, bold, part))
        else:
            codes = part.split(';') if part else []
            for c in codes:
                if c == '' or c == '0':
                    fg = bg = None; bold = False
                elif c == '1':
                    bold = True
                elif c == '22':
                    bold = False
                elif c in Nord.ansi_colors:
                    fg = Nord.ansi_colors[c]
                elif c in Nord.ansi_bg:
                    bg = Nord.ansi_bg[c]
    return segments


class ConsoleText(tk.Text):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.config(state=tk.DISABLED)
        self._ansi_tags = set()

    def _get_ansi_tag(self, fg, bg, bold):
        tag = f"ansi_{fg or 'none'}_{bg or 'none'}_{bold}"
        if tag not in self._ansi_tags:
            cfg = {}
            if fg:
                cfg['foreground'] = fg
            if bg:
                cfg['background'] = bg
            if bold:
                cfg['font'] = (MONO_FONT, 10, 'bold')
            self.tag_config(tag, **cfg)
            self._ansi_tags.add(tag)
        return tag

    def append(self, text: str, parse_ansi_codes=True):
        self.config(state=tk.NORMAL)
        end = self.index(tk.END + '-1c')
        if parse_ansi_codes and '\x1b[' in text:
            for fg, bg, bold, segment in parse_ansi(text):
                if not segment:
                    continue
                tag = self._get_ansi_tag(fg, bg, bold)
                self.insert(tk.END, segment, tag)
        else:
            self.insert(tk.END, text)
        self.see(tk.END)
        self.config(state=tk.DISABLED)

    def clear(self):
        self.config(state=tk.NORMAL)
        self.delete('1.0', tk.END)
        self.config(state=tk.DISABLED)


class MCSMGUI:
    def __init__(self):
        ensure_font_installed()
        self.root = tk.Tk()
        self._set_icon()
        self.root.title("mcsm-tools - MCSManager 管理工具")
        self.root.geometry("1100x720")
        self.root.minsize(900, 600)

        self.cfg: AppConfig = load_config()
        self.api = MCSManagerAPI(self.cfg.base_url)
        self.terminal = MCSMTerminal()
        self._cmd_history = CommandHistory()
        self._terminal_thread: threading.Thread | None = None
        self._term_log_file = None
        self._term_log_loaded = False
        self._running = False
        self._daemon_id = self.cfg.daemon_id
        self._instance_uuid = self.cfg.instance_uuid

        self._apply_auth_from_config()
        self._build_ui()
        self._center_window()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        if self.cfg.auto_connect and self.cfg.is_instance_configured:
            self.root.after(500, self._auto_connect_terminal)

    def _set_icon(self):
        _dir = os.path.dirname(__file__)
        if sys.platform == "win32":
            ico = os.path.join(_dir, "icon.ico")
            if os.path.exists(ico):
                try:
                    self.root.iconbitmap(ico)
                except Exception:
                    pass
        else:
            png = os.path.join(_dir, "icon.png")
            if os.path.exists(png):
                try:
                    img = tk.PhotoImage(file=png)
                    self.root.iconphoto(True, img)
                except Exception:
                    pass

    def _center_window(self):
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _apply_auth_from_config(self):
        if self.cfg.apikey:
            self.api.set_apikey(self.cfg.apikey)
        elif self.cfg.token:
            self.api.set_auth(self.cfg.token, self.cfg.cookie)

    def _get_term_log_dir(self) -> str:
        uid = f"{self._daemon_id}_{self._instance_uuid}" if self._daemon_id and self._instance_uuid else "default"
        d = os.path.expanduser(os.path.join("~", ".mcsm_tools", "terminal", uid))
        os.makedirs(d, exist_ok=True)
        return d

    def _build_ui(self):
        self._apply_nord_theme()
        self._build_menu()
        self._build_statusbar()
        self._build_notebook()

    def _apply_nord_theme(self):
        style = ttk.Style()
        style.theme_use('clam')

        style.configure('.', background=Nord.bg, foreground=Nord.fg,
                        fieldbackground=Nord.bg_alt,
                        selectbackground=Nord.bg_sel, selectforeground=Nord.fg)

        style.configure('TFrame', background=Nord.bg)

        style.configure('TLabel', background=Nord.bg, foreground=Nord.fg)
        style.configure('Heading.TLabel', font=('', 11, 'bold'),
                         foreground=Nord.snow_storm_3)

        style.configure('TButton', background=Nord.bg_alt, foreground=Nord.fg,
                        bordercolor=Nord.polar_night_4, focuscolor='none',
                        lightcolor=Nord.bg_alt, darkcolor=Nord.bg_alt,
                        borderwidth=1, padding=(12, 4))
        style.map('TButton',
                  background=[('active', Nord.bg_sel), ('pressed', Nord.polar_night_4)],
                  foreground=[('active', Nord.snow_storm_3)],
                  bordercolor=[('active', Nord.frost_4)])

        style.configure('Small.TButton', padding=(8, 2))

        style.configure('TEntry', fieldbackground=Nord.bg_alt, foreground=Nord.fg,
                        insertcolor=Nord.fg, borderwidth=1, padding=(4, 2))
        style.map('TEntry',
                  bordercolor=[('focus', Nord.frost_4), ('!focus', Nord.polar_night_4)])

        style.configure('TNotebook', background=Nord.bg, borderwidth=0)
        style.configure('TNotebook.Tab',
                        background=Nord.polar_night_2, foreground=Nord.polar_night_4,
                        padding=[8, 2], borderwidth=0)
        style.map('TNotebook.Tab',
                  background=[('selected', Nord.bg), ('active', Nord.polar_night_3)],
                  foreground=[('selected', Nord.snow_storm_3), ('active', Nord.fg),
                              ('!selected', Nord.fg)],
                  padding=[('selected', [18, 8])])

        style.configure('Treeview', background=Nord.bg_alt, foreground=Nord.fg,
                        fieldbackground=Nord.bg, borderwidth=0)
        style.map('Treeview', background=[('selected', Nord.bg_sel)])

        style.configure('Vertical.TScrollbar', background=Nord.bg_alt,
                        troughcolor=Nord.bg, bordercolor=Nord.bg, arrowcolor=Nord.fg)
        style.configure('Horizontal.TScrollbar', background=Nord.bg_alt,
                        troughcolor=Nord.bg, bordercolor=Nord.bg, arrowcolor=Nord.fg)

        style.configure('TCombobox', fieldbackground=Nord.bg_alt,
                        foreground=Nord.fg, arrowcolor=Nord.fg)

        style.configure('TCheckbutton', background=Nord.bg, foreground=Nord.fg,
                        focuscolor='none')

        style.configure('TLabelframe', background=Nord.bg, foreground=Nord.snow_storm_3,
                        borderwidth=1, bordercolor=Nord.polar_night_3)
        style.configure('TLabelframe.Label', background=Nord.bg,
                        foreground=Nord.snow_storm_3, font=('', 10, 'bold'))

        style.configure('TProgressbar', background=Nord.frost_3,
                        troughcolor=Nord.bg_alt, borderwidth=0)

        style.configure('TSeparator', background=Nord.polar_night_3)

        style.configure('Bordered.TFrame', background=Nord.bg_alt,
                        borderwidth=1, bordercolor=Nord.polar_night_3, relief='solid')

        style.layout('TNotebook.Tab', [
            ('Notebook.tab', {'sticky': 'nswe', 'children': [
                ('Notebook.padding', {'side': 'top', 'sticky': 'nswe', 'children': [
                    ('Notebook.focus', {'side': 'top', 'sticky': 'nswe', 'children': [
                        ('Notebook.label', {'side': 'top', 'sticky': ''})
                    ]})
                ]})
            ]})
        ])

        self.root.config(bg=Nord.bg)

    def _build_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="设置", command=self._show_settings, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self._on_close)

        instance_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="实例", menu=instance_menu)
        instance_menu.add_command(label="连接终端", command=self._connect_terminal)
        instance_menu.add_command(label="断开终端", command=self._disconnect_terminal)
        instance_menu.add_separator()
        instance_menu.add_command(label="启动实例", command=self._open_instance)
        instance_menu.add_command(label="强制关闭", command=self._kill_instance)
        instance_menu.add_separator()
        instance_menu.add_command(label="自动发现实例", command=self._auto_discover)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="关于", command=self._show_about)

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=6, pady=(4, 0))

        self._build_terminal_tab()
        self._build_dashboard_tab()
        self._build_file_manager_tab()
        self._build_log_viewer_tab()
        self._build_backup_tab()
        self._build_player_tab()
        self._build_plugin_tab()
        self._build_settings_tab()

    def _build_terminal_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="  终端  ")

        toolbar = ttk.Frame(frame)
        toolbar.pack(fill=tk.X, padx=8, pady=(6, 2))

        group_conn = ttk.Frame(toolbar)
        group_conn.pack(side=tk.LEFT)
        ttk.Button(group_conn, text="连接", style='Small.TButton',
                   command=self._connect_terminal).pack(side=tk.LEFT, padx=1)
        ttk.Button(group_conn, text="断开", style='Small.TButton',
                   command=self._disconnect_terminal).pack(side=tk.LEFT, padx=1)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        group_action = ttk.Frame(toolbar)
        group_action.pack(side=tk.LEFT)
        self._btn_open = ttk.Button(group_action, text="启动", style='Small.TButton',
                                    command=self._open_instance)
        self._btn_open.pack(side=tk.LEFT, padx=1)
        self._btn_kill = ttk.Button(group_action, text="强制关闭", style='Small.TButton',
                                    command=self._kill_instance)
        self._btn_kill.pack(side=tk.LEFT, padx=1)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        ttk.Button(toolbar, text="清屏", style='Small.TButton',
                   command=self._clear_terminal).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="历史", style='Small.TButton',
                   command=self._show_command_history).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="收藏", style='Small.TButton',
                   command=self._show_command_favorites).pack(side=tk.LEFT, padx=1)

        self._term_conn_label = ttk.Label(toolbar, text="● 未连接",
                                          foreground=Nord.polar_night_4)
        self._term_conn_label.pack(side=tk.RIGHT, padx=6)

        console_bg = ttk.Frame(frame, style='Bordered.TFrame')
        console_bg.pack(fill=tk.BOTH, expand=True, padx=8, pady=(2, 0))

        self._term_output = ConsoleText(console_bg, wrap=tk.WORD,
                                        font=(MONO_FONT, 10),
                                        bg=Nord.bg, fg=Nord.fg,
                                        insertbackground=Nord.snow_storm_3,
                                        borderwidth=0, highlightthickness=0)
        self._term_output.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        scrollbar = ttk.Scrollbar(self._term_output, command=self._term_output.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._term_output.config(yscrollcommand=scrollbar.set)

        input_outer = ttk.Frame(frame)
        input_outer.pack(fill=tk.X, padx=8, pady=(3, 6))

        input_frame = ttk.Frame(input_outer, style='Bordered.TFrame')
        input_frame.pack(fill=tk.X)

        self._cmd_var = tk.StringVar()
        self._cmd_entry = ttk.Entry(input_frame, textvariable=self._cmd_var,
                                    font=(MONO_FONT, 10))
        self._cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True,
                             padx=6, pady=4)
        self._cmd_entry.bind("<Return>", self._send_command)
        self._cmd_entry.bind("<Up>", lambda e: self._history_navigate("prev"))
        self._cmd_entry.bind("<Down>", lambda e: self._history_navigate("next"))
        self._cmd_entry.bind("<Control-r>", self._show_command_search)
        self._cmd_entry.bind("<Control-f>", self._show_command_search)
        self._cmd_entry.bind("<Control-d>", lambda e: self._save_favorite())

        send_btn = ttk.Button(input_frame, text="发送", width=6,
                              command=self._send_command)
        send_btn.pack(side=tk.RIGHT, padx=(0, 4), pady=4)

        self.terminal.on_output = self._on_terminal_output
        self.terminal.on_connect = lambda: self.root.after(0, self._on_terminal_connected)
        self.terminal.on_disconnect = lambda: self.root.after(0, self._on_terminal_disconnected)

    def _build_file_manager_tab(self):
        from .file_manager import FileManagerTab
        self._fm_tab = FileManagerTab(self.notebook, self)
        self.notebook.add(self._fm_tab.frame, text="  文件管理  ")

    def _build_log_viewer_tab(self):
        from .log_viewer import LogViewerTab
        self._lv_tab = LogViewerTab(self.notebook, self)
        self.notebook.add(self._lv_tab.frame, text="  日志查看  ")

    def _build_dashboard_tab(self):
        from .dashboard import DashboardTab
        self._dash_tab = DashboardTab(self.notebook, self)
        self.notebook.add(self._dash_tab.frame, text="  仪表盘  ")

    def _build_backup_tab(self):
        from .backup_manager import BackupManagerTab
        self._backup_tab = BackupManagerTab(self.notebook, self)
        self.notebook.add(self._backup_tab.frame, text="  备份  ")

    def _build_player_tab(self):
        from .player_manager import PlayerManagerTab
        self._player_tab = PlayerManagerTab(self.notebook, self)
        self.notebook.add(self._player_tab.frame, text="  玩家管理  ")

    def _build_plugin_tab(self):
        from .plugin_manager import PluginManagerTab
        self._plugin_tab = PluginManagerTab(self.notebook, self)
        self.notebook.add(self._plugin_tab.frame, text="  插件/Mod  ")

    def _build_settings_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="  设置  ")

        canvas = tk.Canvas(frame, bg=Nord.bg, highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def _on_mousewheel(event):
            canvas.yview_scroll(-1 * (event.delta // 120), "units")
        def _on_mousewheel_linux_up(event):
            canvas.yview_scroll(-3, "units")
        def _on_mousewheel_linux_down(event):
            canvas.yview_scroll(3, "units")
        scroll_frame.bind("<MouseWheel>", _on_mousewheel)
        scroll_frame.bind("<Button-4>", _on_mousewheel_linux_up)
        scroll_frame.bind("<Button-5>", _on_mousewheel_linux_down)

        main = ttk.Frame(scroll_frame)
        main.pack(fill=tk.BOTH, expand=True, padx=30, pady=24)

        # ── 面板设置 ──
        panel_lf = ttk.LabelFrame(main, text="面板设置", padding=14)
        panel_lf.pack(fill=tk.X, pady=(0, 12))

        ttk.Label(panel_lf, text="面板地址").grid(row=0, column=0, sticky=tk.W, pady=4)
        self._cfg_base_url = ttk.Entry(panel_lf, width=60)
        self._cfg_base_url.insert(0, self.cfg.base_url)
        self._cfg_base_url.grid(row=0, column=1, sticky=tk.EW, pady=4, padx=(8, 0))
        panel_lf.columnconfigure(1, weight=1)

        # ── 登录设置 ──
        auth_lf = ttk.LabelFrame(main, text="登录设置", padding=14)
        auth_lf.pack(fill=tk.X, pady=(0, 12))

        ttk.Label(auth_lf, text="用户名").grid(row=0, column=0, sticky=tk.W, pady=4)
        entry_frame0 = ttk.Frame(auth_lf)
        entry_frame0.grid(row=0, column=1, sticky=tk.EW, pady=4, padx=(8, 0))
        self._cfg_username = ttk.Entry(entry_frame0, width=30)
        self._cfg_username.insert(0, self.cfg.username)
        self._cfg_username.pack(side=tk.LEFT)
        ttk.Label(entry_frame0, text="密码").pack(side=tk.LEFT, padx=(10, 4))
        self._cfg_password = ttk.Entry(entry_frame0, width=20, show="*")
        self._cfg_password.insert(0, self.cfg.password)
        self._cfg_password.pack(side=tk.LEFT)
        ttk.Button(entry_frame0, text="密码登录", style='Small.TButton',
                   command=self._login).pack(side=tk.LEFT, padx=(10, 0))
        auth_lf.columnconfigure(1, weight=1)

        ttk.Label(auth_lf, text="API Key").grid(row=1, column=0, sticky=tk.W, pady=4)
        entry_frame1 = ttk.Frame(auth_lf)
        entry_frame1.grid(row=1, column=1, sticky=tk.EW, pady=4, padx=(8, 0))
        self._cfg_apikey = ttk.Entry(entry_frame1, width=45, show="*")
        self._cfg_apikey.insert(0, self.cfg.apikey)
        self._cfg_apikey.pack(side=tk.LEFT)
        ttk.Button(entry_frame1, text="API Key 登录", style='Small.TButton',
                   command=self._login_with_apikey).pack(side=tk.LEFT, padx=(10, 0))
        auth_lf.columnconfigure(1, weight=1)

        # ── 实例设置 ──
        inst_lf = ttk.LabelFrame(main, text="实例设置", padding=14)
        inst_lf.pack(fill=tk.X, pady=(0, 12))

        ttk.Label(inst_lf, text="Daemon ID").grid(row=0, column=0, sticky=tk.W, pady=4)
        self._cfg_daemon_id = ttk.Entry(inst_lf, width=60)
        self._cfg_daemon_id.insert(0, self.cfg.daemon_id)
        self._cfg_daemon_id.grid(row=0, column=1, sticky=tk.EW, pady=4, padx=(8, 0))

        ttk.Label(inst_lf, text="Instance UUID").grid(row=1, column=0, sticky=tk.W, pady=4)
        self._cfg_instance_uuid = ttk.Entry(inst_lf, width=60)
        self._cfg_instance_uuid.insert(0, self.cfg.instance_uuid)
        self._cfg_instance_uuid.grid(row=1, column=1, sticky=tk.EW, pady=4, padx=(8, 0))

        ttk.Label(inst_lf, text="实例名称").grid(row=2, column=0, sticky=tk.W, pady=4)
        self._cfg_instance_name = ttk.Entry(inst_lf, width=30)
        self._cfg_instance_name.insert(0, self.cfg.instance_name)
        self._cfg_instance_name.grid(row=2, column=1, sticky=tk.W, pady=4, padx=(8, 0))
        inst_lf.columnconfigure(1, weight=1)

        # ── 功能设置 ──
        feat_lf = ttk.LabelFrame(main, text="功能设置", padding=14)
        feat_lf.pack(fill=tk.X, pady=(0, 12))

        self._cfg_auto_connect = tk.BooleanVar(value=self.cfg.auto_connect)
        ttk.Checkbutton(feat_lf, text="启动时自动连接终端",
                        variable=self._cfg_auto_connect).pack(anchor=tk.W, pady=3)
        self._cfg_term_memory = tk.BooleanVar(value=self.cfg.terminal_memory)
        ttk.Checkbutton(feat_lf, text="终端记忆（记录上一次的终端输出）",
                        variable=self._cfg_term_memory).pack(anchor=tk.W, pady=3)
        self._cfg_show_exit = tk.BooleanVar(value=self.cfg.show_exit_dialog)
        ttk.Checkbutton(feat_lf, text="退出时显示确认对话框",
                        variable=self._cfg_show_exit).pack(anchor=tk.W, pady=3)

        # ── 按钮 ──
        sep = ttk.Separator(main, orient=tk.HORIZONTAL)
        sep.pack(fill=tk.X, pady=(4, 10))

        btn_frame = ttk.Frame(main)
        btn_frame.pack(pady=(0, 10))
        ttk.Button(btn_frame, text="保存设置", width=14,
                   command=self._save_settings).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="自动发现实例", width=14,
                   command=self._auto_discover).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="清除凭证", width=14,
                   command=self._clear_auth).pack(side=tk.LEFT, padx=4)

    def _build_statusbar(self):
        sep = ttk.Separator(self.root, orient=tk.HORIZONTAL)
        sep.pack(fill=tk.X, side=tk.BOTTOM)

        self._statusbar = ttk.Frame(self.root)
        self._statusbar.pack(fill=tk.X, side=tk.BOTTOM)

        self._status_label = ttk.Label(self._statusbar, text="就绪",
                                       anchor=tk.W, padding=(6, 2))
        self._status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._instance_label = ttk.Label(self._statusbar, text="实例: -",
                                         anchor=tk.W, padding=(6, 2), width=35)
        self._instance_label.pack(side=tk.RIGHT)

        self._online_label = ttk.Label(self._statusbar, text="在线: -",
                                       anchor=tk.W, padding=(6, 2), width=15)
        self._online_label.pack(side=tk.RIGHT)

        self._update_statusbar()

    def _set_status(self, text: str):
        self._status_label.config(text=text)

    def _update_statusbar(self):
        instance_id = self._instance_uuid[:12] + "..." if len(self._instance_uuid) > 12 else self._instance_uuid
        self._instance_label.config(text=f"实例: {instance_id or '-'}")
        self.root.after(5000, self._update_statusbar)

    def _save_settings(self):
        self.cfg.base_url = self._cfg_base_url.get().strip()
        self.cfg.username = self._cfg_username.get().strip()
        self.cfg.password = self._cfg_password.get().strip()
        self.cfg.daemon_id = self._cfg_daemon_id.get().strip()
        self.cfg.instance_uuid = self._cfg_instance_uuid.get().strip()
        self.cfg.instance_name = self._cfg_instance_name.get().strip()
        self.cfg.apikey = self._cfg_apikey.get().strip()
        self.cfg.auto_connect = self._cfg_auto_connect.get()
        self.cfg.terminal_memory = self._cfg_term_memory.get()
        self.cfg.show_exit_dialog = self._cfg_show_exit.get()
        save_config(self.cfg)
        self.api.base_url = self.cfg.base_url
        self.api._update_headers()
        if self.cfg.apikey:
            self.api.set_apikey(self.cfg.apikey)
        elif self.cfg.token:
            self.api.set_auth(self.cfg.token, self.cfg.cookie)
        self._daemon_id = self.cfg.daemon_id
        self._instance_uuid = self.cfg.instance_uuid
        self._set_status("设置已保存")
        messagebox.showinfo("保存成功", "配置已保存")

    def _login(self):
        if self.api.is_authenticated:
            messagebox.showinfo("已登录", "您已经登录过了")
            return
        username = self._cfg_username.get().strip()
        password = self._cfg_password.get().strip()
        if not username or not password:
            messagebox.showwarning("输入错误", "请输入用户名和密码")
            return

        self._set_status("正在登录...")
        def do_login():
            ok = self.api.login(username, password)
            self.root.after(0, lambda: self._on_login_result(ok, username, password))
        threading.Thread(target=do_login, daemon=True).start()

    def _on_login_result(self, ok: bool, username: str, password: str):
        if ok:
            self.cfg.token = self.api.token
            self.cfg.cookie = self.api.cookie
            self.cfg.username = username
            self.cfg.password = password
            save_config(self.cfg)
            try:
                save_credentials(self.api.token, self.api.cookie, self.api.session)
            except Exception:
                pass
            self._set_status("登录成功")
            messagebox.showinfo("登录成功", "已成功登录 MCSManager")
            self._fm_tab._refresh_remote()
            self._lv_tab._refresh_file_list()
        else:
            self._set_status("登录失败")
            messagebox.showerror("登录失败", "登录失败，请检查用户名和密码")

    def _login_with_apikey(self):
        if self.api.is_authenticated:
            messagebox.showinfo("已登录", "您已经登录过了")
            return
        apikey = self._cfg_apikey.get().strip()
        if not apikey:
            messagebox.showwarning("输入错误", "请输入 API Key")
            return

        self._set_status("正在验证 API Key...")
        api = self.api

        def do_login():
            api.set_apikey(apikey)
            ok = api.validate_credentials()
            self.root.after(0, lambda: self._on_apikey_result(ok, apikey))

        threading.Thread(target=do_login, daemon=True).start()

    def _on_apikey_result(self, ok: bool, apikey: str):
        if ok:
            self.cfg.apikey = apikey
            self.cfg.token = ""
            self.cfg.cookie = ""
            save_config(self.cfg)
            self._set_status("API Key 登录成功")
            messagebox.showinfo("登录成功", "API Key 验证通过")
            self._fm_tab._refresh_remote()
            self._lv_tab._refresh_file_list()
        else:
            self.api.apikey = ""
            self.api._clear_auth_headers()
            self._set_status("API Key 验证失败")
            messagebox.showerror("验证失败", "API Key 无效，请检查后重试")

    def _clear_auth(self):
        if messagebox.askyesno("确认", "确定清除所有凭证信息吗？"):
            self.cfg.token = ""
            self.cfg.cookie = ""
            self.cfg.username = ""
            self.cfg.password = ""
            self.cfg.apikey = ""
            save_config(self.cfg)
            clear_credentials()
            self.api.token = ""
            self.api.cookie = ""
            self.api.apikey = ""
            self.api._clear_auth_headers()
            self._set_status("凭证已清除")
            messagebox.showinfo("已清除", "所有凭证信息已清除")
            self._fm_tab._refresh_remote()
            self._lv_tab._refresh_file_list()

    def _auto_discover(self):
        self._set_status("正在自动发现实例...")
        if not self.api.is_authenticated:
            cfg = self._load_current_settings()
            if cfg.apikey:
                def do_apikey_discover():
                    self.api.set_apikey(cfg.apikey)
                    if self.api.validate_credentials():
                        self.cfg.apikey = cfg.apikey
                        self.cfg.token = ""
                        self.cfg.cookie = ""
                        result = self.api.auto_discover_instance(cfg.instance_name or None)
                        self.root.after(0, lambda: self._on_discover_result(result))
                    else:
                        self.api.apikey = ""
                        self.api._clear_auth_headers()
                        self.root.after(0, lambda: self._set_status("自动发现失败: API Key 无效"))
                threading.Thread(target=do_apikey_discover, daemon=True).start()
            elif cfg.username and cfg.password:
                def do_login_and_discover():
                    ok = self.api.login(cfg.username, cfg.password)
                    if ok:
                        self.cfg.token = self.api.token
                        self.cfg.cookie = self.api.cookie
                        result = self.api.auto_discover_instance(cfg.instance_name or None)
                        self.root.after(0, lambda: self._on_discover_result(result))
                    else:
                        self.root.after(0, lambda: self._set_status("自动发现失败: 登录失败"))
                threading.Thread(target=do_login_and_discover, daemon=True).start()
            else:
                self._set_status("请先输入登录信息")
                messagebox.showwarning("需要登录", "请先输入 API Key、用户名和密码，或手动配置 Token")
        else:
            def do_discover():
                result = self.api.auto_discover_instance(self.cfg.instance_name or None)
                self.root.after(0, lambda: self._on_discover_result(result))
            threading.Thread(target=do_discover, daemon=True).start()

    def _on_discover_result(self, result):
        if result:
            daemon_id, instance_uuid = result
            self._daemon_id = daemon_id
            self._instance_uuid = instance_uuid
            self.cfg.daemon_id = daemon_id
            self.cfg.instance_uuid = instance_uuid
            save_config(self.cfg)

            self._cfg_daemon_id.delete(0, tk.END)
            self._cfg_daemon_id.insert(0, daemon_id)
            self._cfg_instance_uuid.delete(0, tk.END)
            self._cfg_instance_uuid.insert(0, instance_uuid)

            self._set_status(f"已发现实例: {daemon_id}")
            messagebox.showinfo("发现成功", f"已自动发现实例\nDaemon: {daemon_id}\nUUID: {instance_uuid}")
        else:
            self._set_status("自动发现失败")
            messagebox.showerror("发现失败", "未找到可用的实例")

    def _connect_terminal(self):
        if self.terminal.is_connected:
            messagebox.showinfo("已连接", "终端已连接")
            return

        if not self.api.is_authenticated:
            self.api.refresh_auth_from_config(self.cfg)
            if not self.api.is_authenticated:
                messagebox.showwarning("未登录", "请在设置中登录")
                self.notebook.select(7)
                return

        if not self._daemon_id or not self._instance_uuid:
            messagebox.showwarning("未配置", "请先配置或自动发现实例")
            self.notebook.select(7)
            return

        self._set_status("正在连接终端...")

        def do_connect():
            result = self.api.get_websocket_password(self._daemon_id, self._instance_uuid)
            if result:
                password, addr = result
                ok = self.terminal.connect(addr, password, self.cfg.base_url)
                self.root.after(0, lambda: self._on_connect_result(ok))
            else:
                err = self.api.last_error or "获取密码失败"
                self.root.after(0, lambda: self._set_status(f"终端连接失败: {err}"))

        threading.Thread(target=do_connect, daemon=True).start()

    def _history_navigate(self, direction: str):
        if direction == "prev":
            cmd = self._cmd_history.prev()
        else:
            cmd = self._cmd_history.next()
        if cmd is not None:
            self._cmd_var.set(cmd)
            self._cmd_entry.icursor(tk.END)

    def _show_command_search(self, event=None):
        dialog = tk.Toplevel(self.root)
        dialog.title("搜索命令历史")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(True, False)
        dialog.config(bg=Nord.bg)
        w, h = 500, 400
        sw = dialog.winfo_screenwidth()
        sh = dialog.winfo_screenheight()
        dialog.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        frame = ttk.Frame(dialog, padding=8)
        frame.pack(fill=tk.BOTH, expand=True)

        search_frame = ttk.Frame(frame)
        search_frame.pack(fill=tk.X)
        ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT)
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, font=(MONO_FONT, 10))
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        search_entry.focus_set()

        listbox = tk.Listbox(frame, font=(MONO_FONT, 10),
                             bg=Nord.bg_alt, fg=Nord.fg,
                             selectbackground=Nord.bg_sel,
                             borderwidth=0, highlightthickness=0)
        listbox.pack(fill=tk.BOTH, expand=True, pady=4)

        scroll = ttk.Scrollbar(listbox, orient=tk.VERTICAL, command=listbox.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        listbox.configure(yscrollcommand=scroll.set)

        results: list[str] = []

        def update_search(*args):
            nonlocal results
            q = search_var.get()
            results = self._cmd_history.search(q) if q else self._cmd_history.get_recent(50)
            listbox.delete(0, tk.END)
            for r in results:
                listbox.insert(tk.END, r)

        search_var.trace_add("write", update_search)
        update_search()

        def use_selected():
            sel = listbox.curselection()
            if sel:
                idx = sel[0]
                if idx < len(results):
                    self._cmd_var.set(results[idx])
                    self._cmd_entry.icursor(tk.END)
                    self._cmd_entry.focus_set()
                    dialog.destroy()

        listbox.bind("<Double-1>", lambda e: use_selected())
        listbox.bind("<Return>", lambda e: use_selected())

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="使用", command=use_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="收藏", command=lambda: self._save_favorite_from_search(listbox, results)).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="关闭", command=dialog.destroy).pack(side=tk.RIGHT, padx=2)

    def _show_command_history(self):
        results = self._cmd_history.get_recent(50)
        dialog = tk.Toplevel(self.root)
        dialog.title("命令历史")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.config(bg=Nord.bg)
        w, h = 500, 400
        sw = dialog.winfo_screenwidth()
        sh = dialog.winfo_screenheight()
        dialog.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        frame = ttk.Frame(dialog, padding=8)
        frame.pack(fill=tk.BOTH, expand=True)

        listbox = tk.Listbox(frame, font=(MONO_FONT, 10),
                             bg=Nord.bg_alt, fg=Nord.fg,
                             selectbackground=Nord.bg_sel,
                             borderwidth=0, highlightthickness=0)
        listbox.pack(fill=tk.BOTH, expand=True)

        for r in results:
            listbox.insert(tk.END, r)

        def use_selected():
            sel = listbox.curselection()
            if sel:
                idx = sel[0]
                if idx < len(results):
                    self._cmd_var.set(results[idx])
                    self._cmd_entry.icursor(tk.END)
                    self._cmd_entry.focus_set()
                    dialog.destroy()

        listbox.bind("<Double-1>", lambda e: use_selected())

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(btn_frame, text="使用", command=use_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="关闭", command=dialog.destroy).pack(side=tk.RIGHT, padx=2)

    def _show_command_favorites(self):
        favs = self._cmd_history.favorites
        dialog = tk.Toplevel(self.root)
        dialog.title("收藏命令")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.config(bg=Nord.bg)
        w, h = 500, 400
        sw = dialog.winfo_screenwidth()
        sh = dialog.winfo_screenheight()
        dialog.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        frame = ttk.Frame(dialog, padding=8)
        frame.pack(fill=tk.BOTH, expand=True)

        toolbar = ttk.Frame(frame)
        toolbar.pack(fill=tk.X)
        ttk.Button(toolbar, text="添加当前命令", command=self._save_favorite).pack(side=tk.LEFT, padx=2)
        sep_btn = ttk.Button(toolbar, text="移除所选", command=lambda: self._remove_favorite(listbox, favs))
        sep_btn.pack(side=tk.LEFT, padx=2)

        listbox = tk.Listbox(frame, font=(MONO_FONT, 10),
                             bg=Nord.bg_alt, fg=Nord.fg,
                             selectbackground=Nord.bg_sel,
                             borderwidth=0, highlightthickness=0)
        listbox.pack(fill=tk.BOTH, expand=True, pady=4)

        for f in favs:
            label = f.get("label", f["cmd"])
            listbox.insert(tk.END, f"{label}")

        def use_selected():
            sel = listbox.curselection()
            if sel:
                idx = sel[0]
                if idx < len(favs):
                    self._cmd_var.set(favs[idx]["cmd"])
                    self._cmd_entry.icursor(tk.END)
                    self._cmd_entry.focus_set()
                    dialog.destroy()

        listbox.bind("<Double-1>", lambda e: use_selected())

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="使用", command=use_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="关闭", command=dialog.destroy).pack(side=tk.RIGHT, padx=2)

    def _save_favorite(self):
        cmd = self._cmd_var.get().strip()
        if cmd:
            self._cmd_history.add_favorite(cmd)
            self._set_status(f"已收藏: {cmd}")

    def _save_favorite_from_search(self, listbox, results):
        sel = listbox.curselection()
        if sel:
            idx = sel[0]
            if idx < len(results):
                self._cmd_history.add_favorite(results[idx])
                self._set_status(f"已收藏: {results[idx]}")

    def _remove_favorite(self, listbox, favs):
        sel = listbox.curselection()
        if sel:
            idx = sel[0]
            if idx < len(favs):
                cmd = favs[idx]["cmd"]
                self._cmd_history.remove_favorite(cmd)
                self._show_command_favorites()
                self._set_status(f"已移除收藏: {cmd}")

    def _download_world(self):
        if not self._daemon_id or not self._instance_uuid:
            messagebox.showwarning("未配置", "请先配置实例")
            return
        if not self.api.is_authenticated:
            messagebox.showwarning("未登录", "请先登录")
            return

        world_dirs = ["world", "worlds", "world_nether", "world_the_end"]
        self._set_status("正在检测世界文件夹...")

        def do_detect():
            found = []
            for wd in world_dirs:
                items = self.api.list_files(
                    self._daemon_id, self._instance_uuid, f"/{wd}"
                )
                if items is not None:
                    found.append(wd)
            self.root.after(0, lambda: self._on_world_detected(found))

        threading.Thread(target=do_detect, daemon=True).start()

    def _on_world_detected(self, found: list[str]):
        if not found:
            messagebox.showwarning("未找到世界", "未在远程实例中检测到世界文件夹")
            self._set_status("世界下载失败")
            return

        selected = found
        if len(found) > 1:
            dialog = tk.Toplevel(self.root)
            dialog.title("选择世界")
            dialog.transient(self.root)
            dialog.grab_set()
            dialog.config(bg=Nord.bg)
            w, h = 300, 200
            sw = dialog.winfo_screenwidth()
            sh = dialog.winfo_screenheight()
            dialog.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

            frame = ttk.Frame(dialog, padding=12)
            frame.pack(fill=tk.BOTH, expand=True)

            ttk.Label(frame, text="发现多个世界文件夹，选择要下载的:").pack(pady=(0, 8))

            var = tk.StringVar(value=found[0])
            for wd in found:
                ttk.Radiobutton(frame, text=wd, variable=var, value=wd).pack(anchor=tk.W, padx=12)

            result = [None]

            def on_ok():
                result[0] = var.get()
                dialog.destroy()

            ttk.Button(frame, text="下载", command=on_ok).pack(pady=(8, 0))
            dialog.protocol("WM_DELETE_WINDOW", lambda: dialog.destroy())
            dialog.wait_window()
            if result[0] is None:
                return
            selected = [result[0]]

        save_dir = filedialog.askdirectory(title="选择保存位置", initialdir=os.path.expanduser("~"))
        if not save_dir:
            return

        name = f"{selected[0]}.zip"
        save_path = os.path.join(save_dir, name)

        self._set_status(f"正在压缩并下载世界: {selected[0]}...")

        def do_download():
            try:
                archive_path = f"/_world_download_{selected[0]}"
                ok = self.api.compress_files(
                    self._daemon_id, self._instance_uuid,
                    archive_path, [f"/{selected[0]}"]
                )
                if not ok:
                    self.root.after(0, lambda: self._on_world_download_result(False, "压缩失败"))
                    return

                def progress(cur, total):
                    pct = int(cur / total * 100) if total > 0 else 0
                    self.root.after(0, lambda v=pct: self._set_status(f"正在下载世界... {v}%"))

                ok = self.api.download_file(
                    self._daemon_id, self._instance_uuid,
                    archive_path, save_path, progress_callback=progress
                )

                self.api.delete_files(
                    self._daemon_id, self._instance_uuid, [archive_path]
                )

                self.root.after(0, lambda: self._on_world_download_result(ok, save_path))
            except Exception as e:
                self.root.after(0, lambda: self._on_world_download_result(False, str(e)))

        threading.Thread(target=do_download, daemon=True).start()

    def _on_world_download_result(self, ok: bool, msg: str):
        if ok:
            self._set_status(f"世界已下载: {msg}")
            messagebox.showinfo("下载完成", f"世界已保存到:\n{msg}")
        else:
            self._set_status(f"世界下载失败: {msg}")
            messagebox.showerror("下载失败", msg)

    def _auto_connect_terminal(self):
        if self.terminal.is_connected:
            return
        if not self.api.is_authenticated:
            self.api.refresh_auth_from_config(self.cfg)
            if not self.api.is_authenticated:
                return
        self._connect_terminal()

    def _on_connect_result(self, ok: bool):
        if ok:
            self._set_status("终端已连接")
            self._term_conn_label.config(text="● 已连接", foreground=Nord.aurora_green)
        else:
            err = self.terminal.last_error or "未知错误"
            self._set_status(f"终端连接失败: {err}")
            self._term_conn_label.config(text="● 连接失败", foreground=Nord.aurora_red)

    def _disconnect_terminal(self):
        self.terminal.disconnect()
        self._set_status("终端已断开")
        self._term_conn_label.config(text="● 未连接", foreground=Nord.polar_night_4)

    def _on_terminal_connected(self):
        self._term_conn_label.config(text="● 已连接", foreground=Nord.aurora_green)
        if not self._term_log_loaded and self.cfg.terminal_memory:
            log_dir = self._get_term_log_dir()
            a_path = os.path.join(log_dir, "session_a.log")
            b_path = os.path.join(log_dir, "session_b.log")
            if self._term_log_file:
                try:
                    self._term_log_file.close()
                except Exception:
                    pass
            try:
                self._term_log_file = open(b_path, "w", encoding="utf-8")
            except Exception:
                self._term_log_file = None
            if os.path.exists(a_path):
                try:
                    with open(a_path, "r", encoding="utf-8") as f:
                        prev = f.read()
                    if prev:
                        self._term_output.clear()
                        self._term_output.append(prev, parse_ansi_codes=False)
                except Exception:
                    pass
            self._term_log_loaded = True

    def _on_terminal_disconnected(self):
        self._term_conn_label.config(text="● 未连接", foreground=Nord.polar_night_4)
        self._set_status("终端已断开")

    def _on_terminal_output(self, text: str):
        self.root.after(0, lambda: self._term_output.append(text))
        if self._term_log_file:
            try:
                self._term_log_file.write(text)
                self._term_log_file.flush()
            except Exception:
                pass

    def _send_command(self, event=None):
        cmd = self._cmd_var.get().strip()
        if not cmd:
            return
        self._cmd_var.set("")
        self._cmd_history.add(cmd)
        self._cmd_history.reset_pos()

        if cmd.startswith('!'):
            parts = cmd.split(maxsplit=1)
            command = parts[0].lower()

            if command == '!help':
                help_text = (
                    "控制命令:\n"
                    "  !upload <本地> <远程目录>  上传文件\n"
                    "  !kill          强制关闭实例\n"
                    "  !open          启动实例\n"
                    "  !send <JSON>   发送 WebSocket 事件\n"
                    "  !clear         清屏\n"
                )
                self._term_output.append(help_text)
            elif command == '!clear':
                self._term_output.clear()
            elif command == '!upload':
                self._term_output.append("请使用文件管理标签页上传文件\n")
            elif command == '!kill':
                self._kill_instance()
            elif command == '!open':
                self._open_instance()
            elif command == '!send':
                if len(parts) < 2:
                    self._term_output.append("用法: !send <JSON>\n")
                else:
                    try:
                        data = json.loads(parts[1])
                        if "event" in data:
                            event = data["event"]
                            del data["event"]
                            self.terminal.send_raw(event, data)
                        else:
                            self._term_output.append("请指定 event 字段\n")
                    except json.JSONDecodeError:
                        self._term_output.append("JSON 格式错误\n")
            else:
                self._term_output.append(f"未知命令: {command}\n")
        else:
            self._term_output.append(f"> {cmd}\n")
            self.terminal.send_command(cmd)

    def _clear_terminal(self):
        self._term_output.clear()

    def _open_instance(self):
        if not self._daemon_id or not self._instance_uuid:
            messagebox.showwarning("未配置", "请先配置实例")
            return
        self._set_status("正在启动实例...")
        def do_open():
            ok = self.api.open_instance(self._daemon_id, self._instance_uuid)
            self.root.after(0, lambda: self._on_instance_action("启动", ok))
        threading.Thread(target=do_open, daemon=True).start()

    def _kill_instance(self):
        if not self._daemon_id or not self._instance_uuid:
            messagebox.showwarning("未配置", "请先配置实例")
            return
        if not messagebox.askyesno("确认", "确定要强制关闭实例吗？"):
            return
        self._set_status("正在关闭实例...")
        def do_kill():
            ok = self.api.kill_instance(self._daemon_id, self._instance_uuid)
            self.root.after(0, lambda: self._on_instance_action("关闭", ok))
        threading.Thread(target=do_kill, daemon=True).start()

    def _on_instance_action(self, action: str, ok: bool):
        if ok:
            self._set_status(f"实例{action}成功")
            self._term_output.append(f"✅ 实例已{action}\n")
        else:
            self._set_status(f"实例{action}失败")
            self._term_output.append(f"❌ 实例{action}失败\n")

    def _load_current_settings(self) -> AppConfig:
        cfg = AppConfig()
        cfg.base_url = self._cfg_base_url.get().strip() or self.cfg.base_url
        cfg.username = self._cfg_username.get().strip() or self.cfg.username
        cfg.password = self._cfg_password.get().strip() or self.cfg.password
        cfg.daemon_id = self._cfg_daemon_id.get().strip() or self.cfg.daemon_id
        cfg.instance_uuid = self._cfg_instance_uuid.get().strip() or self.cfg.instance_uuid
        cfg.instance_name = self._cfg_instance_name.get().strip() or self.cfg.instance_name
        cfg.token = self.cfg.token
        cfg.cookie = self.cfg.cookie
        cfg.apikey = self._cfg_apikey.get().strip() or self.cfg.apikey
        return cfg

    def _show_settings(self):
        self.notebook.select(7)

    def _show_about(self):
        from . import __version__
        messagebox.showinfo("关于 mcsm-tools",
                            f"mcsm-tools v{__version__}\n\n"
                            "MCSManager 服务器管理工具\n"
                            "支持终端控制、文件管理、日志查看等功能")

    def _finalize_terminal_logs(self):
        if not self.cfg.terminal_memory:
            return
        if self._term_log_file:
            try:
                self._term_log_file.close()
            except Exception:
                pass
            self._term_log_file = None
        try:
            log_dir = self._get_term_log_dir()
            a_path = os.path.join(log_dir, "session_a.log")
            b_path = os.path.join(log_dir, "session_b.log")
            if os.path.exists(b_path):
                shutil.move(b_path, a_path)
        except Exception:
            pass

    def _on_close(self):
        if not self.cfg.show_exit_dialog:
            self._running = False
            self.terminal.disconnect()
            self._finalize_terminal_logs()
            try:
                self._dash_tab.stop()
            except Exception:
                pass
            self.root.destroy()
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("确认退出")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        w, h = 380, 170
        sw = dialog.winfo_screenwidth()
        sh = dialog.winfo_screenheight()
        dialog.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        dialog.config(bg=Nord.bg)

        frame = ttk.Frame(dialog, padding=24)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="确定要退出 mcsm-tools 吗？",
                  font=('', 11)).pack(pady=(0, 18))

        dont_show = tk.BooleanVar(value=False)
        cb = ttk.Checkbutton(frame, text="不再显示此确认",
                             variable=dont_show)
        cb.pack(pady=(0, 18))

        btn_frame = ttk.Frame(frame)
        btn_frame.pack()

        result = [False]

        def on_confirm():
            result[0] = True
            if dont_show.get():
                self.cfg.show_exit_dialog = False
                save_config(self.cfg)
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        ttk.Button(btn_frame, text="退出", width=10, command=on_confirm).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="取消", width=10, command=on_cancel).pack(side=tk.LEFT, padx=6)

        dialog.protocol("WM_DELETE_WINDOW", on_cancel)
        dialog.wait_window()

        if result[0]:
            self._running = False
            self.terminal.disconnect()
            self._finalize_terminal_logs()
            try:
                self._dash_tab.stop()
            except Exception:
                pass
            self.root.destroy()

    def run(self):
        self._running = True
        self.root.mainloop()
