#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$DIR/.venv"

export XMODIFIERS="${XMODIFIERS:-@im=fcitx}"
export GTK_IM_MODULE="${GTK_IM_MODULE:-fcitx}"
export QT_IM_MODULE="${QT_IM_MODULE:-fcitx}"

if [ -d "$VENV" ]; then
    source "$VENV/bin/activate"
    exec python -m mcsm_tools "$@"
else
    exec python3 -m mcsm_tools "$@"
fi
