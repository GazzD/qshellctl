# qshellctl

`qshellctl` is a small CLI for managing **Quickshell setups** and **Hyprland profile switching** on Arch Linux.

The project is aimed at people who like trying different shell environments such as **Caelestia** or **Illogical Impulse**, but want a single command-line tool to install them, check dependencies, update them, and switch the active Hyprland profile.

## What it does

- Lists supported shells from a central registry
- Checks and optionally installs shell dependencies
- Clones shell source repositories locally
- Bootstraps local Quickshell and Hyprland configuration where needed
- Updates shells from upstream Git repositories using a shell-specific flow
- Switches the active Hyprland profile by editing `$profile = ...` in `hyprland.conf`
- Persists the active profile in `~/.local/state/qshellctl/state.json`
- Provides a simple `doctor` command for environment and bootstrap checks

## Scope

`qshellctl` is intentionally opinionated:

- **Platform:** Arch Linux
- **Compositor:** Hyprland
- **Shell stack:** Quickshell
- **Package manager:** `uv`

It is not a generic Linux desktop manager and it does not try to hide the underlying shell projects. It is a thin orchestration layer around them.

## Supported shells

| Shell | ID | Status | Notes |
| --- | --- | --- | --- |
| Default profile | `default` | Available | No Quickshell shell; represents a plain Hyprland fallback profile. |
| Caelestia | `caelestia` | Implemented | Installed from its own Git repo and built with CMake/Ninja. |
| Illogical Impulse | `ii` | Implemented | Uses an upstream dotfiles repo as the source tree and deploys its Quickshell config into `~/.config/quickshell/ii`. |

## Installation

`qshellctl` currently targets local development and source installs.

### Requirements

- Python **3.12+**
- [`uv`](https://github.com/astral-sh/uv)
- `git`
- Arch Linux with Hyprland

### Install from source

```sh
git clone https://github.com/GazzD/qshellctl.git
cd qshellctl
uv sync
```

Run it with:

```sh
uv run qshellctl --help
```

## Quick start

Check whether the current machine looks compatible:

```sh
uv run qshellctl doctor
```

Initialize the profile system on first use:

```sh
uv run qshellctl init
```

`qshellctl shells install <name>` and `qshellctl shells switch <name>` expect this
bootstrap step to be completed first.

You can use `uv run qshellctl init --yes` to skip the confirmation prompt.

List available shells:

```sh
uv run qshellctl shells list
```

Inspect dependencies for a shell:

```sh
uv run qshellctl shells deps caelestia
```

Install a shell:

```sh
uv run qshellctl shells install caelestia
```

Switch to it:

```sh
uv run qshellctl shells switch caelestia
```

Update it later:

```sh
uv run qshellctl shells update caelestia
```

## Command overview

### Root commands

| Command | Description |
| --- | --- |
| `qshellctl init` | Initialize the Hyprland profile system for first use. |
| `qshellctl doctor` | Runs basic environment checks. |
| `qshellctl shells ...` | Shell management commands. |

### `qshellctl shells`

| Command | Description |
| --- | --- |
| `shells list` | List all registered shells. |
| `shells deps <name>` | Show declared dependencies for a shell. |
| `shells deps <name> --install` | Attempt to install missing dependencies. |
| `shells install <name>` | Install a shell and bootstrap its local configuration. |
| `shells update <name>` | Update a shell from upstream and apply its shell-specific update flow. |
| `shells status <name>` | Show whether the shell is installed and, when applicable, its Git revision. |
| `shells uninstall <name>` | Remove an installed shell and its managed files. |
| `shells switch <name>` | Switch the active Hyprland profile and launch the target shell. |

## How profile switching works

Before switching shells for the first time, run:

```sh
uv run qshellctl init
```

This bootstraps the profile system by conservatively copying the current
`~/.config/hypr/` tree into `~/.config/hypr/default/` without overwriting existing files,
backing up the root `hyprland.conf`, and rewriting the root config as a profile selector.

`qshellctl shells switch <name>` assumes your root `hyprland.conf` selects a profile through a variable like this:

```ini
$profile = caelestia
source = $profile/hyprland.conf
```

When switching, `qshellctl`:

1. loads the persisted state from `~/.local/state/qshellctl/state.json`
2. validates that `~/.config/hypr/<name>/hyprland.conf` exists
3. updates `$profile = <name>` in the root Hyprland config
4. runs `hyprctl reload`
5. starts the destination shell and stores the new active profile

This keeps Hyprland profile selection simple and lets each shell own its own profile subtree under `~/.config/hypr/<profile>/`.

## Update behavior

The tool distinguishes between **shell code** and **Hyprland profile configuration**.

### Shell updates

`qshellctl` updates the upstream source repo first, then applies a shell-specific deployment step.

- **Caelestia**
  - pulls the upstream shell repo
  - rebuilds and reinstalls the compiled shell components
  - does **not** automatically re-sync `~/.config/hypr/caelestia` on update

- **Illogical Impulse (`ii`)**
  - updates the upstream repo in `~/.cache/dots-hyprland`
  - syncs `dots/.config/quickshell/ii` into `~/.config/quickshell/ii`
  - does **not** automatically re-sync `~/.config/hypr/ii` on update

- **Git-based source updates**
  - local changes in the source repo are temporarily stashed during the update flow
  - the stash is only popped when that update actually created one

### Hyprland profile updates

Hyprland profile directories under `~/.config/hypr/<profile>/` should be treated as **user-owned configuration**.

The project direction is:

- bootstrap a profile on first install
- avoid overwriting the user's live Hyprland config on regular updates
- keep any destructive re-sync as an explicit action rather than a default behavior

This is especially important for dotfile-based projects where upstream config and local edits naturally diverge over time.

## Architecture

The project is intentionally small:

```text
cli/     Typer entrypoints and commands
models/  Abstract shell classes, dependency model, exceptions
shells/  Concrete shell implementations and registry
utils/   Dependency checks, bootstrap helpers, process helpers, state handling, Rich helpers
```

Main entrypoint:

- `cli/main.py`

Shell command group:

- `cli/shells.py`

Registry:

- `shells/__init__.py`

## Development

Install dependencies:

```sh
uv sync
```

Run the CLI:

```sh
uv run qshellctl
```

Lint:

```sh
uv run ruff check .
uv run ruff format .
```

Run tests:

```sh
uv run pytest
```

Build a distributable:

```sh
uv build
```

## Current limitations

This project is still evolving. A few important caveats:

- Hyprland profile syncing is being simplified to avoid overwriting user configuration on updates
- There is currently no test suite in the repository

## Why this project exists

Projects like Caelestia and Illogical Impulse are great, but each comes with its own installation style, dependency story, and update workflow. `qshellctl` exists to provide a **single control surface** for:

- dependency checks
- local source installs
- profile-aware shell switching
- safer, more explicit updates

without hiding the fact that the real logic still lives in the upstream shell projects.
