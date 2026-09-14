"""Tkinter GUI: tabbed window (Infra Control / Database Tunnel / Jobs / Settings)
plus a shared log panel for infra tasks, the SSH tunnel, and scheduled tasks.
"""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from . import config as cfg
from . import scheduled_tasks
from .ssh_tunnel import SSHTunnel
from .tasks import TASKS, Task

BG = "#f3f4f6"
HEADER_BG = "#111827"
MUTED = "#6b7280"

BUTTON_STYLES = {
    "success": ("Success.TButton", "#2e7d32", "#388e3c"),
    "danger": ("Danger.TButton", "#c62828", "#d32f2f"),
    "neutral": ("Neutral.TButton", "#455a64", "#546e7a"),
    "primary": ("Primary.TButton", "#1565c0", "#1976d2"),
}

JOB_ACTIONS = {
    "run": scheduled_tasks.run_task,
    "enable": scheduled_tasks.enable_task,
    "disable": scheduled_tasks.disable_task,
    "delete": scheduled_tasks.delete_task,
}


class MainWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Infra Toolbox")
        self.root.geometry("880x600")
        self.root.minsize(660, 460)
        self.root.configure(background=BG)

        self._log_queue: "queue.Queue[str]" = queue.Queue()
        self.tunnel = SSHTunnel(log=self._log_queue.put)
        self._jobs_by_row: dict[str, scheduled_tasks.ScheduledTask] = {}

        self._configure_styles()
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(100, self._drain_log_queue)
        self.root.after(500, self._update_tunnel_status)
        self.root.after(200, self._refresh_jobs)

    # -- Styling -------------------------------------------------------------
    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")

        style.configure("TFrame", background=BG)
        style.configure("Header.TFrame", background=HEADER_BG)
        style.configure("Header.TLabel", background=HEADER_BG, foreground="white", font=("Segoe UI", 14, "bold"))
        style.configure("Sub.TLabel", background=HEADER_BG, foreground="#9ca3af", font=("Segoe UI", 9))
        style.configure("Hint.TLabel", background=BG, foreground=MUTED, font=("Segoe UI", 8, "italic"))
        style.configure("Status.TLabel", background=BG, font=("Segoe UI", 9, "bold"))
        style.configure(
            "Section.TLabelframe", background=BG, bordercolor="#d1d5db", relief=tk.GROOVE
        )
        style.configure(
            "Section.TLabelframe.Label", background=BG, foreground="#374151", font=("Segoe UI", 9, "bold")
        )
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", padding=(14, 8), font=("Segoe UI", 9, "bold"))

        for style_name, base_color, active_color in BUTTON_STYLES.values():
            style.configure(
                style_name,
                background=base_color,
                foreground="white",
                font=("Segoe UI", 9, "bold"),
                padding=(10, 6),
                borderwidth=0,
            )
            style.map(style_name, background=[("active", active_color), ("disabled", "#c7c7c7")])

    # -- UI construction ---------------------------------------------------
    def _build_ui(self) -> None:
        header = ttk.Frame(self.root, style="Header.TFrame")
        header.pack(fill=tk.X)
        text_col = ttk.Frame(header, style="Header.TFrame")
        text_col.pack(side=tk.LEFT, padx=16, pady=10)
        ttk.Label(text_col, text="Infra Toolbox", style="Header.TLabel").pack(anchor=tk.W)
        ttk.Label(text_col, text="EC2 + RDS control  \u00b7  SSH DB tunnel  \u00b7  Scheduled jobs", style="Sub.TLabel").pack(
            anchor=tk.W
        )

        body = ttk.Frame(self.root)
        body.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)

        notebook_container = ttk.Frame(body)
        notebook_container.pack(fill=tk.X)
        notebook = ttk.Notebook(notebook_container)
        notebook.pack(fill=tk.BOTH, expand=True)

        infra_tab = ttk.Frame(notebook, padding=8)
        tunnel_tab = ttk.Frame(notebook, padding=8)
        jobs_tab = ttk.Frame(notebook, padding=8)
        settings_tab = ttk.Frame(notebook, padding=8)
        notebook.add(infra_tab, text="Infra Control")
        notebook.add(tunnel_tab, text="Database Tunnel")
        notebook.add(jobs_tab, text="Jobs")
        notebook.add(settings_tab, text="Settings")

        self._build_infra_tab(infra_tab)
        self._build_tunnel_tab(tunnel_tab)
        self._build_jobs_tab(jobs_tab)
        self._build_settings_tab(settings_tab)

        # The Notebook otherwise sizes itself to fit its tallest tab (Jobs' table),
        # leaving a big empty gap on simpler tabs like Infra Control. Pin its height
        # to what the button-row tab actually needs instead, plus the tab-bar chrome.
        self.root.update_idletasks()
        fixed_height = infra_tab.winfo_reqheight() + 34
        notebook_container.configure(height=fixed_height)
        notebook_container.pack_propagate(False)

        self.hint_var = tk.StringVar(value="")
        ttk.Label(body, textvariable=self.hint_var, style="Hint.TLabel").pack(fill=tk.X, pady=(8, 6))

        log_frame = ttk.LabelFrame(body, text="Activity Log", style="Section.TLabelframe")
        log_frame.pack(fill=tk.BOTH, expand=True)
        log_toolbar = ttk.Frame(log_frame)
        log_toolbar.pack(fill=tk.X, padx=6, pady=(6, 0))
        ttk.Button(log_toolbar, text="Clear Logs", style="Neutral.TButton", command=self._clear_logs).pack(
            side=tk.RIGHT
        )
        self.log_widget = scrolledtext.ScrolledText(
            log_frame,
            state="disabled",
            wrap=tk.WORD,
            background="#1e1e1e",
            foreground="#d4d4d4",
            insertbackground="white",
            font=("Consolas", 10),
            borderwidth=0,
            relief=tk.FLAT,
        )
        self.log_widget.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.log_widget.tag_configure("error", foreground="#f87171")
        self.log_widget.tag_configure("tunnel", foreground="#60a5fa")
        self.log_widget.tag_configure("jobs", foreground="#c084fc")
        self.log_widget.tag_configure("normal", foreground="#d4d4d4")

    def _build_infra_tab(self, tab: ttk.Frame) -> None:
        for task in TASKS:
            style_name, _, _ = BUTTON_STYLES.get(task.style, BUTTON_STYLES["primary"])
            btn = ttk.Button(
                tab, text=task.name, style=style_name,
                command=lambda t=task: self._run_task_async(t),
            )
            btn.pack(side=tk.LEFT, anchor=tk.N, padx=6, pady=6)
            btn.bind("<Enter>", lambda _e, d=task.description: self._set_hint(d))
            btn.bind("<Leave>", lambda _e: self._set_hint(""))

    def _build_tunnel_tab(self, tab: ttk.Frame) -> None:
        ttk.Button(tab, text="Start Tunnel", style="Success.TButton", command=self._start_tunnel).pack(
            side=tk.LEFT, anchor=tk.N, padx=6, pady=6
        )
        ttk.Button(tab, text="Stop Tunnel", style="Danger.TButton", command=self._stop_tunnel).pack(
            side=tk.LEFT, anchor=tk.N, padx=6, pady=6
        )
        self.tunnel_status_var = tk.StringVar(value="\u25cf Stopped")
        self.tunnel_status_label = ttk.Label(
            tab, textvariable=self.tunnel_status_var, style="Status.TLabel", foreground=MUTED
        )
        self.tunnel_status_label.pack(side=tk.LEFT, anchor=tk.N, padx=12, pady=6)

    def _build_jobs_tab(self, tab: ttk.Frame) -> None:
        toolbar = ttk.Frame(tab)
        toolbar.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(toolbar, text="Refresh", style="Primary.TButton", command=self._refresh_jobs).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(toolbar, text="Run", style="Success.TButton", command=lambda: self._job_action("run")).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(toolbar, text="Enable", style="Neutral.TButton", command=lambda: self._job_action("enable")).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(toolbar, text="Disable", style="Neutral.TButton", command=lambda: self._job_action("disable")).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(toolbar, text="Delete", style="Danger.TButton", command=lambda: self._job_action("delete")).pack(
            side=tk.LEFT, padx=6
        )

        columns = ("name", "path", "state")
        tree_frame = ttk.Frame(tab)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        self.jobs_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=5)
        for col, label, width in (("name", "Task Name", 260), ("path", "Folder", 220), ("state", "State", 100)):
            self.jobs_tree.heading(col, text=label)
            self.jobs_tree.column(col, width=width, anchor=tk.W)
        tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.jobs_tree.yview)
        self.jobs_tree.configure(yscrollcommand=tree_scroll.set)
        self.jobs_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.LEFT, fill=tk.Y)

        ttk.Label(
            tab, text="Shows scheduled tasks authored by your Windows user account.", style="Hint.TLabel"
        ).pack(anchor=tk.W, pady=(6, 0))

    def _build_settings_tab(self, tab: ttk.Frame) -> None:
        ttk.Label(tab, text=f"Config file: {cfg.config_path()}", style="Hint.TLabel").pack(
            anchor=tk.NW, pady=(0, 10)
        )
        ttk.Button(tab, text="\u2699 Edit Settings", style="Primary.TButton", command=self._edit_settings).pack(
            anchor=tk.NW
        )

    def _set_hint(self, text: str) -> None:
        self.hint_var.set(text)

    def _clear_logs(self) -> None:
        self.log_widget.configure(state="normal")
        self.log_widget.delete("1.0", tk.END)
        self.log_widget.configure(state="disabled")

    # -- Logging -------------------------------------------------------------
    def _drain_log_queue(self) -> None:
        while not self._log_queue.empty():
            message = self._log_queue.get_nowait()
            lower = message.lower()
            if any(k in lower for k in ("error", "failed", "denied", "unexpectedly")):
                tag = "error"
            elif message.startswith("[tunnel]"):
                tag = "tunnel"
            elif message.startswith("[jobs]"):
                tag = "jobs"
            else:
                tag = "normal"
            self.log_widget.configure(state="normal")
            self.log_widget.insert(tk.END, message + "\n", tag)
            self.log_widget.see(tk.END)
            self.log_widget.configure(state="disabled")
        self.root.after(100, self._drain_log_queue)

    # -- Tunnel status indicator --------------------------------------------
    def _update_tunnel_status(self) -> None:
        if self.tunnel.is_running():
            self.tunnel_status_var.set("\u25cf Running")
            self.tunnel_status_label.configure(foreground="#2e7d32")
        else:
            self.tunnel_status_var.set("\u25cf Stopped")
            self.tunnel_status_label.configure(foreground=MUTED)
        self.root.after(500, self._update_tunnel_status)

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

    # -- Jobs tab ------------------------------------------------------------
    def _refresh_jobs(self) -> None:
        def worker() -> None:
            try:
                tasks = scheduled_tasks.list_tasks()
            except Exception as exc:
                self._log_queue.put(f"[jobs] Failed to list scheduled tasks: {exc}")
                return
            self.root.after(0, lambda: self._populate_jobs(tasks))

        threading.Thread(target=worker, daemon=True).start()

    def _populate_jobs(self, tasks: list) -> None:
        self._jobs_by_row.clear()
        self.jobs_tree.delete(*self.jobs_tree.get_children())
        for task in tasks:
            row_id = self.jobs_tree.insert("", tk.END, values=(task.name, task.path, task.state))
            self._jobs_by_row[row_id] = task
        self._log_queue.put(f"[jobs] Loaded {len(tasks)} scheduled task(s) authored by you.")

    def _job_action(self, action: str) -> None:
        selection = self.jobs_tree.selection()
        if not selection:
            messagebox.showinfo("Jobs", "Select a task first.")
            return
        task = self._jobs_by_row.get(selection[0])
        if task is None:
            return
        if action == "delete" and not messagebox.askyesno(
            "Delete task", f"Permanently delete scheduled task '{task.name}'?"
        ):
            return

        def worker() -> None:
            JOB_ACTIONS[action](task, self._log_queue.put)
            self.root.after(0, self._refresh_jobs)

        threading.Thread(target=worker, daemon=True).start()

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


