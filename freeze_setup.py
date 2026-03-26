"""
Build Windows MSI via cx_Freeze:
  python freeze_setup.py bdist_msi
Output: dist/*.msi and build/exe.*/
"""

from __future__ import annotations

import sys
from pathlib import Path

from cx_Freeze import Executable, setup

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "iperf3_gui.py"

# Fixed for in-place MSI upgrades (do not change between releases you want to upgrade).
MSI_UPGRADE_CODE = "{8F7E6D5C-4B3A-4918-A726-354453627180}"

build_exe_options = {
    "packages": ["tkinter"],
    "include_msvcr": True,
    "include_files": [],
}

bdist_msi_options = {
    "upgrade_code": MSI_UPGRADE_CODE,
    "add_to_path": False,
    "initial_target_dir": r"[ProgramFilesFolder]\iperf3-gui",
}

executables = [
    Executable(
        SCRIPT,
        base="Win32GUI" if sys.platform == "win32" else None,
        target_name="iperf3-gui.exe",
        shortcut_name="iperf3 GUI",
        shortcut_dir="ProgramMenuFolder",
    )
]

setup(
    name="iperf3-gui",
    version="1.1.2",
    description="iperf3 GUI — guided and manual iperf3 for Windows",
    author="iperf3-gui",
    options={
        "build_exe": build_exe_options,
        "bdist_msi": bdist_msi_options,
    },
    executables=executables,
)
