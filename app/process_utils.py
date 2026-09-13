"""Helpers for running external processes and streaming their output line by line."""
from __future__ import annotations

import subprocess
from typing import Callable, List, Optional

# Prevents a console window from flashing up when launching bash.exe/ssh.exe.
CREATE_NO_WINDOW = 0x08000000


def stream_process(cmd: List[str], on_line: Callable[[str], None], cwd: Optional[str] = None) -> int:
    """Run `cmd` to completion, forwarding each output line to `on_line`, and return the exit code."""
    process = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        creationflags=CREATE_NO_WINDOW,
    )
    assert process.stdout is not None
    for line in process.stdout:
        on_line(line.rstrip())
    return process.wait()
