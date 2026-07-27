#!/usr/bin/env python3
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if len(sys.argv) > 1 and sys.argv[1] == "--gui":
    from mcsm_tools.gui import MCSMGUI
    app = MCSMGUI()
    app.run()
else:
    from mcsm_tools.terminal_cli import run_terminal
    run_terminal()
