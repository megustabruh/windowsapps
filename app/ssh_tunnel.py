"""Manage a background SSH local port-forward (tunnel) process, e.g. for the prod DB."""
from __future__ import annotations

import subprocess
import threading
from typing import Callable, Optional

CREATE_NO_WINDOW = 0x08000000


class SSHTunnel:
    """Starts/stops a single long-lived `ssh -N -L ...` process."""

    def __init__(self, log: Callable[[str], None]):
        self._log = log
        self._process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()

    def is_running(self) -> bool:
        with self._lock:
            return self._process is not None and self._process.poll() is None

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
            if self._process is not None and self._process.poll() is None:
                self._log("Tunnel already running.")
                return

            cmd = [
                ssh_exe,
                "-i", pem_key_path,
                "-N",  # don't run a remote command, just forward the port
                "-o", "ExitOnForwardFailure=yes",
                "-o", "ServerAliveInterval=30",
                "-o", "StrictHostKeyChecking=accept-new",
                "-L", f"{local_port}:{remote_host}:{remote_port}",
                f"{ssh_user}@{ssh_host}",
            ]
            self._log(f"Starting SSH tunnel: localhost:{local_port} -> {remote_host}:{remote_port}")
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=CREATE_NO_WINDOW,
            )
            threading.Thread(target=self._read_output, args=(self._process,), daemon=True).start()

    def _read_output(self, process: subprocess.Popen) -> None:
        if process.stdout is not None:
            for line in process.stdout:
                self._log(f"[tunnel] {line.rstrip()}")
        code = process.wait()
        self._log(f"[tunnel] SSH process exited (code {code}).")

    def stop(self) -> None:
        with self._lock:
            if self._process is None or self._process.poll() is not None:
                self._log("Tunnel is not running.")
                return
            self._log("Stopping SSH tunnel...")
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
        self._log("Tunnel stopped.")
