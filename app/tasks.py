"""Registry of one-off script/command tasks shown as buttons in the UI.

To add a new capability in the future, just write a function and decorate it
with @register_task below (or in a new module, imported here) - no GUI code
needs to change, the button appears automatically.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List

from . import config as cfg
from .process_utils import build_env_with_git_tools, stream_process


@dataclass
class Task:
    name: str
    description: str
    run: Callable[[Callable[[str], None]], int]
    style: str = "primary"  # "primary" | "success" | "danger" | "neutral" - used for button color


TASKS: List[Task] = []


def register_task(name: str, description: str = "", style: str = "primary"):
    def decorator(func: Callable[[Callable[[str], None]], int]):
        TASKS.append(Task(name=name, description=description, run=func, style=style))
        return func

    return decorator


def _run_infra_command(args: List[str], log: Callable[[str], None]) -> int:
    """Runs `manage_infra.sh <args>` via Git Bash. See manage_infra.sh's own
    usage/help text for the full set of supported actions and duration formats."""
    conf = cfg.load_config()
    cmd = [conf["bash_exe"], conf["infra_script_path"], *args]
    log(f"Running: manage_infra.sh {' '.join(args)} ...")
    return stream_process(cmd, on_line=log, env=build_env_with_git_tools(conf["bash_exe"]))


@register_task("Start (1h)", "Starts RDS + EC2, auto-stops after 1 hour", style="success")
def start_infra_1h(log: Callable[[str], None]) -> int:
    return _run_infra_command(["start", "1h"], log)


@register_task("Start (3h)", "Starts RDS + EC2, auto-stops after 3 hours", style="success")
def start_infra_3h(log: Callable[[str], None]) -> int:
    return _run_infra_command(["start", "3h"], log)


@register_task("Start (no limit)", "Starts RDS + EC2, stays up until stopped manually", style="success")
def start_infra_indefinite(log: Callable[[str], None]) -> int:
    return _run_infra_command(["start"], log)


@register_task("Extend +1h", "Adds 1 hour to the current auto-stop timer (or starts one if none is pending)", style="success")
def extend_auto_stop_1h(log: Callable[[str], None]) -> int:
    return _run_infra_command(["extend", "1h"], log)


@register_task("Stop", "Stops EC2 and RDS now", style="danger")
def stop_infra(log: Callable[[str], None]) -> int:
    return _run_infra_command(["stop"], log)


@register_task("Cancel Auto-Stop", "Keeps infra running - cancels any pending auto-stop timer", style="neutral")
def cancel_auto_stop(log: Callable[[str], None]) -> int:
    return _run_infra_command(["cancel-stop"], log)


@register_task("Status", "Shows current EC2/RDS state and any pending auto-stop", style="neutral")
def infra_status(log: Callable[[str], None]) -> int:
    return _run_infra_command(["status"], log)


