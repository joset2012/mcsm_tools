import os
import platform
import shutil
import subprocess
import sys


SYSTEM = platform.system()

_FONTS_DIR = os.path.join(os.path.dirname(__file__), "fonts")
MONO_FONT = "JetBrains Mono"

_SEVEN_ZIP_PATH: str | None = None
_SEVEN_ZIP_RESOLVED = False


def seven_zip_path() -> str | None:
    """Path to the 7-Zip binary, resolved once and cached."""
    global _SEVEN_ZIP_PATH, _SEVEN_ZIP_RESOLVED
    if not _SEVEN_ZIP_RESOLVED:
        _SEVEN_ZIP_PATH = _find_7z()
        _SEVEN_ZIP_RESOLVED = True
    return _SEVEN_ZIP_PATH


def _find_7z() -> str | None:
    candidates = []
    if SYSTEM == "Windows":
        candidates = [
            shutil.which("7z.exe"),
            shutil.which("7z"),
        ]
        prog = os.environ.get("ProgramFiles", "C:\\Program Files")
        prog_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
        candidates.append(os.path.join(prog, "7-Zip", "7z.exe"))
        if prog != prog_x86:
            candidates.append(os.path.join(prog_x86, "7-Zip", "7z.exe"))
    else:
        candidates = [
            shutil.which("7z"),
            shutil.which("7za"),
            "/usr/bin/7z",
            "/usr/local/bin/7z",
        ]
    for c in candidates:
        if c and os.path.exists(c):
            return os.path.abspath(c)
    return None


def ensure_font_installed() -> bool:
    if not os.path.exists(_FONTS_DIR):
        return False

    if SYSTEM == "Windows":
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        if not local_appdata:
            return False
        font_dir = os.path.join(local_appdata, "Microsoft", "Windows", "Fonts")
    else:
        font_dir = os.path.expanduser("~/.fonts")

    os.makedirs(font_dir, exist_ok=True)
    copied = 0
    for fn in os.listdir(_FONTS_DIR):
        if fn.endswith(".ttf"):
            src = os.path.join(_FONTS_DIR, fn)
            dst = os.path.join(font_dir, fn)
            if not os.path.exists(dst):
                try:
                    shutil.copy2(src, dst)
                    copied += 1
                except OSError:
                    pass

    if copied and SYSTEM != "Windows" and shutil.which("fc-cache"):
        try:
            subprocess.run(["fc-cache", "-f"], capture_output=True, timeout=10, check=False)
        except (OSError, subprocess.SubprocessError):
            pass

    return True


def run():
    print(f"[mcsm-tools] 系统: {SYSTEM}", file=sys.stderr)
    print(f"[mcsm-tools] Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}", file=sys.stderr)

    path = seven_zip_path()
    if path:
        print(f"[mcsm-tools] 7-Zip: {path}", file=sys.stderr)
    else:
        print("[mcsm-tools] ⚠ 7-Zip 未安装（解压非 .zip 格式和本地压缩功能不可用）", file=sys.stderr)

    try:
        ensure_font_installed()
        print(f"[mcsm-tools] 字体 {MONO_FONT} 已就绪", file=sys.stderr)
    except OSError as e:
        print(f"[mcsm-tools] ⚠ 字体安装异常: {e}", file=sys.stderr)
