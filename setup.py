from setuptools import setup, find_packages

with open("requirements.txt", encoding="utf-8") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="mcsm-tools",
    version="2.0.0",
    description="MCSManager 服务器管理工具 - 终端控制、文件管理、日志查看",
    packages=find_packages(),
    install_requires=requirements,
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "mcsm-tools=mcsm_tools.__main__:main",
            "mcsm-terminal=mcsm_tools.terminal_cli:run_terminal",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
)
