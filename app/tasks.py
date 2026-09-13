"""Registry of one-off script/command tasks shown as buttons in the UI.

To add a new capability in the future, just write a function and decorate it
with @register_task below (or in a new module, imported here) - no GUI code
needs to change, the button appears automatically.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List

from . import config as cfg
from .process_utils import stream_process


@dataclass
class Task:
    name: str
    description: str
    run: Callable[[Callable[[str], None]], int]


TASKS: List[Task] = []


def register_task(name: str, description: str = ""):
    def decorator(func: Callable[[Callable[[str], None]], int]):
        TASKS.append(Task(name=name, description=description, run=func))
        return func

    return decorator


@register_task("Run Infra Script", "Runs manage_infra.sh via Git Bash")
def run_infra_script(log: Callable[[str], None]) -> int:
    conf = cfg.load_config()
    cmd = [conf["bash_exe"], conf["infra_script_path"]]
    log(f"Running {conf['infra_script_path']} ...")
    return stream_process(cmd, on_line=log)
