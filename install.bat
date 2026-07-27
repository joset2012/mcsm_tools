@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set "VENV_DIR=.venv"

call :info "mcsm-tools 依赖安装脚本"
echo.

:: ── 检查 Python ──
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    call :err "Python 未安装，请先安装 Python >= 3.10"
    call :err "  下载地址: https://www.python.org/downloads/"
    echo   安装时请勾选 "Add Python to PATH"
    pause
    exit /b 1
)

for /f "tokens=2 delims=." %%a in ('python -c "import sys; print(sys.version)"') do set "PY_MAJOR=%%a"
for /f "tokens=1 delims=." %%a in ('python -c "import sys; print(sys.version_info.minor)"') do set "PY_MINOR=%%a"

python -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)"
if %ERRORLEVEL% neq 0 (
    call :err "需要 Python >= 3.10，当前版本不满足"
    pause
    exit /b 1
)

python --version
call :ok "Python 版本符合要求"

:: ── 虚拟环境 ──
if not exist "%VENV_DIR%" (
    call :info "创建虚拟环境 %VENV_DIR% ..."
    python -m venv "%VENV_DIR%"
    call :ok "虚拟环境已创建"
)
call :ok "虚拟环境已就绪"

:: ── pip 依赖 ──
call :info "安装 Python 依赖..."
"%VENV_DIR%\Scripts\python" -m pip install --upgrade pip -q
"%VENV_DIR%\Scripts\python" -m pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    call :err "依赖安装失败"
    pause
    exit /b 1
)
call :ok "Python 依赖安装完成"

:: ── 7-Zip ──
where 7z.exe >nul 2>&1
if %ERRORLEVEL% equ 0 (
    call :ok "7-Zip 已安装"
) else (
    call :warn "7-Zip 未安装"
    call :warn "解压非 .zip 格式和使用本地压缩功能需要 7-Zip"
    echo.
    echo   下载地址: https://7-zip.org/download.html
    echo.
)

:: ── 完成 ──
echo.
call :ok "安装完成！"
echo.
echo   启动方式：
echo     1) 激活虚拟环境后运行:
echo        %VENV_DIR%\Scripts\activate
echo        python -m mcsm_tools
echo.
echo     2) 直接运行（自动使用系统 Python）:
echo        python -m mcsm_tools
echo.
pause
goto :eof

:: ── 辅助函数 ──
:info
echo [mcsm-tools] %*
goto :eof

:ok
echo [mcsm-tools] %*
goto :eof

:warn
echo [mcsm-tools] %*
goto :eof

:err
echo [mcsm-tools] %*
goto :eof
