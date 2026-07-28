#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

VENV="$DIR/.venv"
if [ -d "$VENV" ]; then
    source "$VENV/bin/activate"
else
    python3 -m venv "$VENV"
    source "$VENV/bin/activate"
    pip install -q -r requirements.txt
fi

pip install -q pyinstaller

pyinstaller \
    --name mcsm-tools \
    --onefile \
    --distpath ./dist \
    --workpath ./build \
    --add-data "$DIR/mcsm_tools/fonts:mcsm_tools/fonts" \
    --hidden-import engineio \
    --hidden-import engineio.client \
    --hidden-import prompt_toolkit \
    --hidden-import requests \
    --hidden-import PyQt5 \
    --hidden-import PyQt5.QtCore \
    --hidden-import PyQt5.QtGui \
    --hidden-import PyQt5.QtWidgets \
    "$DIR/run.py"

echo ""
echo "构建完成: dist/mcsm-tools"
