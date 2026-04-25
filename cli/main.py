import os
import shutil
import sys
from os import path
from typing import Optional

import typer
from rich.table import Table

import utils.rich_helper as rich
import utils.state as state
from models.exceptions import BootstrapError
from utils.bootstrap import initialize_profile_system
from cli.shells import shells_app

console = rich.console
app = typer.Typer(
    no_args_is_help=True,
    help="qshellctl: manage shell profiles and system compatibility.",
)

app.add_typer(shells_app, name="shells")


@app.callback()
def main() -> None:
    """qshellctl root command."""
    pass


@app.command()
def init(
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip the confirmation prompt.",
    ),
) -> None:
    """Initialize qshellctl's Hyprland profile system."""
    bootstrap_status = state.detect_bootstrap()
    if bootstrap_status.initialized:
        rich.success_message("Hyprland profile system is already initialized.")
        raise typer.Exit()

    if not bootstrap_status.hyprland_conf_exists:
        rich.error_message(
            "Hyprland config not found at ~/.config/hypr/hyprland.conf. "
            "Create it before running qshellctl init."
        )
        raise typer.Exit(code=1)

    rich.print("[bold]qshellctl will initialize your Hyprland profile system.[/bold]")
    rich.print("[dim]This will:[/dim]")
    rich.print("  [cyan]•[/cyan] create ~/.config/hypr/default/ if needed")
    rich.print("  [cyan]•[/cyan] copy your current Hyprland config into that profile")
    rich.print("  [cyan]•[/cyan] back up ~/.config/hypr/hyprland.conf")
    rich.print("  [cyan]•[/cyan] rewrite the root config as a profile selector")
    rich.print("  [cyan]•[/cyan] save initial state with active_profile = default")

    if not yes:
        typer.confirm("Continue?", abort=True)

    try:
        result = initialize_profile_system()
    except BootstrapError as exc:
        rich.error_message(str(exc))
        raise typer.Exit(code=1)

    rich.success_message("Initialized Hyprland profile system.")
    rich.print(
        f"[dim]Default profile :[/dim] [bold]{result.default_profile_dir}[/bold]"
    )
    if result.backup_path is not None:
        rich.print(f"[dim]Root backup     :[/dim] [bold]{result.backup_path}[/bold]")
    if result.copied_entries:
        rich.print(f"[dim]Copied entries  :[/dim] {result.copied_entries}")
    if result.root_rewritten:
        rich.print(
            "[dim]Root hyprland.conf now uses:[/dim] "
            "[bold]$profile = default[/bold]"
        )
    rich.print(
        "[dim]Next step: install a shell with "
        "[bold]qshellctl shells install <name>[/bold][/dim]"
    )


@app.command()
def doctor() -> None:
    """Run system checks and report compatibility issues."""
    rich.print("Running system checks for qshellctl...")

    # --- 1. Data gathering ---
    git_found = shutil.which("git") is not None
    python_version_ok = sys.version_info >= (3, 12)
    hyprland_detected = "HYPRLAND_INSTANCE_SIGNATURE" in os.environ
    linux_distro = get_linux_distro()
    bootstrap_status = state.detect_bootstrap()
    checks = {
        "Python": {
            "ok": python_version_ok,
            "msg": f"{sys.version.split()[0]}",
        },
        "Git": {
            "ok": git_found,
            "msg": "Installed" if git_found else "Not found",
        },
        "Linux Distro": {
            "ok": linux_distro is not None,
            "msg": linux_distro or "Unknown",
        },
        "Hyprland": {
            "ok": hyprland_detected,
            "msg": "Detected" if hyprland_detected else "Not active",
        },
        "Profile Bootstrap": {
            "ok": bootstrap_status.initialized,
            "msg": bootstrap_status.detail(),
        },
    }

    # --- 3. Summary Table ---
    table = Table(title="Environment Check Summary", title_style="bold magenta")
    table.add_column("Component", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Details", style="dim")

    for component, data in checks.items():
        icon = "[green]✔[/green]" if data["ok"] else "[red]✗[/red]"
        table.add_row(component, icon, data["msg"])

    console.print(table)

    # --- 4. Final Result ---
    all_passed = all(check["ok"] for check in checks.values())

    if all_passed:
        rich.success_message("All checks passed! Your system is ready.")
    else:
        rich.error_message("Some checks failed. Please address the issues above.")


def get_linux_distro() -> Optional[str]:
    """Attempt to detect Linux distribution from /etc/os-release."""
    os_release_path = "/etc/os-release"
    if not path.exists(os_release_path):
        return None
    # Read os_release_path file
    with open(os_release_path, "r", encoding="utf-8") as f:
        for line in f:
            # Look for the line starting with "ID=" to get the distro identifier.
            if line.startswith("ID="):
                # Extract the value after "ID=" and strip any surrounding quotes.
                return line.split("=", 1)[1].strip().strip('"')
    return None


if __name__ == "__main__":
    app()
