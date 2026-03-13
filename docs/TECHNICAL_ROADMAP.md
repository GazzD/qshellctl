# qshellctl - Technical Roadmap (Mentoring Mode)

## 1. Context and Goal

`qshellctl` will be a CLI tool to manage Quickshell shells and dotfiles in a modular, reproducible way.

Primary target for v0.1:

- OS: Arch Linux
- WM/Session: Hyprland
- Shell source: Git repositories

Main value proposition:

- Switch Quickshell shells as easily as switching a wallpaper.
- Avoid conflicts between dotfiles/services from different shells.
- Keep a clean and reproducible local environment.

## 2. Development Mode (How We Will Work)

You will write the code. I will act as:

- Tech lead: architecture, sequencing, design decisions.
- Python mentor: idioms, patterns, readability, tests, error handling.

Rules for this mode:

- Small vertical slices (one feature at a time).
- Each slice ends with runnable validation before moving on.
- Prefer simple Python over "clever" Python.
- Refactor only when pain appears, not before.

Definition of Done for every step:

- Feature works from CLI.
- Edge cases handled with clear errors.
- Minimal tests added.
- README section updated (or a changelog note).

## 3. High-Level Architecture

Use a lightweight layered architecture:

- `cli/`: command definitions and argument parsing.
- `services/`: use cases (application logic orchestration).
- `core/`: domain rules and pure business logic.
- `infra/`: adapters to OS, git, filesystem, systemd.
- `config/`: settings and path resolution.
- `models/`: DTOs and domain data structures.
- `utils/`: shared helpers (small, focused).

Golden rule:

- `cli/` should not know OS details.
- `core/` should not know Typer, subprocess, or concrete IO.

## 4. Feature Roadmap (Incremental)

### F0 - Project Bootstrap (Foundation)

Objective:

- Have a runnable CLI with one health command and clean package structure.

Deliverables:

- `pyproject.toml` with entrypoint (`qshellctl`).
- Minimal `cli/main.py` (Typer app).
- `qshellctl doctor` command.

Validation:

- `uv run qshellctl --help`
- `uv run qshellctl doctor`

F0 acceptance criteria for `doctor`:

- Command is visible in CLI help (`qshellctl --help`).
- Command runs without crashing on a normal machine.
- Command is read-only (no file writes, no system changes).
- Command prints, at minimum:
  - Python version.
  - Detected OS id (from `/etc/os-release` when available).
  - Hyprland session detection (`HYPRLAND_INSTANCE_SIGNATURE`).
  - `git` availability in `PATH` (recommended in F0).
- Output format is stable and human-readable (line-based key/value is enough).
- Exit codes:
  - `0` when command executed correctly, even if host is not fully supported.
  - Non-zero only for technical execution failures (unexpected exception, command runtime failure).

F0 is considered complete when:

- `uv run qshellctl --help` lists the command.
- `uv run qshellctl doctor` prints the diagnostics above.
- README includes a short "how to run" section.

Python learning focus:

- Packaging basics, modules, imports, Typer command signatures.

---

### F1 - Local State Management

Objective:

- Persist and load qshellctl state safely.

Deliverables:

- State file under XDG (`~/.local/state/qshellctl/state.json`).
- Data model for installed shells + active shell.
- `qshellctl shell status` command.

Validation:

- Run status on clean state.
- Verify state file creation and reload behavior.

Python learning focus:

- `dataclasses`, typing, JSON serialization, file paths with `pathlib`.

---

### F2 - Install Shell from Git

Objective:

- Install/update a shell from Git repo and register it in state.

Deliverables:

- `qshellctl shell install <name> <repo-url> [--branch main]`
- `qshellctl shell list`
- Basic adapter in `infra/` for git operations.

Validation:

- Install a test repo.
- Re-run install to validate update path.
- List and verify metadata (name, path, revision).

Python learning focus:

- `subprocess.run`, error handling, command wrappers, return types.

---

### F3 - Activation Plan (Dry-Run First)

Objective:

- Build deterministic activation plan before touching system state.

Deliverables:

- `qshellctl shell activate <name> --dry-run`
- Internal "plan steps" model (precheck, dotfiles, services, env, verify).
- `qshellctl shell switch <name> --dry-run`

Validation:

- Dry-run output is deterministic and readable.
- Non-installed shell returns actionable error.

Python learning focus:

- Separation of pure functions (`core`) from side effects (`infra`).

---

### F4 - Real Activation (Apply + Persist)

Objective:

- Execute a first real activation flow and mark active shell.

Deliverables:

- `activate` without dry-run updates active shell state.
- `deactivate` clears active shell.
- `switch` transitions from one shell to another.

Validation:

- Activate -> status -> switch -> status -> deactivate -> status.
- State remains consistent after each command.

Python learning focus:

- Transaction-like thinking and basic rollback strategy.

---

### F5 - Dotfiles Management (Stow-Style)

Objective:

- Apply shell dotfiles safely and detect conflicts.

Deliverables:

- Dotfiles profile convention per shell.
- Symlink strategy similar to GNU Stow.
- Conflict reporting before apply.

Validation:

- Clean apply on empty target.
- Conflict scenario detected and reported.

Python learning focus:

- Filesystem traversal, symlink APIs, conflict detection algorithms.

---

### F6 - Service Orchestration (systemd --user)

Objective:

- Avoid duplicated/conflicting services when switching shells.

Deliverables:

- Start/stop/restart selected user units per profile.
- Minimal policy (whitelist per shell profile).

Validation:

- Simulate shell switch with service set A -> set B.
- Ensure no duplicate running units from previous shell.

Python learning focus:

- Process execution, command output parsing, resilient retries.

---

### F7 - UX and Reliability

Objective:

- Make CLI production-friendly.

Deliverables:

- Consistent error model and exit codes.
- `--verbose`, `--json`, and improved help messages.
- Better diagnostics in `doctor`.

Validation:

- Script-friendly output mode works.
- Errors are understandable and actionable.

Python learning focus:

- Custom exceptions, structured output, logging strategy.

---

### F8 - Test Suite and Quality Gate

Objective:

- Build confidence and prevent regressions.

Deliverables:

- Unit tests (`core/` and selected `services/`).
- Integration tests for git/filesystem adapters.
- Basic CLI tests for major flows.

Validation:

- Test command runs green.
- At least one failing-case test per critical command.

Python learning focus:

- `pytest`, fixtures, mocking IO boundaries.

## 5. Recommended Implementation Order (Now)

Start with:

1. F0 - bootstrap CLI and project config.
2. F1 - state model + `shell status`.
3. F2 - `shell install` + `shell list`.

Do NOT start with dotfiles/services yet.
Reason: first we need a stable lifecycle (install -> state -> activate plan).

## 6. Technical Conventions

- Python version: choose one stable version for dev (example: 3.12 or 3.13).
- Formatting/linting: Ruff.
- Naming:
  - modules/functions: `snake_case`
  - classes: `PascalCase`
  - constants: `UPPER_SNAKE_CASE`
- Keep functions small; prefer explicit return types.
- Use `pathlib` over string paths.
- Surface domain errors with clear messages.

## 7. First Working Session (Concrete Task)

Next task for you:

- Implement F0 completely.

Checklist:

- Create `pyproject.toml` with Typer dependency and script entrypoint.
- Create `cli/main.py` with app and `doctor` command.
- Ensure command runs with `uv run qshellctl --help`.
- Add a short README with run instructions.

When you finish F0, ask for review and we will do:

- Code review (Python style + architecture fit).
- Gaps and improvements.
- F1 plan with exact file-by-file guidance.

## 8. Mentoring Workflow for Next Iterations

For each feature we will use this loop:

1. You implement.
2. You run a small validation checklist.
3. I review code and explain improvements.
4. We patch only what is necessary.
5. Move to next feature.

This keeps progress real while maximizing Python learning.
