"""Registry of one-off script/command tasks shown as buttons in the UI.

To add a new capability in the future, just write a function and decorate it
with @register_task below (or in a new module, imported here) - no GUI code
needs to change, the button appears automatically.
"""
from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from typing import Callable, List

from . import config as cfg
from .process_utils import build_env_with_git_tools, stream_process

RDS_RETRY_INTERVAL_SECONDS = 15


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


def _run_resource_command(resource: str, action: str, log: Callable[[str], None]) -> int:
    """Start or stop one AWS resource without affecting the other."""
    conf = cfg.load_config()
    aws = conf.get("aws_exe", "aws")
    region = conf.get("aws_region", "ap-south-1")
    if resource == "db":
        cmd = [aws, "rds", f"{action}-db-instance", "--region", region,
               "--db-instance-identifier", conf.get("rds_instance_id", "database-3")]
    else:
        cmd = [aws, "ec2", f"{action}-instances", "--region", region,
               "--instance-ids", conf.get("ec2_instance_id", "i-0c3d1dd6757159c28")]
    log(f"Running AWS {action} for {resource.upper()}...")
    return stream_process(cmd, on_line=log)


@register_task("Start DB only", "Starts RDS without changing EC2", style="success")
def start_db_only(log: Callable[[str], None]) -> int:
    return _run_resource_command("db", "start", log)


@register_task("Start EC2 only", "Starts EC2 without changing RDS", style="success")
def start_ec2_only(log: Callable[[str], None]) -> int:
    return _run_resource_command("ec2", "start", log)


@register_task("Stop DB only", "Stops RDS without changing EC2", style="danger")
def stop_db_only(log: Callable[[str], None]) -> int:
    return _run_resource_command("db", "stop", log)


@register_task("Stop EC2 only", "Stops EC2 without changing RDS", style="danger")
def stop_ec2_only(log: Callable[[str], None]) -> int:
    return _run_resource_command("ec2", "stop", log)


@register_task("Start RDS (retry)", "Keeps checking and retrying until RDS is available", style="success")
def start_rds_retry(log: Callable[[str], None]) -> int:
    """Keep polling RDS and request a start whenever the instance is stopped."""
    conf = cfg.load_config()
    aws = conf.get("aws_exe", "aws")
    region = conf.get("aws_region", "ap-south-1")
    db_id = conf.get("rds_instance_id", "database-3")
    base_cmd = [aws, "rds", "describe-db-instances", "--region", region,
                "--db-instance-identifier", db_id, "--query",
                "DBInstances[0].DBInstanceStatus", "--output", "text"]
    env = build_env_with_git_tools(conf.get("bash_exe", ""))
    log(f"Retrying RDS start for {db_id}; checking every {RDS_RETRY_INTERVAL_SECONDS}s until available.")

    while True:
        try:
            result = subprocess.run(
                base_cmd, capture_output=True, text=True, env=env,
                creationflags=0x08000000,
            )
        except OSError as exc:
            log(f"[RDS retry] Could not run AWS CLI: {exc}; will retry.")
            time.sleep(RDS_RETRY_INTERVAL_SECONDS)
            continue
        status = result.stdout.strip() if result.returncode == 0 else ""
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            log(f"[RDS retry] Could not read RDS status: {detail or 'AWS CLI failed'}")
        elif status.lower() == "available":
            log(f"[RDS retry] RDS {db_id} is available.")
            return 0
        else:
            log(f"[RDS retry] RDS status: {status or 'unknown'}.")
            if status.lower() == "stopped":
                start_cmd = [aws, "rds", "start-db-instance", "--region", region,
                             "--db-instance-identifier", db_id]
                try:
                    started = subprocess.run(
                        start_cmd, capture_output=True, text=True, env=env,
                        creationflags=0x08000000,
                    )
                except OSError as exc:
                    log(f"[RDS retry] Could not run AWS CLI: {exc}; will retry.")
                    time.sleep(RDS_RETRY_INTERVAL_SECONDS)
                    continue
                if started.returncode == 0:
                    log(f"[RDS retry] Start requested for {db_id}.")
                else:
                    detail = (started.stderr or started.stdout).strip()
                    log(f"[RDS retry] Start request failed; will retry: {detail or 'AWS CLI failed'}")
        time.sleep(RDS_RETRY_INTERVAL_SECONDS)


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


