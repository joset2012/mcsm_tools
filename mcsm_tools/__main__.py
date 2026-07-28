import sys


def main():
    from .system_check import run as system_check
    system_check()

    if len(sys.argv) > 1 and sys.argv[1] == "--terminal":
        from .terminal_cli import run_terminal
        run_terminal()
    elif len(sys.argv) > 1 and sys.argv[1] == "--tk":
        from .gui import MCSMGUI
        app = MCSMGUI()
        app.run()
    else:
        from .gui_pyqt import main as pyqt_main
        pyqt_main()


if __name__ == "__main__":
    main()
