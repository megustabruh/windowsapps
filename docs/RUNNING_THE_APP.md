# Running the App

## Generating InfraToolbox.exe

The `.exe` isn't checked into git - it's built locally from source with
[PyInstaller](https://pyinstaller.org/), which bundles the Python interpreter
and this app's code into one standalone file.

Requirements: Python 3.10+ on the machine doing the build (use the `py`
launcher if `python`/`python3` aren't on PATH - that's the case on this
machine, where only `py -3` resolves to a real interpreter).

```bash
cd /d/Workspaces/Mixed/WindowsApp
./build.sh
```

What `build.sh` does:

1. `py -3 -m pip install --upgrade pyinstaller` - installs/updates PyInstaller.
2. `py -3 -m PyInstaller --noconfirm --onefile --windowed --name InfraToolbox main.py` -
   builds a single-file, console-less exe from `main.py` (which imports the
   `app` package, so everything under `app/` gets bundled in automatically).
3. Copies `config.example.json` to `dist/config.json` as a starter config.

Output lands in `dist/InfraToolbox.exe` + `dist/config.json`. PyInstaller also
creates a `build/` folder (intermediate files) and an `InfraToolbox.spec` file
(the generated build spec) - both are safe to ignore/delete and are already
git-ignored. Re-run `./build.sh` any time you change code under `app/` or
`main.py` to get an updated exe.

> A PowerShell equivalent (`build.ps1`) is also included if you prefer that shell.

## Option A - Run the built .exe (no Python needed)

1. Make sure [Git for Windows](https://git-scm.com/download/win) is installed
   (provides `bash.exe`/`ssh.exe`) and your `.pem` key + `manage_infra.sh` are
   somewhere on disk.
2. Double-click `InfraToolbox.exe` (in `dist\` after building, see above).
3. On first launch a `config.json` is created next to the exe if one doesn't
   already exist. Click **Edit Settings** in the app (or open `config.json`
   directly) and fill in your real paths/hosts:


   ```jsonc
   {
     "bash_exe": "C:\\Program Files\\Git\\bin\\bash.exe",
     "ssh_exe": "C:\\Program Files\\Git\\usr\\bin\\ssh.exe",
     "infra_script_path": "C:\\Users\\<you>\\Downloads\\manage_infra.sh",
     "ssh_tunnel": {
       "pem_key_path": "C:\\path\\to\\ec2-pem-key.pem",
       "local_port": 3307,
       "remote_host": "database-3.ct0wi8eqo8od.ap-south-1.rds.amazonaws.com",
       "remote_port": 3306,
       "ssh_user": "ubuntu",
       "ssh_host": "15.206.29.16"
     }
   }
   ```
4. Save the file. No restart needed - settings are re-read each time you click
   a button.

## Using the app

The window is split into four tabs, with a shared Activity Log always visible
at the bottom (all tabs stream their output there).

### Infra Control tab (EC2 + RDS)

Each button runs `manage_infra.sh` (see its own `--help`/usage comments for
the full command reference) via Git Bash:

- **Start (1h)** / **Start (3h)** - `manage_infra.sh start 1h` / `start 3h`:
  starts RDS then EC2, and auto-stops both after that duration. A warning is
  logged 5 minutes before the auto-stop fires (immediately if the duration is
  under 5 minutes).
- **Start (no limit)** - `manage_infra.sh start`: starts RDS then EC2, stays
  up until you stop it manually.
- **Extend +1h** - `manage_infra.sh extend 1h`: adds 1 hour to a pending
  auto-stop (or starts a fresh 1h timer if none is pending). Handy when you
  get the "about to auto-stop" warning and just need more time.
- **Stop** - `manage_infra.sh stop`: stops EC2 and RDS now.
- **Cancel Auto-Stop** - `manage_infra.sh cancel-stop`: if you got the
  "about to auto-stop" warning and want to keep going indefinitely, this
  cancels the pending timer entirely without touching EC2/RDS. Re-running
  any **Start** button also replaces a pending timer with a fresh one.
- **Status** - `manage_infra.sh status`: prints current EC2/RDS state plus
  how long until any pending auto-stop.

### Database Tunnel tab

- **Start Tunnel** - opens the SSH port-forward
  (`localhost:3307 -> database-3....:3306`) in the background and
  auto-reconnects if the connection drops. Leave it running for as long as
  you need DB access (e.g. via a MySQL client pointed at `localhost:3307`).
  The status dot next to the buttons turns green (Running) or gray (Stopped).
- **Stop Tunnel** - closes the SSH connection and disables auto-reconnect.
- Closing the window automatically stops the tunnel if it's still running.

### Jobs tab

Lists Windows Scheduled Tasks authored by your Windows user account (via
`Get-ScheduledTask` in PowerShell) - i.e. tasks you created yourself, not the
built-in Windows/vendor ones. Select a row, then:

- **Refresh** - reloads the list (also runs automatically on startup).
- **Run** - triggers the task immediately (`Start-ScheduledTask`).
- **Enable** / **Disable** - toggles whether the task's own schedule/triggers
  fire (`Enable-ScheduledTask` / `Disable-ScheduledTask`).
- **Delete** - permanently removes the task (`Unregister-ScheduledTask`,
  asks for confirmation first since this can't be undone).

### Settings tab

Shows the path to `config.json` and an **Edit Settings** button that opens it
in your default editor.



## Option B - Run from source (for development)

Requires Python 3.10+ (use the `py` launcher on Windows if `python`/`python3`
aren't on PATH):

```powershell
cd D:\Workspaces\Mixed\WindowsApp
py -3 main.py
```

This behaves identically to the `.exe`, just launched via the interpreter -
useful while developing new tasks in `app/tasks.py`.
