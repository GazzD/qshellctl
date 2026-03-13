# qshellctl

CLI tool to manage Quickshell shell profiles and diagnostics.

Current status: `F0` bootstrap in progress.

## Requirements

- Python 3.12+
- `uv` installed

## Setup

```bash
uv sync
```

## Run

```bash
uv run qshellctl --help
uv run qshellctl doctor
```

## F0 Health Check

`doctor` should report at least:

- Python version and executable path
- Linux distro detection from `/etc/os-release` when available
- Hyprland session detection (`HYPRLAND_INSTANCE_SIGNATURE`)
- `git` availability in `PATH`

Expected behavior for F0:

- Command is read-only (no system changes)
- Exit code `0` when diagnostics run successfully
- Non-zero only for technical failures
