"""Registry of one-off script/command tasks shown as buttons in the UI.

To add a new capability in the future, just write a function and decorate it
with @register_task below (or in a new module, imported here) - no GUI code
needs to change, the button appears automatically.
"""
from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
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


def upload_frontend_to_s3(log: Callable[[str], None]) -> int:
    """Sync the configured frontend build directory to its S3 bucket."""
    conf = cfg.load_config()
    aws = conf.get("aws_exe", "aws")
    region = conf.get("aws_region", "ap-south-1")
    source = Path(conf.get(
        "frontend_dist_path",
        r"D:\Workspaces\Mixed\Houstyle\builder-io-react-frontend\dist\spa",
    ))
    bucket = conf.get("frontend_s3_bucket", "personal-react-app")
    if not source.is_dir():
        log(f"[s3] Frontend build folder was not found: {source}")
        return 1

    cmd = [aws, "s3", "sync", str(source), f"s3://{bucket}", "--region", region]
    log(f"[s3] Uploading frontend files from {source} to s3://{bucket} ({region})...")
    code = stream_process(cmd, on_line=lambda line: log(f"[s3] {line}"))
    if code == 0:
        log(f"[s3] Upload finished successfully: s3://{bucket}")
    else:
        log(f"[s3] Upload failed with exit code {code}.")
    return code


def deploy_backend_to_ec2(log: Callable[[str], None]) -> int:
    """Pull the backend's main branch and apply Alembic migrations on EC2."""
    conf = cfg.load_config()
    tunnel = conf.get("ssh_tunnel", {})
    ssh = conf.get("ssh_exe", "ssh")
    pem = tunnel.get("pem_key_path", "")
    ssh_user = tunnel.get("ssh_user", "ubuntu")
    ssh_host = tunnel.get("ssh_host", "")
    if not pem or not ssh_host:
        log("[ec2] SSH key path and host must be configured in config.json.")
        return 1

    remote_commands = (
        "cd ~/fastapi-lambda-app && "
        "git pull origin main && "
        "source venv/bin/activate && "
        "alembic upgrade heads"
    )
    cmd = [
        ssh, "-i", pem,
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=accept-new",
        f"{ssh_user}@{ssh_host}", remote_commands,
    ]
    log(f"[ec2] Deploying backend on {ssh_user}@{ssh_host}...")
    code = stream_process(
        cmd, on_line=lambda line: log(f"[ec2] {line}"),
        env=build_env_with_git_tools(ssh),
    )
    if code == 0:
        log("[ec2] Backend deployment and database migrations completed successfully.")
    else:
        log(f"[ec2] Backend deployment failed with exit code {code}.")
    return code


def deploy_both(log: Callable[[str], None]) -> int:
    """Attempt both production deploys and report each result independently."""
    log("[deploy] Starting both production deployments.")
    results = []
    for name, tag, deploy in (
        ("S3 frontend", "s3", upload_frontend_to_s3),
        ("EC2 backend", "ec2", deploy_backend_to_ec2),
    ):
        try:
            code = deploy(log)
        except Exception as exc:
            log(f"[{tag}] {name} raised an error: {exc}")
            code = 1
        results.append((name, code))
        outcome = "SUCCESS" if code == 0 else f"FAILED (exit code {code})"
        log(f"[deploy] {name}: {outcome}")

    failures = [name for name, code in results if code != 0]
    if failures:
        log(f"[deploy] DEPLOY BOTH FAILED. Failed: {', '.join(failures)}.")
        return 1
    log("[deploy] DEPLOY BOTH SUCCEEDED. S3 frontend and EC2 backend are deployed.")
    return 0


