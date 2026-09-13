# How This Repo Was Built

Notes on the design decisions behind Infra Toolbox, for future reference when
extending it.

## Requirements that shaped the design

1. Trigger `manage_infra.sh` (a bash script) from a Windows app.
2. On-demand start/stop of an SSH local port-forward to the prod DB:
   `ssh -i ec2-pem-key.pem -L 3307:database-3....:3306 ubuntu@15.206.29.16`.
3. Deployable to multiple laptops without each one needing a dev environment.
4. Easy to bolt on new functionality later without reworking the whole app.
5. Ends up as a single `.exe`.

## Tech choices

- **Python + Tkinter** for the GUI. Tkinter ships with Python (no extra GUI
  dependency), and Python's `subprocess` module makes shelling out to
  `bash.exe`/`ssh.exe` and streaming their output straightforward. Chosen over
  Java (would need `jpackage`/Launch4j and more boilerplate for process
  streaming) and Electron (much larger exe, needs Node tooling).
- **Git for Windows' `bash.exe` / `ssh.exe`** to run the `.sh` script and the
  SSH tunnel, since Git for Windows is a common, lightweight prerequisite
  (rather than requiring WSL on every laptop).
- **PyInstaller** (`--onefile --windowed`) to produce a single portable `.exe`
  that doesn't need Python installed on the target machine.

## Structure

```
main.py               entry point (also the PyInstaller target)
app/
  config.py           loads/creates config.json (lives next to the exe)
  process_utils.py     stream_process() - run a command, forward output line by line
  ssh_tunnel.py        SSHTunnel class - start()/stop()/is_running() for the DB tunnel
  tasks.py             @register_task registry - one-off script/command buttons
  gui.py               Tkinter window: buttons (from TASKS) + tunnel controls + log panel
config.example.json    checked-in template; config.json itself is git-ignored (per-laptop)
build.sh               PyInstaller build script for Git Bash -> dist/InfraToolbox.exe + config.json
build.ps1              same build script for PowerShell
```

## Key design patterns

- **Config lives outside the exe.** `app/config.py` resolves the app directory
  via `sys.frozen`/`sys.executable` so `config.json` sits next to the `.exe`
  after building, not baked into it. This is what lets each laptop have its
  own pem key path, script path, and DB host without rebuilding.
- **Task registry for extensibility.** `app/tasks.py` exposes a
  `@register_task("Label", "description")` decorator. `gui.py` just iterates
  `TASKS` and creates one button per entry - adding a new one-off command
  never requires touching the GUI code.
- **Stateful things get their own class.** The SSH tunnel isn't a one-shot
  task (it needs Start *and* Stop, and a running process handle), so it's a
  small `SSHTunnel` class instead of a `TASKS` entry. Follow this pattern for
  any future long-running/background feature.
- **Background threads + a queue for logging.** All external processes run on
  background threads so the UI never freezes; they push log lines into a
  `queue.Queue`, and the Tkinter main loop drains it every 100ms
  (`root.after`) to append to the log panel safely from the UI thread.

## How to extend this later

See [RUNNING_THE_APP.md](RUNNING_THE_APP.md) for day-to-day use and
[DEPLOY_TO_ANOTHER_LAPTOP.md](DEPLOY_TO_ANOTHER_LAPTOP.md) for rollout. For
adding features: write a function in `app/tasks.py` and decorate it with
`@register_task(...)` for a simple new button, or add a new module similar to
`ssh_tunnel.py` for anything that needs start/stop or persistent state.
