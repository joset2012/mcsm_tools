import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from mcsm_tools.system_check import run as system_check

system_check()

if len(sys.argv) > 1 and sys.argv[1] == "--terminal":
    from mcsm_tools.terminal_cli import run_terminal
    run_terminal()
else:
    from mcsm_tools.gui import MCSMGUI
    app = MCSMGUI()
    app.run()
