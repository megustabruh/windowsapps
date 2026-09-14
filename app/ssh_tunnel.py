"""Manage a background SSH local port-forward (tunnel) process, e.g. for the prod DB."""
from __future__ import annotations

import subprocess
import threading
from typing import Callable, Optional

from .process_utils import build_env_with_git_tools

CREATE_NO_WINDOW = 0x08000000
RECONNECT_DELAY_SECONDS = 5


class SSHTunnel:
    """Runs a supervised `ssh -N -L ...` process, auto-reconnecting if it drops."""

    def __init__(self, log: Callable[[str], None]):
        self._log = log
        self._process: Optional[subprocess.Popen] = None
        self._supervisor_thread: Optional[threading.Thread] = None
        self._params: Optional[dict] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def is_running(self) -> bool:
        with self._lock:
            return self._supervisor_thread is not None and self._supervisor_thread.is_alive()

    def start(
        self,
        ssh_exe: str,
        pem_key_path: str,
        local_port: int,
        remote_host: str,
        remote_port: int,
        ssh_user: str,
        ssh_host: str,
    ) -> None:
        with self._lock:
            if self._supervisor_thread is not None and self._supervisor_thread.is_alive():
                self._log("Tunnel already running.")
                return

            self._params = {
                "ssh_exe": ssh_exe,
                "pem_key_path": pem_key_path,
                "local_port": local_port,
                "remote_host": remote_host,
                "remote_port": remote_port,
                "ssh_user": ssh_user,
                "ssh_host": ssh_host,
            }
            self._stop_event.clear()
            self._supervisor_thread = threading.Thread(target=self._supervise, daemon=True)
            self._supervisor_thread.start()

    def _build_cmd(self) -> list[str]:
        p = self._params
        assert p is not None
        return [
            p["ssh_exe"],
            "-i", p["pem_key_path"],
            "-N",  # don't run a remote command, just forward the port
            "-o", "ExitOnForwardFailure=yes",
            "-o", "ServerAliveInterval=30",
            "-o", "ServerAliveCountMax=3",
            "-o", "StrictHostKeyChecking=accept-new",
            "-L", f"{p['local_port']}:{p['remote_host']}:{p['remote_port']}",
            f"{p['ssh_user']}@{p['ssh_host']}",
        ]

    def _supervise(self) -> None:
        p = self._params
        assert p is not None
        self._log(f"Starting SSH tunnel: localhost:{p['local_port']} -> {p['remote_host']}:{p['remote_port']}")
        while not self._stop_event.is_set():
            try:
                process = subprocess.Popen(
                    self._build_cmd(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    env=build_env_with_git_tools(p["ssh_exe"]),
                    creationflags=CREATE_NO_WINDOW,
                )
            except OSError as exc:
                self._log(f"[tunnel] Failed to start ssh: {exc}")
                if self._stop_event.wait(RECONNECT_DELAY_SECONDS):
                    break
                continue

            with self._lock:
                self._process = process

            if process.stdout is not None:
                for line in process.stdout:
                    self._log(f"[tunnel] {line.rstrip()}")
            code = process.wait()

            with self._lock:
                self._process = None

            if self._stop_event.is_set():
                break

            self._log(
                f"[tunnel] SSH process exited unexpectedly (code {code}). "
                f"Reconnecting in {RECONNECT_DELAY_SECONDS}s..."
            )
            if self._stop_event.wait(RECONNECT_DELAY_SECONDS):
                break

        self._log("Tunnel stopped.")

    def stop(self) -> None:
        with self._lock:
            if self._supervisor_thread is None or not self._supervisor_thread.is_alive():
                self._log("Tunnel is not running.")
                return
            self._log("Stopping SSH tunnel...")
            self._stop_event.set()
            process = self._process

        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

        supervisor = self._supervisor_thread
        if supervisor is not None:
            supervisor.join(timeout=10)

