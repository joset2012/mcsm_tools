import sys

# Kept 3.9-compatible: the rest of the package uses `X | None` annotations that
# blow up on older interpreters, so the guard must run before anything else.
if sys.version_info < (3, 10):  # noqa: UP036
    sys.exit(f"[mcsm-tools] Python >= 3.10 是必需的，当前版本: {sys.version_info[0]}.{sys.version_info[1]}")

__version__ = "2.0.0"
__app_name__ = "mcsm-tools"
