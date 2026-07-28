#!/usr/bin/env bash
set -e

PYTHON="python3"
PIP="pip3"
VENV_DIR=".venv"

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${CYAN}[mcsm-tools]${NC} $1"; }
ok()    { echo -e "${GREEN}[mcsm-tools]${NC} $1"; }
warn()  { echo -e "${YELLOW}[mcsm-tools]${NC} $1"; }
err()   { echo -e "${RED}[mcsm-tools]${NC} $1"; }

cd "$(dirname "$0")"

# ── Python ──
PY_VERSION=$($PYTHON --version 2>/dev/null || true)
if [ -z "$PY_VERSION" ]; then
    PYTHON="python"
    PY_VERSION=$($PYTHON --version 2>/dev/null || true)
fi

if [ -z "$PY_VERSION" ]; then
    err "Python 未安装，请先安装 Python >= 3.10"
    err "  Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
    err "  Fedora:        sudo dnf install python3 python3-pip"
    err "  Arch:          sudo pacman -S python python-pip"
    exit 1
fi

PY_MAJOR=$($PYTHON -c "import sys; print(sys.version_info.major)")
PY_MINOR=$($PYTHON -c "import sys; print(sys.version_info.minor)")
info "检测到 $PYTHON: $PY_VERSION"

if [ "$PY_MAJOR" -lt 3 ] || [ "$PY_MAJOR" -eq 3 -a "$PY_MINOR" -lt 10 ]; then
    err "需要 Python >= 3.10，当前为 $PY_VERSION"
    exit 1
fi
ok "Python 版本符合要求"

# ── 虚拟环境 ──
if [ ! -d "$VENV_DIR" ]; then
    info "创建虚拟环境 $VENV_DIR ..."
    $PYTHON -m venv "$VENV_DIR"
    ok "虚拟环境已创建"
fi
source "$VENV_DIR/bin/activate"
ok "虚拟环境已激活"

# ── pip 依赖 ──
info "安装 Python 依赖..."
"$VENV_DIR/bin/pip" install --upgrade pip -q
"$VENV_DIR/bin/pip" install -r requirements.txt -q
ok "Python 依赖安装完成"

# ── 7-Zip ──
if command -v 7z &>/dev/null; then
    ok "7-Zip 已安装: $(command -v 7z)"
else
    warn "7-Zip 未安装"
    warn "解压非 .zip 格式和使用本地压缩功能需要 7-Zip"
    echo ""
    echo "  安装方式："
    echo "    Ubuntu/Debian: sudo apt install p7zip-full"
    echo "    Fedora:        sudo dnf install p7zip p7zip-plugins"
    echo "    Arch:          sudo pacman -S p7zip"
    echo "    macOS:         brew install p7zip"
    echo ""
fi

# ── 完成 ──
echo ""
ok "安装完成！"
echo ""
echo "  启动方式："
echo "    1) 激活虚拟环境后运行:"
echo "       source $VENV_DIR/bin/activate"
echo "       python -m mcsm_tools"
echo ""
echo "    2) 或使用快捷脚本:"
echo "       ./mcsm-tools.sh"
echo ""
