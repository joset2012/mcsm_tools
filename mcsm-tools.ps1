# mcsm-tools.ps1
# 用法：.\mcsm-tools.ps1 [--terminal] [--gui]

$VENV_DIR = ".venv"
$SCRIPT_DIR = $PSScriptRoot

if (Test-Path $VENV_DIR) {
    # 激活虚拟环境
    & "$VENV_DIR\Scripts\Activate.ps1"

    # 构建 Qt 插件路径（使用字符串拼接，避免 Join-Path 三个参数问题）
    $qt_plugin_path = "$SCRIPT_DIR\$VENV_DIR\Lib\site-packages\PyQt5\Qt5\plugins"

    if (Test-Path $qt_plugin_path) {
        $env:QT_QPA_PLATFORM_PLUGIN_PATH = $qt_plugin_path
        Write-Host "[mcsm-tools] 设置 Qt 插件路径: $qt_plugin_path" -ForegroundColor Cyan
    } else {
        Write-Host "[mcsm-tools] 警告: 未找到 Qt 插件路径" -ForegroundColor Yellow
    }

    # 运行主程序，传递所有参数
    python -m mcsm_tools @args
} else {
    # 如果没有虚拟环境，直接用系统 Python
    python -m mcsm_tools @args
}