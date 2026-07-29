# build.ps1
# 智能构建：检测当前路径是否含中文，自动选择直接构建或临时目录构建
# 用法：.\build.ps1

$ErrorActionPreference = "Stop"

# ----- 配置 -----
$PIP_INDEX = "https://pypi.tuna.tsinghua.edu.cn/simple"   # pip 镜像源
$TEMP_ROOT = "D:\"                                         # 临时目录根路径（必须英文）
# 若 D: 不可用，可改为 $env:TEMP 或 "C:\temp"
# $TEMP_ROOT = $env:TEMP

# ----- 辅助函数：检测路径是否包含非 ASCII 字符（中文等）-----
function HasNonAscii {
    param([string]$path)
    foreach ($c in $path.ToCharArray()) {
        if ([int]$c -gt 127) {
            return $true
        }
    }
    return $false
}

# ----- 获取当前目录 -----
$ORIG_DIR = $PWD.Path
Write-Host "[构建] 当前目录: $ORIG_DIR" -ForegroundColor Cyan

# ----- 判断是否含中文 -----
if (HasNonAscii $ORIG_DIR) {
    Write-Host "[构建] 检测到路径包含中文，将使用纯英文临时目录构建" -ForegroundColor Yellow
    $USE_TEMP = $true
} else {
    Write-Host "[构建] 路径为纯英文，将直接在当前目录构建" -ForegroundColor Green
    $USE_TEMP = $false
}

# ----- 根据检测结果分支执行 -----
if ($USE_TEMP) {
    # ========== 临时目录构建模式 ==========
    $RAND = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 6 | ForEach-Object { [char]$_ })
    $TEMP_BUILD_DIR = Join-Path $TEMP_ROOT "pyinstaller_tmp_$RAND"
    Write-Host "[构建] 临时目录: $TEMP_BUILD_DIR" -ForegroundColor Cyan

    # 创建临时目录
    New-Item -ItemType Directory -Path $TEMP_BUILD_DIR -Force | Out-Null

    try {
        # 复制源代码（排除不需要的文件夹）
        Write-Host "[构建] 复制源代码到临时目录..." -ForegroundColor Cyan
        $EXCLUDE_DIRS = @(".venv", "dist", "build", ".git", "__pycache__", "Compressed")
        Get-ChildItem -Path $ORIG_DIR -Exclude $EXCLUDE_DIRS | Copy-Item -Destination $TEMP_BUILD_DIR -Recurse -Force

        if (-not (Test-Path "$TEMP_BUILD_DIR\run.py")) {
            throw "复制失败：未找到 run.py"
        }

        # 创建并激活虚拟环境
        Write-Host "[构建] 在临时目录创建虚拟环境..." -ForegroundColor Cyan
        python -m venv "$TEMP_BUILD_DIR\.venv"
        $venv_python = "$TEMP_BUILD_DIR\.venv\Scripts\python.exe"

        # 安装依赖
        Write-Host "[构建] 安装依赖（镜像: $PIP_INDEX）..." -ForegroundColor Cyan
        & $venv_python -m pip install --upgrade pip -q
        & $venv_python -m pip install -r "$TEMP_BUILD_DIR\requirements.txt" -i $PIP_INDEX
        & $venv_python -m pip install pyinstaller -i $PIP_INDEX
        if ($LASTEXITCODE -ne 0) { throw "依赖安装失败" }

        # 执行打包
        Write-Host "[构建] 正在打包（临时目录）..." -ForegroundColor Cyan
        Push-Location $TEMP_BUILD_DIR
        & $venv_python -m PyInstaller `
            --name mcsm-tools `
            --onefile `
            --distpath ./dist `
            --workpath ./build `
            --add-data "mcsm_tools/fonts;mcsm_tools/fonts" `
            --hidden-import engineio `
            --hidden-import engineio.client `
            --hidden-import prompt_toolkit `
            --hidden-import requests `
            --hidden-import PyQt5 `
            --hidden-import PyQt5.QtCore `
            --hidden-import PyQt5.QtGui `
            --hidden-import PyQt5.QtWidgets `
            run.py
        Pop-Location

        if ($LASTEXITCODE -ne 0) { throw "PyInstaller 打包失败" }

        # 复制 EXE 到原项目
        $sourceExe = "$TEMP_BUILD_DIR\dist\mcsm-tools.exe"
        $targetDir = "$ORIG_DIR\dist"
        if (-not (Test-Path $targetDir)) { New-Item -ItemType Directory -Path $targetDir -Force | Out-Null }
        $targetExe = "$targetDir\mcsm-tools.exe"
        Copy-Item $sourceExe $targetExe -Force
        Write-Host "[构建] EXE 已复制到: $targetExe" -ForegroundColor Green

        # 清理临时目录
        Write-Host "[构建] 清理临时目录..." -ForegroundColor Cyan
        Remove-Item -Recurse -Force $TEMP_BUILD_DIR -ErrorAction SilentlyContinue

    } catch {
        Write-Host "[错误] 构建失败: $_" -ForegroundColor Red
        Write-Host "[提示] 临时目录保留在: $TEMP_BUILD_DIR，请手动检查" -ForegroundColor Yellow
        exit 1
    }

} else {
    # ========== 直接构建模式（当前目录纯英文）==========
    # 检查虚拟环境是否存在
    $VENV_DIR = ".venv"
    if (Test-Path $VENV_DIR) {
        Write-Host "[构建] 使用已有虚拟环境" -ForegroundColor Cyan
        & "$VENV_DIR\Scripts\Activate.ps1"
        $venv_python = "$VENV_DIR\Scripts\python.exe"
    } else {
        Write-Host "[构建] 未找到虚拟环境，正在创建..." -ForegroundColor Cyan
        python -m venv $VENV_DIR
        $venv_python = "$VENV_DIR\Scripts\python.exe"
        Write-Host "[构建] 安装依赖..." -ForegroundColor Cyan
        & $venv_python -m pip install --upgrade pip -q
        & $venv_python -m pip install -r requirements.txt -i $PIP_INDEX
        & $venv_python -m pip install pyinstaller -i $PIP_INDEX
        if ($LASTEXITCODE -ne 0) { throw "依赖安装失败" }
    }

    # 确保 pyinstaller 已安装
    & $venv_python -m pip install pyinstaller -i $PIP_INDEX -q

    # 执行打包
    Write-Host "[构建] 正在打包..." -ForegroundColor Cyan
    & $venv_python -m PyInstaller `
        --name mcsm-tools `
        --onefile `
        --distpath ./dist `
        --workpath ./build `
        --add-data "mcsm_tools/fonts;mcsm_tools/fonts" `
        --hidden-import engineio `
        --hidden-import engineio.client `
        --hidden-import prompt_toolkit `
        --hidden-import requests `
        --hidden-import PyQt5 `
        --hidden-import PyQt5.QtCore `
        --hidden-import PyQt5.QtGui `
        --hidden-import PyQt5.QtWidgets `
        run.py

    if ($LASTEXITCODE -ne 0) { throw "PyInstaller 打包失败" }

    $targetExe = "$ORIG_DIR\dist\mcsm-tools.exe"
    Write-Host "[构建] 构建完成: $targetExe" -ForegroundColor Green
}

Write-Host ""
Write-Host "构建完成，按 Enter 退出" -ForegroundColor Green
Read-Host