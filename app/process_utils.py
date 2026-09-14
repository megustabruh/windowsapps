"""Helpers for running external processes and streaming their output line by line."""
from __future__ import annotations

import os
import subprocess
from typing import Callable, Dict, List, Optional

# Prevents a console window from flashing up when launching bash.exe/ssh.exe.
CREATE_NO_WINDOW = 0x08000000


def stream_process(
    cmd: List[str],
    on_line: Callable[[str], None],
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
) -> int:
    """Run `cmd` to completion, forwarding each output line to `on_line`, and return the exit code."""
    process = subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        creationflags=CREATE_NO_WINDOW,
    )
    assert process.stdout is not None
    for line in process.stdout:
        on_line(line.rstrip())
    return process.wait()


def _find_git_root(exe_path: str) -> Optional[str]:
    """Walks up from `exe_path` looking for a Git for Windows install root
    (a folder with sibling `bin` and `usr` directories)."""
    current = os.path.dirname(exe_path)
    for _ in range(4):
        if os.path.isdir(os.path.join(current, "bin")) and os.path.isdir(os.path.join(current, "usr")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent
    return None


def build_env_with_git_tools(exe_path: str) -> Dict[str, str]:
    """Returns a copy of the current environment with Git for Windows' own bin
    dirs prepended to PATH, so tools it spawns (e.g. `date`, `sleep` from a
    bash script) resolve even if PATH doesn't already include them - this can
    happen when the app is launched as a packaged .exe outside a dev shell."""
    env = os.environ.copy()
    git_root = _find_git_root(exe_path)
    if git_root:
        extra_dirs = [
            os.path.join(git_root, "bin"),
            os.path.join(git_root, "usr", "bin"),
            os.path.join(git_root, "mingw64", "bin"),
        ]
        env["PATH"] = os.pathsep.join(extra_dirs) + os.pathsep + env.get("PATH", "")
    return env

