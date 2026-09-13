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

## Using the buttons

- **Run Infra Script** - runs `manage_infra.sh` via Git Bash; output streams
  live into the log panel at the bottom of the window.
- **Start DB Tunnel** - opens the SSH port-forward
  (`localhost:3307 -> database-3....:3306`) in the background. Leave it
  running for as long as you need DB access (e.g. via a MySQL client pointed
  at `localhost:3307`).
- **Stop DB Tunnel** - closes that SSH connection.
- **Edit Settings** - opens `config.json` in your default editor.
- Closing the window automatically stops the tunnel if it's still running.

## Option B - Run from source (for development)

Requires Python 3.10+ (use the `py` launcher on Windows if `python`/`python3`
aren't on PATH):

```powershell
cd D:\Workspaces\Mixed\WindowsApp
py -3 main.py
```

This behaves identically to the `.exe`, just launched via the interpreter -
useful while developing new tasks in `app/tasks.py`.
