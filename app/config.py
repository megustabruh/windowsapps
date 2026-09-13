"""Load and persist the app's editable config.json (lives next to the exe)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

DEFAULTS = {
    "bash_exe": r"C:\Program Files\Git\bin\bash.exe",
    "ssh_exe": r"C:\Program Files\Git\usr\bin\ssh.exe",
    "infra_script_path": str(Path(os.path.expanduser("~")) / "Downloads" / "manage_infra.sh"),
    "ssh_tunnel": {
        "pem_key_path": r"C:\path\to\ec2-pem-key.pem",
        "local_port": 3307,
        "remote_host": "database-3.ct0wi8eqo8od.ap-south-1.rds.amazonaws.com",
        "remote_port": 3306,
        "ssh_user": "ubuntu",
        "ssh_host": "15.206.29.16",
    },
}


def app_dir() -> Path:
    """Directory the exe (or this script, when run from source) lives in."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def config_path() -> Path:
    return app_dir() / "config.json"


def load_config() -> dict:
    """Read config.json, creating it from defaults on first run."""
    path = config_path()
    if not path.exists():
        path.write_text(json.dumps(DEFAULTS, indent=2), encoding="utf-8")
    return json.loads(path.read_text(encoding="utf-8"))


def open_config_in_editor() -> None:
    os.startfile(str(config_path()))  # opens with the user's default .json editor
