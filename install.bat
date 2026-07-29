# install.ps1
# 用法：.\install.ps1
# 若首次运行提示禁止执行，请以管理员身份运行：
# Set-ExecutionPolicy RemoteSigned -Scope CurrentUser

$ErrorActionPreference = "Stop"
$VENV_DIR = ".venv"

# ----- 设置 pip 镜像源（加速下载） -----
$PIP_INDEX = "https://pypi.tuna.tsinghua.edu.cn/simple"
# 备选：阿里云  https://mirrors.aliyun.com/pypi/simple/
# 备选：中科大  https://pypi.mirrors.ustc.edu.cn/simple/
# 备选：豆瓣    https://pypi.douban.com/simple/

function Write-Info   { Write-Host "[mcsm-tools]" $args -ForegroundColor Cyan }
function Write-Ok     { Write-Host "[mcsm-tools]" $args -ForegroundColor Green }
function Write-Warn   { Write-Host "[mcsm-tools]" $args -ForegroundColor Yellow }
function Write-Error  { Write-Host "[mcsm-tools]" $args -ForegroundColor Red }

Write-Info "mcsm-tools 依赖安装脚本"
Write-Host ""

# 检查 Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command python3 -ErrorAction SilentlyContinue
}
if (-not $python) {
    Write-Error "Python 未安装，请先安装 Python >= 3.10"
    Write-Error "  下载地址: https://www.python.org/downloads/"
    Write-Host "   安装时请勾选 'Add Python to PATH'"
    Read-Host "按 Enter 退出"
    exit 1
}

$pyVersion = & $python.Source -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$major, $minor = $pyVersion -split '\.'
if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 10)) {
    Write-Error "需要 Python >= 3.10，当前为 $pyVersion"
    Read-Host "按 Enter 退出"
    exit 1
}
Write-Ok "Python 版本符合要求 ($pyVersion)"

# 虚拟环境
if (-not (Test-Path $VENV_DIR)) {
    Write-Info "创建虚拟环境 $VENV_DIR ..."
    & $python.Source -m venv $VENV_DIR
    Write-Ok "虚拟环境已创建"
}
Write-Ok "虚拟环境已就绪"

# 设置 pip 使用镜像（通过环境变量，当前进程生效）
$env:PIP_INDEX_URL = $PIP_INDEX

# 升级 pip
Write-Info "升级 pip ..."
& "$VENV_DIR\Scripts\python" -m pip install --upgrade pip -q
if ($LASTEXITCODE -ne 0) {
    Write-Error "升级 pip 失败"
    Read-Host "按 Enter 退出"
    exit 1
}

# 安装依赖
Write-Info "安装 Python 依赖（使用镜像 $PIP_INDEX）..."
& "$VENV_DIR\Scripts\python" -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Error "依赖安装失败"
    Read-Host "按 Enter 退出"
    exit 1
}
Write-Ok "Python 依赖安装完成"

# 检查 7-Zip
$7z = Get-Command 7z -ErrorAction SilentlyContinue
if ($7z) {
    Write-Ok "7-Zip 已安装 ($($7z.Source))"
} else {
    Write-Warn "7-Zip 未安装"
    Write-Warn "解压非 .zip 格式和使用本地压缩功能需要 7-Zip"
    Write-Host ""
    Write-Host "  下载地址: https://7-zip.org/download.html"
    Write-Host ""
}

# 完成
Write-Host ""
Write-Ok "安装完成！"
Write-Host ""
Write-Host "  启动方式："
Write-Host "    1) 激活虚拟环境后运行:"
Write-Host "       .\$VENV_DIR\Scripts\Activate.ps1"
Write-Host "       python -m mcsm_tools"
Write-Host ""
Write-Host "    2) 直接运行（使用快捷脚本）:"
Write-Host "       .\mcsm-tools.ps1"
Write-Host ""
Read-Host "按 Enter 退出"
