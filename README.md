# mcsm-tools

MCSManager 服务器管理工具 —— 终端控制、文件管理、日志查看

## 系统要求

| 组件 | 版本要求 |
|------|----------|
| Python | >= 3.10 |
| 7-Zip | 可选（非 .zip 解压和本地压缩时需要） |

## 安装

### 自动安装

**Linux/macOS：**

```bash
chmod +x install.sh
./install.sh
```

**Windows：**

双击 `install.bat`，或在终端中运行：

```cmd
install.bat
```

安装脚本会自动创建虚拟环境、安装 Python 依赖，并检查 7-Zip。

### 手动安装

```bash
# 创建虚拟环境（推荐）
python3 -m venv .venv
source .venv/bin/activate    # Linux/macOS
# .venv\Scripts\activate      # Windows

# 安装依赖
pip install -r requirements.txt
```

### 7-Zip 安装（可选）

| 系统 | 安装命令 |
|------|----------|
| Ubuntu/Debian | `sudo apt install p7zip-full` |
| Fedora | `sudo dnf install p7zip p7zip-plugins` |
| Arch Linux | `sudo pacman -S p7zip` |
| macOS | `brew install p7zip` |
| Windows | 从 [7-zip.org](https://7-zip.org/download.html) 下载安装 |

## 快速启动

```bash
# 推荐：使用启动脚本（自动处理虚拟环境和 fcitx5）
./mcsm-tools.sh

# 或手动激活虚拟环境后运行
source .venv/bin/activate    # Linux/macOS
# .venv\Scripts\activate      # Windows
python -m mcsm_tools
```

### CLI 终端模式

```bash
./mcsm-tools.sh --terminal
# 或
python -m mcsm_tools --terminal
```

## 编译可执行文件

### Linux

```bash
chmod +x build.sh
./build.sh
```

输出：`dist/mcsm-tools`（单文件，约 15 MB）

### Windows

在 Windows 上双击 `build.bat`，或在终端运行：

```cmd
build.bat
```

输出：`dist\mcsm-tools.exe`（单文件）

编译后可直接分发，无需 Python 环境。

## 配置

首次启动后进入 **设置** 标签页，填写以下信息：

### 面板设置
- **面板地址**：MCSManager 面板 URL（默认 `https://mcsm.rainyun.com`）

### 登录设置
两种登录方式任选其一：

| 方式 | 填写内容 | 点击按钮 |
|------|----------|----------|
| 密码登录 | 用户名 + 密码 | "密码登录" |
| API Key 登录 | API Key | "API Key 登录" |

### 实例设置
- **Daemon ID**：节点 UUID
- **Instance UUID**：实例 UUID
- **实例名称**：显示用名称（可选）

也可以通过 **自动发现实例** 按钮自动填充。

### 功能设置
| 选项 | 说明 |
|------|------|
| 启动时自动连接终端 | 打开应用后自动连接终端 WebSocket |
| 终端记忆 | 保存上一会话的终端输出，下次启动时恢复 |
| 退出时显示确认对话框 | 关闭应用时弹出确认窗口 |

## 功能

### 终端控制
- WebSocket 实时连接，支持 ANSI 颜色解析
- 发送 Minecraft 服务器指令
- `!clear` 清屏、`!help` 查看内置命令
- 自动执行 `list` 获取在线玩家
- 双缓冲持久化保存终端输出

### 文件管理
- 双栏文件管理器（本地 / 远程）
- 上传、下载、编辑、删除、移动
- 右键菜单：剪切 / 粘贴 / 解压 / 压缩
- 多选文件压缩（zip 服务端 / 其他格式本地）
- 递归下载目录
- 实时进度条

### 日志查看
- 实时加载远程日志文件
- 支持 `.log`、`.gz` 格式
- 自动换行显示
- 行号显示
- 文件列表按类型过滤

### 界面
- Nord 暗色主题
- JetBrains Mono 等宽字体
- 实例状态栏（在线人数）

## 中文输入（Linux fcitx5）

如果 tkinter 输入框无法使用 fcitx5 输入中文：

1. **安装 fcitx5 tk 前端**

   | 发行版 | 命令 |
   |--------|------|
   | Debian/Ubuntu | `sudo apt install fcitx5-frontend-tk` |
   | Arch Linux | `sudo pacman -S fcitx5-tk` |
   | Fedora | `sudo dnf install fcitx5-tk` |

2. **使用启动脚本**（自动设置环境变量）

   ```bash
   ./mcsm-tools.sh
   ```

   该脚本会自动设置 `XMODIFIERS=@im=fcitx` 等环境变量。

3. **手动设置环境变量**

   ```bash
   export XMODIFIERS=@im=fcitx
   export GTK_IM_MODULE=fcitx
   export QT_IM_MODULE=fcitx
   python -m mcsm_tools
   ```

应用启动时也会自动检测 fcitx5 环境并给出提示。

## 目录结构

```
mcsm-tools/
├── install.sh            # Linux 安装脚本
├── install.bat           # Windows 安装脚本
├── build.sh              # Linux 编译脚本
├── build.bat             # Windows 编译脚本
├── run.py                # PyInstaller 入口
├── mcsm-tools.sh         # Linux 启动脚本（虚拟环境 + fcitx5）
├── requirements.txt      # Python 依赖
├── setup.py              # 包配置
├── mcsm_config.ini       # 配置文件（自动生成）
├── mcsm_tools/
│   ├── __init__.py       # 包标识 + 版本号
│   ├── __main__.py       # 模块入口
│   ├── gui.py            # 主窗口 GUI
│   ├── api.py            # MCSManager REST API 封装
│   ├── terminal.py       # WebSocket 终端
│   ├── terminal_cli.py   # CLI 终端模式
│   ├── file_manager.py   # 文件管理器
│   ├── log_viewer.py     # 日志查看器
│   ├── config.py         # 配置读写
│   ├── auth.py           # 凭证管理
│   ├── font_helper.py    # 字体安装
│   ├── system_check.py   # 系统环境检查（含 fcitx5 检测）
│   ├── theme.py          # Nord 主题配色
│   ├── generate_icon.py  # 图标生成（开发用）
│   ├── icon.ico          # Windows 图标
│   ├── icon.png          # Linux 图标
│   └── fonts/            # JetBrains Mono 字体文件
├── dist/                 # 编译输出目录
│   ├── mcsm-tools        # Linux 可执行文件
│   └── mcsm-tools.exe    # Windows 可执行文件
└── Compressed/           # 本地压缩输出目录（自动创建）
```
