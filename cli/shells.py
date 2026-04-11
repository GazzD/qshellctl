import re
from pathlib import Path
from typing import Optional

import typer

import utils.deps as deps_utils
import utils.process as process
import utils.rich_helper as rich
import utils.state as state
from models.exceptions import (
    DependencyError,
    ProcessError,
    ShellAlreadyInstalledError,
    ShellError,
    ShellNotFoundError,
    ShellNotInstalledError,
)
from shells import get_shell, list_shells

shells_app = typer.Typer(help="Manage Quickshell shell installations.")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _resolve(name: str):
    """Return the shell instance or exit with a friendly error."""
    try:
        return get_shell(name)
    except ShellNotFoundError as exc:
        rich.error_message(str(exc))
        raise typer.Exit(code=1)


def _handle_shell_error(exc: Exception) -> None:
    """Print a shell/process error and exit with code 1."""
    rich.error_message(str(exc))
    raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@shells_app.command("list")
def list_available() -> None:
    """List all available shells."""
    shells = list_shells()
    rich.print("[bold]Available shells:[/bold]")
    for name in shells:
        rich.print(f"  [cyan]•[/cyan] {name}")


@shells_app.command("deps")
def check_deps(
    name: str = typer.Argument(..., help="Shell name (e.g. caelestia)."),
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
    """Check (and optionally install) the dependencies for a shell."""
    shell = _resolve(name)
    all_deps = shell.all_deps()

    if not all_deps:
        rich.success_message(f"{name} has no declared dependencies.")
        return

    deps_utils.print_deps_table(all_deps, title=f"{name} – dependencies")

    missing = deps_utils.get_missing(all_deps)
    if not missing:
        rich.success_message("All dependencies are satisfied.")
        return

    rich.warning_message(
        f"{len(missing)} missing dependenc{'y' if len(missing) == 1 else 'ies'} found."
    )

    if install:
        try:
            deps_utils.install_missing(missing, yes=yes)
        except ProcessError as exc:
            _handle_shell_error(exc)

        still_missing = deps_utils.get_missing(all_deps)
        if still_missing:
            rich.warning_message(
                f"{len(still_missing)} dependenc{'y' if len(still_missing) == 1 else 'ies'} "
                "could not be installed automatically."
            )
        else:
            rich.success_message("All dependencies are now satisfied.")
    else:
        rich.print(
            f"[dim]Run [bold]qshellctl shells deps {name} --install[/bold] to install them.[/dim]"
        )


@shells_app.command("install")
def install_shell(
    name: str = typer.Argument(..., help="Shell name (e.g. caelestia)."),
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
    """Install a shell to ~/.config/quickshell/<name>."""
    shell = _resolve(name)

    try:
        shell.install(branch=branch, yes=yes, skip_deps=skip_deps)
    except ShellAlreadyInstalledError as exc:
        rich.error_message(str(exc))
        raise typer.Exit(code=1)
    except DependencyError as exc:
        rich.error_message(str(exc))
        raise typer.Exit(code=1)
    except (ShellError, ProcessError) as exc:
        _handle_shell_error(exc)


@shells_app.command("update")
def update_shell(
    name: str = typer.Argument(..., help="Shell name (e.g. caelestia)."),
) -> None:
    """Update a shell by pulling the latest changes and rebuilding."""
    shell = _resolve(name)
    try:
        shell.update()
    except ShellNotInstalledError as exc:
        rich.error_message(str(exc))
        rich.print(
            f"[dim]Run [bold]qshellctl shells install {name}[/bold] to install it first.[/dim]"
        )
        raise typer.Exit(code=1)
    except (ShellError, ProcessError) as exc:
        _handle_shell_error(exc)


@shells_app.command("uninstall")
def uninstall_shell(
    name: str = typer.Argument(..., help="Shell name (e.g. caelestia)."),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip the confirmation prompt.",
    ),
) -> None:
    """Remove a shell's config files from ~/.config/quickshell/<name>."""
    shell = _resolve(name)

    if not yes:
        typer.confirm(
            f"This will permanently delete {shell.install_dir}. Continue?",
            abort=True,
        )

    try:
        shell.uninstall()
    except ShellNotInstalledError as exc:
        rich.warning_message(str(exc))
        raise typer.Exit()
    except ShellError as exc:
        _handle_shell_error(exc)


@shells_app.command("status")
def shell_status(
    name: str = typer.Argument(..., help="Shell name (e.g. caelestia)."),
) -> None:
    """Show the installation status of a shell."""
    shell = _resolve(name)
    shell.status()


@shells_app.command("switch")
def switch_shell(
    name: str = typer.Argument(..., help="Shell name to switch to (e.g. caelestia)."),
) -> None:
    """Switch the active Hyprland profile and restart the shell."""
    # Validate the shell name exists in the registry before doing anything.
    _resolve(name)

    # 1. Validate the Hyprland profile exists before doing anything destructive.
    current_state = state.load()
    hyprland_conf = Path(
        current_state.get(
            "hyprland_conf", Path.home() / ".config" / "hypr" / "hyprland.conf"
        )
    )
    profile_conf = hyprland_conf.parent / name / "hyprland.conf"

    if not profile_conf.exists():
        rich.error_message(
            f"Hyprland profile not found: {profile_conf}\n"
            f"  Create ~/.config/hypr/{name}/ with a hyprland.conf before switching."
        )
        raise typer.Exit(code=1)

    try:
        # 2. Stop the currently active shell
        active_profile = current_state.get("active_profile")
        if active_profile and active_profile != name:
            try:
                active_shell = get_shell(active_profile)
                active_shell.stop()
            except ShellNotFoundError:
                # Active profile may be 'default' or unregistered — skip gracefully.
                pass

        # 3. Edit $profile = <name> in hyprland.conf.
        conf_text = hyprland_conf.read_text()
        new_conf_text = re.sub(
            r"^\$profile\s*=\s*\S+",
            f"$profile = {name}",
            conf_text,
            flags=re.MULTILINE,
        )
        hyprland_conf.write_text(new_conf_text)
        rich.print(f"[dim]Updated $profile = {name} in {hyprland_conf}[/dim]")

        # 4. Reload Hyprland — to apply new profile settings (keybindings, rules, etc.)
        process.run("Reloading Hyprland...", ["hyprctl", "reload"])

        # 5. Launch the new shell
        destination_shell = get_shell(name)
        destination_shell.start()

        # 6. Persist the new active profile.
        current_state["active_profile"] = name
        state.save(current_state)

        rich.success_message(f"Switched to {name}.")

    except (ShellError, ProcessError) as exc:
        _handle_shell_error(exc)
