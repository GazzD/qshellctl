import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import typer
from rich.table import Table

import utils.rich_helper as rich

shells_app = typer.Typer(help="Manage Quickshell shell installations.")

CAELESTIA_REPO = "https://github.com/caelestia-dots/shell.git"
QUICKSHELL_CONFIG_DIR = Path.home() / ".config" / "quickshell"
CAELESTIA_INSTALL_DIR = QUICKSHELL_CONFIG_DIR / "caelestia"


# ---------------------------------------------------------------------------
# Dependency model
# ---------------------------------------------------------------------------


@dataclass
class Dep:
    label: str
    checker: Callable[[], bool]
    pacman_pkg: Optional[str] = None
    aur_pkg: Optional[str] = None

    def is_installed(self) -> bool:
        try:
            return self.checker()
        except Exception:
            return False

    @property
    def pkg(self) -> str:
        return self.aur_pkg or self.pacman_pkg or self.label

    @property
    def is_aur(self) -> bool:
        return self.aur_pkg is not None


def _which(binary: str) -> Callable[[], bool]:
    return lambda: shutil.which(binary) is not None


def _pkgconfig(module: str) -> Callable[[], bool]:
    return lambda: (
        subprocess.run(
            ["pkg-config", "--modversion", module], capture_output=True
        ).returncode
        == 0
    )


def _pacman_q(pkg: str) -> Callable[[], bool]:
    return lambda: (
        subprocess.run(["pacman", "-Q", pkg], capture_output=True).returncode == 0
    )


def _font(pattern: str) -> Callable[[], bool]:
    def check() -> bool:
        result = subprocess.run(["fc-list"], capture_output=True, text=True)
        return pattern.lower() in result.stdout.lower()

    return check


# Build-time dependencies (needed to compile the C++ plugin)
CAELESTIA_BUILD_DEPS: list[Dep] = [
    Dep("git", _which("git"), pacman_pkg="git"),
    Dep("cmake", _which("cmake"), pacman_pkg="cmake"),
    Dep("ninja", _which("ninja"), pacman_pkg="ninja"),
]

# Runtime dependencies
CAELESTIA_RUNTIME_DEPS: list[Dep] = [
    Dep("quickshell", _which("qs"), aur_pkg="quickshell-git"),
    Dep("caelestia-cli", _which("caelestia"), aur_pkg="caelestia-cli"),
    Dep("ddcutil", _which("ddcutil"), pacman_pkg="ddcutil"),
    Dep("brightnessctl", _which("brightnessctl"), pacman_pkg="brightnessctl"),
    Dep("app2unit", _which("app2unit"), aur_pkg="app2unit"),
    Dep("libcava", _pkgconfig("libcava"), aur_pkg="libcava"),
    Dep("networkmanager", _which("nmcli"), pacman_pkg="networkmanager"),
    Dep("lm-sensors", _which("sensors"), pacman_pkg="lm_sensors"),
    Dep("fish", _which("fish"), pacman_pkg="fish"),
    Dep("aubio", _pkgconfig("aubio"), pacman_pkg="aubio"),
    Dep("pipewire", _pkgconfig("libpipewire-0.3"), pacman_pkg="pipewire"),
    Dep("qt6-declarative", _pacman_q("qt6-declarative"), pacman_pkg="qt6-declarative"),
    Dep("qt6-base", _pacman_q("qt6-base"), pacman_pkg="qt6-base"),
    Dep("swappy", _which("swappy"), pacman_pkg="swappy"),
    Dep("libqalculate", _pkgconfig("libqalculate"), pacman_pkg="libqalculate"),
    Dep(
        "material-symbols",
        _font("Material Symbols"),
        aur_pkg="ttf-material-symbols-variable-git",
    ),
    Dep(
        "caskaydia-cove-nerd",
        _font("CaskaydiaCove"),
        pacman_pkg="ttf-caskaydia-cove-nerd",
    ),
]

ALL_DEPS = CAELESTIA_BUILD_DEPS + CAELESTIA_RUNTIME_DEPS


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _detect_aur_helper() -> Optional[str]:
    """Return the first available AUR helper found in PATH."""
    for helper in ["yay", "paru", "trizen", "pikaur"]:
        if shutil.which(helper):
            return helper
    return None


def _get_missing(deps: list[Dep]) -> list[Dep]:
    return [dep for dep in deps if not dep.is_installed()]


def _print_deps_table(deps: list[Dep]) -> None:
    table = Table(title="Caelestia Dependencies", title_style="bold magenta")
    table.add_column("Dependency", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Package", style="dim")
    table.add_column("Source", justify="center")

    for dep in deps:
        installed = dep.is_installed()
        status = "[green]✔[/green]" if installed else "[red]✗[/red]"
        source = "[yellow]AUR[/yellow]" if dep.is_aur else "[blue]pacman[/blue]"
        table.add_row(dep.label, status, dep.pkg, source)

    rich.console.print(table)


def _install_missing(missing: list[Dep], yes: bool = False) -> None:
    """Install missing deps, grouping by official repo vs AUR."""
    official = [d for d in missing if not d.is_aur and d.pacman_pkg]
    aur_deps = [d for d in missing if d.is_aur and d.aur_pkg]

    if official:
        pkgs = [d.pacman_pkg for d in official if d.pacman_pkg]
        if yes or typer.confirm(
            f"Install {len(pkgs)} official package(s) via pacman? ({', '.join(pkgs)})"
        ):
            _run(
                "Installing official packages...",
                ["sudo", "pacman", "-S", "--needed", *pkgs],
            )

    if aur_deps:
        helper = _detect_aur_helper()
        if not helper:
            rich.warning_message(
                "No AUR helper found (yay, paru, trizen, pikaur). "
                "Install the following AUR packages manually:"
            )
            for dep in aur_deps:
                rich.print(f"  [dim]  • {dep.aur_pkg}[/dim]")
            return

        pkgs_aur = [d.aur_pkg for d in aur_deps if d.aur_pkg]
        if yes or typer.confirm(
            f"Install {len(pkgs_aur)} AUR package(s) via {helper}? ({', '.join(pkgs_aur)})"
        ):
            _run(
                f"Installing AUR packages with {helper}...",
                [helper, "-S", "--needed", *pkgs_aur],
            )


def _run(
    description: str,
    cmd: list[str],
    *,
    cwd: Optional[Path] = None,
    ok_codes: tuple[int, ...] = (0,),
) -> int:
    """Print a step label and run a command, exiting cleanly on unexpected failure.

    Returns the exit code of the command.
    ok_codes defines which exit codes are considered successful (default: only 0).
    """
    rich.print(f"[bold cyan]→[/bold cyan] {description}")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode not in ok_codes:
        rich.error_message(
            f"Return code {result.returncode} not in ok_codes: {ok_codes}"
        )
        rich.error_message(f"Command failed: {' '.join(str(c) for c in cmd)}")
        raise typer.Exit(code=1)
    return result.returncode


def _launch(description: str, cmd: list[str]) -> None:
    """Print a step label and spawn a long-running process in the background.

    Uses Popen with start_new_session=True so the child process is fully
    detached from qshellctl and keeps running after this command exits.
    """
    rich.print(f"[bold cyan]→[/bold cyan] {description}")
    subprocess.Popen(cmd, start_new_session=True)


def _cmake_install(install_dir: Path) -> None:
    """Run the full CMake configure → build → install pipeline."""
    _run(
        "Configuring build with CMake...",
        [
            "cmake",
            "-B",
            "build",
            "-G",
            "Ninja",
            "-DCMAKE_BUILD_TYPE=Release",
            "-DCMAKE_INSTALL_PREFIX=/",
            f"-DINSTALL_QSCONFDIR={install_dir}",
        ],
        cwd=install_dir,
    )
    _run(
        "Building (this may take a while)...",
        ["cmake", "--build", "build"],
        cwd=install_dir,
    )
    rich.print(
        "[dim]The next step installs compiled libraries to /usr/lib. "
        "sudo may ask for your password.[/dim]"
    )
    _run(
        "Installing system components (requires sudo)...",
        ["sudo", "cmake", "--install", "build"],
        cwd=install_dir,
    )


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@shells_app.command("deps")
def check_deps(
    install: bool = typer.Option(
        False,
        "--install",
        "-i",
        help="Install missing dependencies automatically.",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompts when installing.",
    ),
) -> None:
    """Check (and optionally install) all caelestia dependencies."""
    _print_deps_table(ALL_DEPS)

    missing = _get_missing(ALL_DEPS)
    if not missing:
        rich.success_message("All dependencies are satisfied.")
        return

    rich.warning_message(
        f"{len(missing)} missing dependenc{'y' if len(missing) == 1 else 'ies'} found."
    )

    if install:
        _install_missing(missing, yes=yes)
        still_missing = _get_missing(ALL_DEPS)
        if still_missing:
            rich.warning_message(
                f"{len(still_missing)} dependenc{'y' if len(still_missing) == 1 else 'ies'} "
                "could not be installed automatically."
            )
        else:
            rich.success_message("All dependencies are now satisfied.")
    else:
        rich.print(
            "[dim]Run [bold]qshellctl shells deps --install[/bold] to install them.[/dim]"
        )


@shells_app.command("install")
def install_caelestia(
    branch: Optional[str] = typer.Option(
        None,
        "--branch",
        "-b",
        help="Git branch or tag to clone (defaults to the remote HEAD).",
    ),
    skip_deps: bool = typer.Option(
        False,
        "--skip-deps",
        help="Skip the dependency check (for advanced users).",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Auto-confirm all prompts, including dependency installation.",
    ),
) -> None:
    """Install caelestia shell to ~/.config/quickshell/caelestia."""
    # 1. Dependency check
    if not skip_deps:
        missing = _get_missing(ALL_DEPS)
        if missing:
            rich.warning_message(
                f"{len(missing)} missing dependenc{'y' if len(missing) == 1 else 'ies'}:"
            )
            _print_deps_table(ALL_DEPS)

            if not yes and not typer.confirm(
                "Install missing dependencies and continue?"
            ):
                raise typer.Exit(code=1)

            _install_missing(missing, yes=yes)

            still_missing = _get_missing(ALL_DEPS)
            if still_missing:
                labels = ", ".join(d.label for d in still_missing)
                rich.error_message(
                    f"The following dependencies are still missing: {labels}. Aborting."
                )
                raise typer.Exit(code=1)

    # 2. Guard: already installed
    if CAELESTIA_INSTALL_DIR.exists():
        rich.error_message(
            f"Caelestia is already installed at {CAELESTIA_INSTALL_DIR}."
        )
        rich.print(
            "[dim]Run [bold]qshellctl shells update[/bold] to pull the latest changes.[/dim]"
        )
        raise typer.Exit(code=1)

    QUICKSHELL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # 3. Clone
    clone_cmd = ["git", "clone", CAELESTIA_REPO, str(CAELESTIA_INSTALL_DIR)]
    if branch:
        clone_cmd += ["--branch", branch]
    _run(f"Cloning caelestia shell{f' ({branch})' if branch else ''}...", clone_cmd)

    # 4. Build & install
    _cmake_install(CAELESTIA_INSTALL_DIR)

    # 5. Restore ownership (sudo cmake --install may chown dirs)
    current_user = os.environ.get("USER") or os.environ.get("LOGNAME") or ""
    if current_user:
        _run(
            f"Restoring ownership of {CAELESTIA_INSTALL_DIR} to {current_user}...",
            ["sudo", "chown", "-R", current_user, str(CAELESTIA_INSTALL_DIR)],
        )

    rich.success_message(f"Caelestia shell installed at {CAELESTIA_INSTALL_DIR}")
    rich.print(
        "[dim]Launch it with: [bold]qs -c caelestia[/bold] "
        "or [bold]caelestia shell -d[/bold][/dim]"
    )


@shells_app.command("switch")
def switch(name: str = typer.Argument(...)) -> None:
    """Stop the current shell and start another."""
    # 1. Leer ~/.config/qshellctl/state.json → saber cuál está activo
    # 2. shell_actual.stop()
    # 3. shell_nuevo.start()
    # 4. Actualizar state.json
    # pkill exits with 1 when no process matched — that is fine here.
    code = _run("Killing current shell...", ["pkill", "-x", "qs"], ok_codes=(0, 1))
    if code == 1:
        rich.print("[dim]No shell was running.[/dim]")

    _launch(f"Starting shell {name}...", ["qs", "-c", name])


@shells_app.command("update")
def update_caelestia() -> None:
    """Update caelestia shell by pulling the latest changes and rebuilding."""
    if not CAELESTIA_INSTALL_DIR.exists():
        rich.error_message(
            f"Caelestia does not appear to be installed at {CAELESTIA_INSTALL_DIR}."
        )
        rich.print(
            "[dim]Run [bold]qshellctl shells install[/bold] to install it first.[/dim]"
        )
        raise typer.Exit(code=1)

    _run("Pulling latest changes...", ["git", "pull"], cwd=CAELESTIA_INSTALL_DIR)
    _cmake_install(CAELESTIA_INSTALL_DIR)
    rich.success_message("Caelestia shell updated successfully.")


@shells_app.command("uninstall")
def uninstall_caelestia(
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip the confirmation prompt.",
    ),
) -> None:
    """Remove caelestia shell config files from ~/.config/quickshell/caelestia.

    Note: system-level libraries installed under /usr/lib/caelestia and
    /usr/lib/qt6/qml/Caelestia must be removed manually or via your package manager.
    """
    if not CAELESTIA_INSTALL_DIR.exists():
        rich.warning_message(
            f"Nothing to remove: {CAELESTIA_INSTALL_DIR} does not exist."
        )
        raise typer.Exit()

    if not yes:
        typer.confirm(
            f"This will permanently delete {CAELESTIA_INSTALL_DIR}. Continue?",
            abort=True,
        )

    try:
        shutil.rmtree(CAELESTIA_INSTALL_DIR)
    except OSError as exc:
        rich.error_message(f"Failed to remove {CAELESTIA_INSTALL_DIR}: {exc}")
        raise typer.Exit(code=1)

    rich.success_message(f"Removed {CAELESTIA_INSTALL_DIR}.")
    rich.warning_message(
        "System libraries (/usr/lib/caelestia, /usr/lib/qt6/qml/Caelestia) "
        "were NOT removed. Remove them manually if needed."
    )


@shells_app.command("status")
def status_caelestia() -> None:
    """Show the installation status of caelestia shell."""
    if not CAELESTIA_INSTALL_DIR.exists():
        rich.warning_message("Caelestia shell is [bold]not[/bold] installed.")
        rich.print(
            "[dim]Run [bold]qshellctl shells install[/bold] to install it.[/dim]"
        )
        return

    result_tag = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"],
        cwd=CAELESTIA_INSTALL_DIR,
        capture_output=True,
        text=True,
    )
    version = result_tag.stdout.strip() if result_tag.returncode == 0 else "unknown"

    result_rev = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=CAELESTIA_INSTALL_DIR,
        capture_output=True,
        text=True,
    )
    revision = result_rev.stdout.strip() if result_rev.returncode == 0 else "unknown"

    rich.success_message("Caelestia shell is installed.")
    rich.print(f"  [dim]Location :[/dim] {CAELESTIA_INSTALL_DIR}")
    rich.print(f"  [dim]Version  :[/dim] {version}")
    rich.print(f"  [dim]Revision :[/dim] {revision}")
