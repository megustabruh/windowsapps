"""Windows Scheduled Task listing/control (via PowerShell), for the Jobs tab.

"Created by you" isn't a real Task Scheduler attribute, so this uses a couple
of heuristics: a task counts as yours if its action runs a script/exe outside
Windows/Program Files (i.e. a custom automation, not an OS/vendor task), or
if its Author field matches your Windows username. Built-in \\Microsoft\\
tasks are always excluded.
"""
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from typing import Callable, List

CREATE_NO_WINDOW = 0x08000000

# Full path instead of relying on PATH - some launch contexts (e.g. the
# packaged .exe run outside a dev shell) don't have System32 on PATH.
POWERSHELL_EXE = os.path.join(
    os.environ.get("SystemRoot", r"C:\Windows"), "System32", "WindowsPowerShell", "v1.0", "powershell.exe"
)


@dataclass
class ScheduledTask:
    name: str
    path: str
    state: str


def _run_powershell(script: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [POWERSHELL_EXE, "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
        creationflags=CREATE_NO_WINDOW,
    )


def list_tasks() -> List[ScheduledTask]:
    username = os.environ.get("USERNAME", "").replace("'", "''")
    script = (
        "Get-ScheduledTask | Where-Object { "
        "$_.TaskPath -notlike '\\Microsoft\\*' -and ("
        "  ( ($_.Actions | Select-Object -First 1).Execute -and "
        "    ($_.Actions | Select-Object -First 1).Execute -notmatch '(?i)^\"?(%windir%|C:\\\\Windows|C:\\\\Program Files)'"
        "  ) -or "
        f"  $_.Author -like '*{username}*'"
        ") } | "
        "Select-Object TaskName, TaskPath, @{Name='State';Expression={$_.State.ToString()}} | "
        "ConvertTo-Json -Compress"
    )
    result = _run_powershell(script)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Failed to query scheduled tasks.")
    output = result.stdout.strip()
    if not output:
        return []
    data = json.loads(output)
    if isinstance(data, dict):
        data = [data]
    return [ScheduledTask(name=t["TaskName"], path=t["TaskPath"], state=t["State"]) for t in data]




def _task_action(cmdlet: str, task: ScheduledTask, log: Callable[[str], None], extra: str = "") -> None:
    script = f"{cmdlet} -TaskName '{task.name}' -TaskPath '{task.path}' {extra}".strip()
    result = _run_powershell(script)
    if result.returncode != 0:
        log(f"[jobs] {cmdlet} failed for '{task.name}': {result.stderr.strip()}")
    else:
        log(f"[jobs] {cmdlet} succeeded for '{task.name}'.")


def run_task(task: ScheduledTask, log: Callable[[str], None]) -> None:
    _task_action("Start-ScheduledTask", task, log)


def enable_task(task: ScheduledTask, log: Callable[[str], None]) -> None:
    _task_action("Enable-ScheduledTask", task, log)


def disable_task(task: ScheduledTask, log: Callable[[str], None]) -> None:
    _task_action("Disable-ScheduledTask", task, log)


def delete_task(task: ScheduledTask, log: Callable[[str], None]) -> None:
    _task_action("Unregister-ScheduledTask", task, log, extra="-Confirm:$false")
