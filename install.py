import sys
import os
import subprocess
import platform
from pathlib import Path

MIN_PYTHON = (3, 8)
PROJECT_ROOT = Path(__file__).parent.resolve()
VENV_DIR = PROJECT_ROOT / ".venv"
REQUIREMENTS = PROJECT_ROOT / "requirements.txt"
APP_NAME = "GEE-UI"
ICON_ICO = PROJECT_ROOT / "assets" / "favicon.ico"
ICON_PNG = PROJECT_ROOT / "assets" / "favicon.png"


def check_python_version():
    if sys.version_info < MIN_PYTHON:
        print(f"ERROR: Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ required. Found {sys.version}")
        sys.exit(1)


def ensure_venv():
    if not VENV_DIR.exists():
        print("Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)
        print("  Done.")
    else:
        print("Virtual environment already exists.")


def get_venv_python():
    if platform.system() == "Windows":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def install_dependencies():
    if not REQUIREMENTS.exists():
        print("WARNING: requirements.txt not found, skipping dependency install.")
        return
    print("Syncing dependencies... (might take a while)")
    venv_python = get_venv_python()
    subprocess.run(
        [str(venv_python), "-m", "pip", "install", "--upgrade", "pip", "--quiet"],
        check=True,
    )
    subprocess.run(
        [str(venv_python), "-m", "pip", "install", "-r", str(REQUIREMENTS), "--quiet"],
        check=True,
    )
    print("  Done.")


def get_desktop() -> Path:
    if platform.system() == "Windows":
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "[Environment]::GetFolderPath('Desktop')"],
            capture_output=True, text=True, check=True,
        )
        return Path(result.stdout.strip())
    return Path.home() / "Desktop"


def ask_create_shortcut() -> bool:
    """Ask user via GUI popup (falls back to terminal). Returns True if user says yes."""
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        result = messagebox.askyesno(
            "GEE-UI Setup",
            "Create a desktop shortcut for GEE-UI?",
        )
        root.destroy()
        return result
    except Exception:
        answer = input("Create a desktop shortcut? [Y/n] ").strip().lower()
        return answer in ("", "y", "yes")


def _do_create_shortcut(shortcut_path: Path) -> bool:
    """Return True if shortcut should be created (missing + user consents)."""
    if shortcut_path.exists():
        print("  Shortcut already exists, skipping.")
        return False
    if not sys.stdin.isatty():
        print("  Non-interactive mode, skipping shortcut creation.")
        return False
    return ask_create_shortcut()


def create_shortcut_windows():
    desktop = get_desktop()
    shortcut_path = desktop / f"{APP_NAME}.lnk"

    if not _do_create_shortcut(shortcut_path):
        return

    target = PROJECT_ROOT / "run.bat"
    icon = str(ICON_ICO) if ICON_ICO.exists() else ""

    ps_script = f"""
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('{shortcut_path}')
$Shortcut.TargetPath = 'cmd.exe'
$Shortcut.Arguments = '/k "{target}"'
$Shortcut.WorkingDirectory = '{PROJECT_ROOT}'
$Shortcut.WindowStyle = 7
"""
    if icon:
        ps_script += f"$Shortcut.IconLocation = '{icon}'\n"
    ps_script += "$Shortcut.Save()"

    subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], check=True)
    print(f"  Desktop shortcut created: {shortcut_path}")


def create_shortcut_mac():
    desktop = get_desktop()
    shortcut_path = desktop / f"{APP_NAME}.command"

    if not _do_create_shortcut(shortcut_path):
        return

    venv_python = get_venv_python()
    script_content = f"""#!/bin/bash
cd "{PROJECT_ROOT}"
"{venv_python}" run.py
"""
    shortcut_path.write_text(script_content)
    shortcut_path.chmod(0o755)
    print(f"  Desktop launcher created: {shortcut_path}")
    print("  Note: double-click the .command file to launch GEE-UI.")


def create_shortcut_linux():
    desktop = get_desktop()
    shortcut_path = desktop / f"{APP_NAME}.desktop"

    if not _do_create_shortcut(shortcut_path):
        return

    venv_python = get_venv_python()
    icon_path = str(ICON_PNG) if ICON_PNG.exists() else ""
    desktop_entry = f"""[Desktop Entry]
Version=1.0
Type=Application
Name={APP_NAME}
Exec=bash -c 'cd "{PROJECT_ROOT}" && "{venv_python}" run.py'
Icon={icon_path}
Terminal=false
StartupNotify=false
"""
    shortcut_path.write_text(desktop_entry)
    shortcut_path.chmod(0o755)
    print(f"  Desktop shortcut created: {shortcut_path}")


def create_shortcut():
    print("Creating desktop shortcut...")
    system = platform.system()
    if system == "Windows":
        create_shortcut_windows()
    elif system == "Darwin":
        create_shortcut_mac()
    elif system == "Linux":
        create_shortcut_linux()
    else:
        print(f"  Unsupported OS '{system}', skipping shortcut creation.")


def main():
    from_runbat = "--from-runbat" in sys.argv

    print(f"=== GEE-UI Installer ===")
    print(f"Project root: {PROJECT_ROOT}\n")

    check_python_version()
    ensure_venv()
    install_dependencies()
    create_shortcut()

    print(f"\nInstallation complete.")
    if not from_runbat:
        print(f"Run the app: double-click the desktop shortcut, or run  run.bat  (Windows) / python run.py  (any OS with venv active).")


if __name__ == "__main__":
    main()
