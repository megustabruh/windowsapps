# Deploying to a Different Laptop

The app is a single portable `.exe` plus one editable `config.json` - no
installer, no admin rights, no Python required on the target machine.

## 1. Build the exe (once, on any dev machine)

```bash
cd /d/Workspaces/Mixed/WindowsApp
./build.sh
```

Produces `dist/InfraToolbox.exe` and `dist/config.json`. (A PowerShell
equivalent, `build.ps1`, is also included if you prefer that shell.)

## 2. Copy both files to the new laptop

Copy the whole `dist\` folder (or just `InfraToolbox.exe` + `config.json`
together, they must sit in the same folder) via a shared drive, USB stick, or
an internal release/artifact location. Do **not** commit `config.json` to git
or share it publicly - it will contain that laptop's real pem key path and DB
host details.

## 3. Install the one prerequisite

[Git for Windows](https://git-scm.com/download/win) must be installed on the
new laptop, since the app shells out to its `bash.exe` (to run
`manage_infra.sh`) and `ssh.exe` (for the DB tunnel). Default install paths
already match `config.json`'s defaults:

- `C:\Program Files\Git\bin\bash.exe`
- `C:\Program Files\Git\usr\bin\ssh.exe`

If Git was installed somewhere else, update those two paths in `config.json`.

## 4. Put the laptop-specific files in place

- Copy the `.pem` key file to the new laptop and update
  `ssh_tunnel.pem_key_path` in `config.json` to point at it.
- Copy `manage_infra.sh` to the new laptop and update `infra_script_path`
  accordingly.

## 5. Run it

Double-click `InfraToolbox.exe`. No further setup needed.

## Rolling out updates later

When you add new tasks/features (see
[HOW_THIS_REPO_WAS_BUILT.md](HOW_THIS_REPO_WAS_BUILT.md)), rebuild with
`./build.sh` and just replace `InfraToolbox.exe` on each laptop - leave the
existing `config.json` on each machine untouched since it holds that laptop's
settings.
