@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

cd /d "%~dp0"

if exist ".venv\" (
    call .venv\Scripts\activate
) else (
    python -m venv .venv
    call .venv\Scripts\activate
    pip install -q -r requirements.txt
)

pip install -q pyinstaller

pyinstaller ^
    --name mcsm-tools ^
    --onefile ^
    --distpath ./dist ^
    --workpath ./build ^
    --add-data "mcsm_tools/fonts;mcsm_tools/fonts" ^
    --hidden-import engineio ^
    --hidden-import engineio.client ^
    --hidden-import prompt_toolkit ^
    --hidden-import requests ^
    --hidden-import PyQt5 ^
    --hidden-import PyQt5.QtCore ^
    --hidden-import PyQt5.QtGui ^
    --hidden-import PyQt5.QtWidgets ^
    run.py

echo.
echo 构建完成: dist\mcsm-tools.exe
pause
