---
name: testing-mcsm-tools
description: How to run and GUI-test the mcsm_tools desktop app (PyQt5 / tkinter / CLI) on a headless Linux box, including config-home isolation and how to verify behaviour without a live MCSManager panel.
---

# Testing mcsm_tools

## Environment

- venv at `.venv`; deps via `.venv/bin/pip install -r requirements-dev.txt`.
- System packages needed for the GUIs: `python3-tk`, `xvfb`, plus `wmctrl`/`xdotool` for window control.
- Lint: `.venv/bin/ruff check .` — Tests: `.venv/bin/python -m pytest -q`.

## Launching

```
MCSM_TOOLS_HOME=/tmp/mcsmA PYTHONPATH=/path/to/repo DISPLAY=:0 \
  .venv/bin/python -m mcsm_tools          # PyQt5 (default)
  .venv/bin/python -m mcsm_tools --tk     # legacy tkinter GUI
  .venv/bin/python -m mcsm_tools --terminal   # CLI
```

- **Always set `MCSM_TOOLS_HOME` to a throwaway dir** so the app does not touch the real
  `~/.mcsm_tools`. Everything (`mcsm_config.ini`, `command_history.json`,
  `command_favorites.json`, `.mcsm_credentials`) lands there with mode 0600.
- **Set `PYTHONPATH` to the repo root** if you launch from a different CWD (needed to test
  legacy-config migration, which reads `./mcsm_config.ini` from the CWD).
- Launch with `nohup ... > /tmp/app.log 2>&1 &` and read the log file — tracebacks from GUI
  callbacks only appear on stderr, never in the UI.

## Window handling (headless X / Plasma)

```
DISPLAY=:0 wmctrl -l                                   # find the window
DISPLAY=:0 xdotool windowactivate <id>                 # more reliable than `wmctrl -a`
DISPLAY=:0 wmctrl -r "MCSM Tools" -b add,maximized_vert,maximized_horz
DISPLAY=:0 wmctrl -r "MCSM Tools" -e 0,100,80,760,520  # resize test
```

Window titles: PyQt5 = `MCSM Tools`; tkinter = `mcsm-tools - MCSManager 管理工具`.
After closing/relaunching, the new window often opens behind Chrome — re-activate it
explicitly before taking screenshots.

## Where the UI lives

- PyQt5: settings are a **modal dialog under the 文件 → 设置 menu** (not a tab). Tabs are
  连接 / 终端 / 文件管理 / 日志 / 备份 / 玩家 / 插件Mod.
- tkinter: settings are the last **tab** (设置), with 保存设置 / 自动发现实例 / 清除凭证 buttons
  and inline 密码登录 / API Key 登录 buttons. Tabs are 终端 / 仪表盘 / 文件管理 / 日志查看 /
  备份 / 玩家管理 / 插件Mod / 设置.
- In tk `Entry` widgets **`Ctrl+A` means "go to line start", not select-all** — use a
  triple-click (or `Ctrl+A` then `shift+End`) before typing to replace a value, otherwise
  you silently prepend text.

## Testing without a live MCSManager panel

There is usually no panel and no credentials. Point 面板地址 at `http://127.0.0.1:23333`
(nothing listening) to get fast, deterministic connection failures, and assert on
**graceful degradation** instead of success:

- unauthenticated tabs render a `请先登录` placeholder;
- 密码登录 → `登录失败，请检查用户名和密码`; API Key 登录 → `API Key 无效，请检查后重试`;
- CLI `--terminal` prints the system-check lines, prompts 登录方式, and exits 1 with
  `API Key 验证失败`.

Anything requiring a successful login (credential file write/migration, instance
auto-discovery, terminal websocket, remote file/backup/plugin operations) is **not
testable** in this setup — say so rather than inferring it works.

The CLI reads with `input()`, so run it in a PTY (`exec` with `tty: true`); piping stdin
produces an `EOFError` traceback that is not a real bug in interactive use.

## Verifying config storage

```
stat -c '%a %n' $MCSM_TOOLS_HOME/*     # expect 600 on every file
ls -a $MCSM_TOOLS_HOME | grep tmp      # expect none: writes are atomic via mkstemp+replace
ls -a $CWD                             # expect empty: nothing should be written to the CWD
```

Legacy migration: put an old-style `mcsm_config.ini` with distinctive values in an empty
CWD, point `MCSM_TOOLS_HOME` at a **non-existent** dir, launch, and confirm the values show
up in the GUI and in the new file. The legacy file is copied, not deleted.

## Devin Secrets Needed

None for the offline/graceful-failure coverage described above. To exercise live panel
flows you would need a reachable MCSManager panel URL plus either an API key or a
username/password for it — none exist in this environment today.
