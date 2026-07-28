import argparse

from . import __app_name__, __version__


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog=__app_name__,
        description="MCSManager 服务器管理工具",
    )
    parser.add_argument("--version", action="version", version=f"{__app_name__} {__version__}")
    ui = parser.add_mutually_exclusive_group()
    ui.add_argument("--terminal", action="store_true", help="启动 CLI 终端模式")
    ui.add_argument("--tk", action="store_true", help="启动旧版 tkinter 界面")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None):
    args = _parse_args(argv)

    from .system_check import run as system_check
    system_check()

    if args.terminal:
        from .terminal_cli import run_terminal
        run_terminal()
    elif args.tk:
        from .gui import MCSMGUI
        MCSMGUI().run()
    else:
        from .gui_pyqt import main as pyqt_main
        pyqt_main()


if __name__ == "__main__":
    main()
