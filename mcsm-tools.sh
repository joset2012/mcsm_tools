#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$DIR/.venv"



if [ -d "$VENV" ]; then
    source "$VENV/bin/activate"
    exec python -m mcsm_tools "$@"
else
    exec python3 -m mcsm_tools "$@"
fi
