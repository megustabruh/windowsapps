"""Tkinter GUI: a log panel plus buttons for infra tasks and the SSH tunnel."""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext

from . import config as cfg
from .ssh_tunnel import SSHTunnel
from .tasks import TASKS, Task


class MainWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Infra Toolbox")
        self.root.geometry("760x480")
        self.root.minsize(560, 360)

        self._log_queue: "queue.Queue[str]" = queue.Queue()
        self.tunnel = SSHTunnel(log=self._log_queue.put)

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(100, self._drain_log_queue)

    # -- UI construction ---------------------------------------------------
    def _build_ui(self) -> None:
        task_bar = tk.Frame(self.root)
        task_bar.pack(fill=tk.X, padx=8, pady=(8, 4))

        for task in TASKS:
            tk.Button(
                task_bar,
                text=task.name,
                command=lambda t=task: self._run_task_async(t),
            ).pack(side=tk.LEFT, padx=4)

        tunnel_bar = tk.Frame(self.root)
        tunnel_bar.pack(fill=tk.X, padx=8, pady=(0, 8))

        tk.Button(tunnel_bar, text="Start DB Tunnel", command=self._start_tunnel).pack(side=tk.LEFT, padx=4)
        tk.Button(tunnel_bar, text="Stop DB Tunnel", command=self._stop_tunnel).pack(side=tk.LEFT, padx=4)
        tk.Button(tunnel_bar, text="Edit Settings", command=self._edit_settings).pack(side=tk.LEFT, padx=4)

        self.log_widget = scrolledtext.ScrolledText(self.root, state="disabled", wrap=tk.WORD)
        self.log_widget.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

    # -- Logging -------------------------------------------------------------
    def _drain_log_queue(self) -> None:
        while not self._log_queue.empty():
            message = self._log_queue.get_nowait()
            self.log_widget.configure(state="normal")
            self.log_widget.insert(tk.END, message + "\n")
            self.log_widget.see(tk.END)
            self.log_widget.configure(state="disabled")
        self.root.after(100, self._drain_log_queue)

    # -- Task buttons ----------------------------------------------------
    def _run_task_async(self, task: Task) -> None:
        def worker() -> None:
            try:
                code = task.run(self._log_queue.put)
                self._log_queue.put(f"'{task.name}' finished (exit code {code}).")
            except Exception as exc:  # surfaced to the log panel instead of crashing the UI
                self._log_queue.put(f"'{task.name}' failed: {exc}")

        threading.Thread(target=worker, daemon=True).start()

    # -- Tunnel buttons --------------------------------------------------
    def _start_tunnel(self) -> None:
        conf = cfg.load_config()
        t = conf["ssh_tunnel"]
        threading.Thread(
            target=lambda: self.tunnel.start(
                ssh_exe=conf["ssh_exe"],
                pem_key_path=t["pem_key_path"],
                local_port=t["local_port"],
                remote_host=t["remote_host"],
                remote_port=t["remote_port"],
                ssh_user=t["ssh_user"],
                ssh_host=t["ssh_host"],
            ),
            daemon=True,
        ).start()

    def _stop_tunnel(self) -> None:
        threading.Thread(target=self.tunnel.stop, daemon=True).start()

    def _edit_settings(self) -> None:
        try:
            cfg.open_config_in_editor()
        except Exception as exc:
            messagebox.showerror("Settings", f"Could not open config.json: {exc}")

    def _on_close(self) -> None:
        if self.tunnel.is_running():
            self.tunnel.stop()
        self.root.destroy()


def launch() -> None:
    root = tk.Tk()
    MainWindow(root)
    root.mainloop()
