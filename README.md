# Infra Toolbox

A small Windows desktop app (Python + Tkinter) that gives you one-click buttons for
infra chores instead of remembering shell commands. Organized into tabs:

- **Infra Control** - Start (1h/3h/no limit), Extend +1h, Stop, Cancel Auto-Stop,
  Status buttons that run `manage_infra.sh` via Git Bash.
- **Database Tunnel** - Start/Stop buttons for the SSH local port-forward to the
  prod DB (equivalent to `ssh -i ec2-pem-key.pem -L 3307:database-3....:3306 ubuntu@15.206.29.16`),
  with a live status indicator and auto-reconnect if the connection drops.
- **Jobs** - lists Windows Scheduled Tasks you created yourself, with Run/Enable/Disable/Delete.
- **Settings** - opens `config.json` so each laptop can use its own paths/hosts.
- Extensible: new buttons/tasks can be added without touching the GUI code.

## Docs

- [docs/HOW_THIS_REPO_WAS_BUILT.md](docs/HOW_THIS_REPO_WAS_BUILT.md) - design decisions, structure, how to extend it
- [docs/RUNNING_THE_APP.md](docs/RUNNING_THE_APP.md) - how to run the app (exe or from source), config.json reference
- [docs/DEPLOY_TO_ANOTHER_LAPTOP.md](docs/DEPLOY_TO_ANOTHER_LAPTOP.md) - build the exe and roll it out to other machines

## Quick start

```bash
cd /d/Workspaces/Mixed/WindowsApp
py -3 main.py          # run from source
./build.sh             # or build dist/InfraToolbox.exe
``` 
