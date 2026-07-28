import re
from pathlib import Path

from setuptools import setup, find_packages

ROOT = Path(__file__).parent

requirements = [
    line.strip()
    for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    if line.strip() and not line.startswith("#")
]

version = re.search(
    r'^__version__ = "([^"]+)"',
    (ROOT / "mcsm_tools" / "__init__.py").read_text(encoding="utf-8"),
    re.MULTILINE,
).group(1)

setup(
    name="mcsm-tools",
    version=version,
    description="MCSManager 服务器管理工具 - 终端控制、文件管理、日志查看",
    packages=find_packages(exclude=("tests", "tests.*")),
    include_package_data=True,
    package_data={"mcsm_tools": ["fonts/*.ttf", "*.ico", "*.png"]},
    install_requires=requirements,
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "mcsm-tools=mcsm_tools.__main__:main",
            "mcsm-terminal=mcsm_tools.terminal_cli:run_terminal",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
    ],
)
