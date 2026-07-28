import json
import sys
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter

from .config import load_config, save_config
from .api import MCSManagerAPI
from .terminal import MCSMTerminal, apply_player_events
from .auth import save_credentials, load_credentials, clear_credentials, secure_input


def run_terminal():
    cfg = load_config()
    api = MCSManagerAPI(cfg.base_url)

    _authenticate(api, cfg)

    daemon_id = cfg.daemon_id
    instance_uuid = cfg.instance_uuid

    if not daemon_id or not instance_uuid:
        print("自动发现实例...")
        result = api.auto_discover_instance(cfg.instance_name or None)
        if result:
            daemon_id, instance_uuid = result
            cfg.daemon_id = daemon_id
            cfg.instance_uuid = instance_uuid
            save_config(cfg)
            print("已保存实例 ID")
        else:
            print("自动发现失败")
            sys.exit(1)

    result = api.get_websocket_password(daemon_id, instance_uuid)
    if not result:
        print(f"获取 WebSocket 连接信息失败: {api.last_error}")
        sys.exit(1)

    password, addr = result
    term = MCSMTerminal()

    online_players: set[str] = set()

    history = InMemoryHistory()
    term.on_disconnect = lambda: print("\n连接断开")

    def on_output(text):
        print(text, end='')
        apply_player_events(text, online_players)

    term.on_output = on_output

    static_words = ['!help', '!upload', '!kill', '!open', '!send', '!clear']

    def get_words():
        return static_words + list(online_players)

    completer = WordCompleter(get_words, ignore_case=True)
    session = PromptSession(
        history=history,
        auto_suggest=AutoSuggestFromHistory(),
        completer=completer,
        complete_while_typing=True,
    )

    print("正在连接终端...")
    if not term.connect(addr, password, cfg.base_url):
        print(term.last_error or "连接失败")
        sys.exit(1)
    print("终端已连接，输入 !help 查看帮助")

    try:
        while True:
            try:
                with patch_stdout():
                    cmd = session.prompt('> ')
            except (EOFError, KeyboardInterrupt):
                print("\n退出")
                break

            if not cmd.strip():
                continue

            if cmd.startswith('!'):
                parts = cmd.split(maxsplit=1)
                command = parts[0].lower()

                if command == '!help':
                    print("控制命令:")
                    print("  !help          显示帮助")
                    print("  !upload <本地> <目录>  上传文件")
                    print("  !kill          强制关闭")
                    print("  !open          启动实例")
                    print("  !send <JSON>   手动发送事件")
                    print("  !clear         清屏")
                    print("  exit/quit      退出")
                elif command == '!clear':
                    print("\033[2J\033[H", end='')
                elif command == '!upload':
                    if len(parts) < 2:
                        print("用法: !upload <本地路径> <远程目录>")
                    else:
                        args = parts[1].split(maxsplit=1)
                        if len(args) < 2:
                            print("请指定本地路径和远程目录")
                        else:
                            ok = api.upload_file(args[0], args[1], daemon_id, instance_uuid)
                            print("上传成功" if ok else f"上传失败: {api.last_error}")
                elif command == '!kill':
                    ok = api.kill_instance(daemon_id, instance_uuid)
                    print("实例已关闭" if ok else "关闭失败")
                elif command == '!open':
                    ok = api.open_instance(daemon_id, instance_uuid)
                    print("实例已启动" if ok else "启动失败")
                elif command == '!send':
                    if len(parts) < 2:
                        print("用法: !send <JSON>")
                    else:
                        try:
                            data = json.loads(parts[1])
                            if "event" in data:
                                ev = data["event"]
                                del data["event"]
                                term.send_raw(ev, data)
                            else:
                                print("请指定 event 字段")
                        except json.JSONDecodeError:
                            print("JSON 格式错误")
                else:
                    print(f"未知命令: {command}")
            else:
                term.send_command(cmd)

    finally:
        term.disconnect()


def _authenticate(api: MCSManagerAPI, cfg) -> None:
    if cfg.apikey:
        api.set_apikey(cfg.apikey)
        if api.validate_credentials():
            print("API Key 有效")
            return
        print("配置的 API Key 无效")

    if cfg.token:
        api.set_auth(cfg.token, cfg.cookie)
        if api.validate_credentials():
            print("配置的凭证有效")
            return

    creds = load_credentials()
    if creds:
        api.set_auth(creds.token, creds.cookie)
        if api.validate_credentials():
            print("使用已保存的凭证")
            return
        clear_credentials()

    choice = input("登录方式 (1=密码登录, 2=API Key): ").strip()
    if choice == "2":
        apikey = input("API Key: ").strip()
        api.set_apikey(apikey)
        if not api.validate_credentials():
            print("API Key 验证失败")
            sys.exit(1)
        cfg.apikey = apikey
        cfg.token = ""
        cfg.cookie = ""
    else:
        username = cfg.username
        password = cfg.password
        if not username:
            username = input("用户名: ").strip()
        if not password:
            password = secure_input(f"密码 ({username}): " if username else "密码: ")
        if not api.login(username, password):
            print(f"登录失败: {api.last_error or '请检查用户名密码'}")
            sys.exit(1)
        save_credentials(api.token, api.cookie, api.session)
        cfg.username = username
        cfg.password = password
        cfg.token = api.token
        cfg.cookie = api.cookie

    save_config(cfg)


if __name__ == "__main__":
    run_terminal()
