import shutil
from typing import Optional

import typer
from rich.table import Table

import utils.rich_helper as rich
from models.dep import Dep


def detect_aur_helper() -> Optional[str]:
    """Return the first available AUR helper found in PATH, or None."""
    for helper in ["yay", "paru", "trizen", "pikaur"]:
        if shutil.which(helper):
            return helper
    return None


def get_missing(deps: list[Dep]) -> list[Dep]:
    """Return only the deps that are not currently installed."""
    return [dep for dep in deps if not dep.is_installed()]


def print_deps_table(deps: list[Dep], title: str = "Dependencies") -> None:
    """Render a Rich table showing the status of each dependency."""
    table = Table(title=title, title_style="bold magenta")
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


def install_missing(missing: list[Dep], yes: bool = False) -> None:
    """Install missing dependencies, grouping by official repo vs AUR.

    When *yes* is False the user is prompted for confirmation before
    each group is installed.
    """
    # Avoid a circular import at module level (process → rich → here)
    from utils.process import run

    official = [d for d in missing if not d.is_aur and d.pacman_pkg]
    aur_deps = [d for d in missing if d.is_aur and d.aur_pkg]

    if official:
        pkgs = [d.pacman_pkg for d in official if d.pacman_pkg]
        if yes or typer.confirm(
            f"Install {len(pkgs)} official package(s) via pacman? ({', '.join(pkgs)})"
        ):
            run(
                "Installing official packages...",
                ["sudo", "pacman", "-S", "--needed", *pkgs],
            )

    if aur_deps:
        helper = detect_aur_helper()
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
            run(
                f"Installing AUR packages with {helper}...",
                [helper, "-S", "--needed", *pkgs_aur],
            )
