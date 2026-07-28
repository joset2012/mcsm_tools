import math
import threading
import time
import tkinter as tk
from tkinter import ttk
from datetime import datetime

from .font_helper import MONO_FONT
from .theme import Nord


MAX_POINTS = 60
POLL_INTERVAL = 5


class DashboardTab:
    def __init__(self, notebook, app):
        self.app = app
        self.frame = ttk.Frame(notebook)
        self._running = False

        self._tps_history: list[float] = []
        self._mem_history: list[float] = []
        self._player_history: list[int] = []
        self._events: list[str] = []
        self._max_events = 50

        self._build_ui()
        self._start_polling()

    def _build_ui(self):
        canvas = tk.Canvas(self.frame, bg=Nord.bg, highlightthickness=0)
        v_scroll = ttk.Scrollbar(self.frame, orient=tk.VERTICAL, command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=v_scroll.set)

        def _on_mousewheel(event):
            canvas.yview_scroll(-1 * (event.delta // 120), "units")
        def _on_mousewheel_linux_up(event):
            canvas.yview_scroll(-3, "units")
        def _on_mousewheel_linux_down(event):
            canvas.yview_scroll(3, "units")
        scroll_frame.bind("<MouseWheel>", _on_mousewheel)
        scroll_frame.bind("<Button-4>", _on_mousewheel_linux_up)
        scroll_frame.bind("<Button-5>", _on_mousewheel_linux_down)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        main = ttk.Frame(scroll_frame)
        main.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)

        header = ttk.Label(main, text="实例概览仪表盘", style='Heading.TLabel')
        header.pack(pady=(0, 12))

        info_frame = ttk.Frame(main)
        info_frame.pack(fill=tk.X, pady=(0, 12))

        status_lf = ttk.LabelFrame(info_frame, text="实例状态", padding=10)
        status_lf.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        self._status_text = ttk.Label(status_lf, text="未连接", font=('', 11, 'bold'))
        self._status_text.pack(anchor=tk.W, pady=2)
        self._online_text = ttk.Label(status_lf, text="在线: -")
        self._online_text.pack(anchor=tk.W, pady=2)
        self._mem_text = ttk.Label(status_lf, text="内存: -")
        self._mem_text.pack(anchor=tk.W, pady=2)
        self._tps_text = ttk.Label(status_lf, text="TPS: -")
        self._tps_text.pack(anchor=tk.W, pady=2)

        info_lf = ttk.LabelFrame(info_frame, text="实例信息", padding=10)
        info_lf.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))

        self._instance_info = ttk.Label(info_lf, text="Daemon: -\nUUID: -\n名称: -")
        self._instance_info.pack(anchor=tk.W, pady=2)

        charts_frame = ttk.Frame(main)
        charts_frame.pack(fill=tk.BOTH, expand=True)

        self._chart_tps = self._create_chart(charts_frame, "TPS 趋势", Nord.aurora_green)
        self._chart_tps.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        self._chart_player = self._create_chart(charts_frame, "在线玩家", Nord.aurora_pink)
        self._chart_player.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))

        events_lf = ttk.LabelFrame(main, text="最近事件", padding=8)
        events_lf.pack(fill=tk.X, pady=(12, 0))

        self._events_text = tk.Text(events_lf, height=6, wrap=tk.WORD,
                                     font=(MONO_FONT, 9),
                                     bg=Nord.bg_alt, fg=Nord.fg,
                                     borderwidth=0, highlightthickness=0,
                                     state=tk.DISABLED)
        self._events_text.pack(fill=tk.X)

    def _create_chart(self, parent, title: str, color: str):
        frame = ttk.LabelFrame(parent, text=title, padding=4)
        canvas_w = 400
        canvas_h = 160
        c = tk.Canvas(frame, bg=Nord.bg_alt, highlightthickness=0)
        c.pack(fill=tk.BOTH, expand=True)
        c.data = []
        c.color = color
        c.max_val = 100
        c._redraw = lambda: self._redraw_chart(c)
        frame.canvas = c
        return frame

    def _redraw_chart(self, canvas: tk.Canvas):
        canvas.delete("all")
        data = canvas.data
        if not data:
            return
        w = canvas.winfo_width() or 400
        h = canvas.winfo_height() or 160
        if w < 10:
            return

        max_val = max(data) if data else 1
        if max_val == 0:
            max_val = 1
        canvas.max_val = max_val

        pad_l, pad_r, pad_t, pad_b = 30, 10, 10, 20
        plot_w = w - pad_l - pad_r
        plot_h = h - pad_t - pad_b

        if plot_w < 10 or plot_h < 10:
            return

        n = len(data)
        points = []
        for i, val in enumerate(data):
            x = pad_l + (i / max(n - 1, 1)) * plot_w
            y = pad_t + plot_h - (val / max_val) * plot_h
            points.append((x, y))

        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            canvas.create_line(x1, y1, x2, y2, fill=canvas.color, width=2)

        if data:
            cur = data[-1]
            x, y = points[-1]
            canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill=canvas.color, outline="")
            canvas.create_text(x - 8, y - 10, text=f"{cur:.1f}" if isinstance(cur, float) else str(cur),
                               anchor=tk.E, fill=canvas.color, font=(MONO_FONT, 8))

        canvas.create_text(pad_l, pad_t - 2, text=str(max_val), anchor=tk.W,
                           fill=Nord.polar_night_4, font=(MONO_FONT, 7))
        canvas.create_text(pad_l, pad_t + plot_h + 2, text="0", anchor=tk.W,
                           fill=Nord.polar_night_4, font=(MONO_FONT, 7))
        canvas.create_text(w - pad_r, pad_t + plot_h + 2, text=n,
                           anchor=tk.E, fill=Nord.polar_night_4, font=(MONO_FONT, 7))

    def _start_polling(self):
        self._running = True

        def poll():
            while self._running:
                self._poll_once()
                time.sleep(POLL_INTERVAL)

        t = threading.Thread(target=poll, daemon=True)
        t.start()

    def _poll_once(self):
        if not self.app.api.is_authenticated or not self.app._daemon_id:
            return
        try:
            info = self.app.api.get_instance_info(self.app._daemon_id, self.app._instance_uuid)
            if info:
                instance = info.get("instance", info)

                mem_raw = instance.get("memory", None)
                if isinstance(mem_raw, (int, float)):
                    if mem_raw > 1e9:
                        mem_mb = mem_raw / (1024 * 1024)
                    elif mem_raw > 1e6:
                        mem_mb = mem_raw / 1024
                    else:
                        mem_mb = mem_raw
                    self._mem_history.append(mem_mb)
                    if len(self._mem_history) > MAX_POINTS:
                        self._mem_history.pop(0)

                try:
                    tps_val = float(instance.get("tps", instance.get("Tps", instance.get("TPS", 0))))
                    if tps_val > 0:
                        self._tps_history.append(tps_val)
                        if len(self._tps_history) > MAX_POINTS:
                            self._tps_history.pop(0)
                except (ValueError, TypeError):
                    pass

                if self.app.terminal and self.app.terminal.online_players:
                    player_count = len(self.app.terminal.online_players)
                    self._player_history.append(player_count)
                    if len(self._player_history) > MAX_POINTS:
                        self._player_history.pop(0)

                self.app.root.after(0, lambda: self._update_display(instance))

        except Exception:
            pass

    def _update_display(self, instance: dict):
        status = instance.get("status", -1)
        status_map = {0: "已停止", 1: "运行中", 2: "启动中", 3: "停止中"}
        color_map = {0: Nord.aurora_green, 1: Nord.aurora_red, 2: Nord.aurora_yellow, 3: Nord.aurora_orange}
        status_text = status_map.get(status, "未知")
        color = color_map.get(status, Nord.fg)
        self._status_text.config(text=f"状态: {status_text}", foreground=color)

        online = len(self.app.terminal.online_players or set())
        self._online_text.config(text=f"在线: {online} 人")

        if self._mem_history:
            mem = self._mem_history[-1]
            self._mem_text.config(text=f"内存: {mem:.0f} MB  (峰值 {max(self._mem_history):.0f} MB)")
        if self._tps_history:
            tps = self._tps_history[-1]
            self._tps_text.config(text=f"TPS: {tps:.1f}")

        daemon = self.app._daemon_id[:20] + "..." if len(self.app._daemon_id) > 20 else self.app._daemon_id
        uuid = self.app._instance_uuid[:12] + "..." if len(self.app._instance_uuid) > 12 else self.app._instance_uuid
        name = self.app.cfg.instance_name or "-"
        self._instance_info.config(text=f"Daemon: {daemon}\nUUID: {uuid}\n名称: {name}")

        self._chart_tps.canvas.data = self._tps_history[-MAX_POINTS:]
        self._chart_tps.canvas._redraw()
        self._chart_player.canvas.data = self._player_history[-MAX_POINTS:]
        self._chart_player.canvas._redraw()

    def add_event(self, text: str):
        now = datetime.now().strftime("%H:%M:%S")
        self._events.append(f"[{now}] {text}")
        if len(self._events) > self._max_events:
            self._events.pop(0)
        self._events_text.config(state=tk.NORMAL)
        self._events_text.insert(tk.END, self._events[-1] + "\n")
        self._events_text.see(tk.END)
        self._events_text.config(state=tk.DISABLED)

    def stop(self):
        self._running = False
