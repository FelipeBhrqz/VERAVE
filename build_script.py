"""PyInstaller build script for Electoral Auditor."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


def build() -> None:
    root = Path(__file__).resolve().parent
    icon_path = root / "assets" / "icon.ico"

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name",
        "ElectoralAuditor",
        str(root / "main.py"),
    ]

    if icon_path.exists():
        command.extend(["--icon", str(icon_path)])

    subprocess.check_call(command)


if __name__ == "__main__":
    build()
