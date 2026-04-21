import shutil
from pathlib import Path
from typing import Optional

import utils.process as process
import utils.rich_helper as rich
from models.dep import Dep
from models.exceptions import ShellError, ShellNotInstalledError
from models.shell import GitShell, QUICKSHELL_CONFIG_DIR
from utils.checkers import pacman_q, which

II_DOTFILES_DIR = Path.home() / ".cache" / "dots-hyprland"

# ---------------------------------------------------------------------------
# Dependency lists
#
# ii ships its own AUR meta-packages that group all transitive dependencies.
# We detect them with pacman_q (package presence) rather than which (binary
# presence) because most of these packages don't install a named executable.
# ---------------------------------------------------------------------------

II_RUNTIME_DEPS: list[Dep] = [
    Dep("quickshell", which("qs"), aur_pkg="illogical-impulse-quickshell-git"),
    Dep(
        "illogical-impulse-audio",
        pacman_q("illogical-impulse-audio"),
        aur_pkg="illogical-impulse-audio",
    ),
    Dep(
        "illogical-impulse-backlight",
        pacman_q("illogical-impulse-backlight"),
        aur_pkg="illogical-impulse-backlight",
    ),
    Dep(
        "illogical-impulse-basic",
        pacman_q("illogical-impulse-basic"),
        aur_pkg="illogical-impulse-basic",
    ),
    Dep(
        "illogical-impulse-bibata-modern-classic-bin",
        pacman_q("illogical-impulse-bibata-modern-classic-bin"),
        aur_pkg="illogical-impulse-bibata-modern-classic-bin",
    ),
    Dep(
        "illogical-impulse-fonts-themes",
        pacman_q("illogical-impulse-fonts-themes"),
        aur_pkg="illogical-impulse-fonts-themes",
    ),
    Dep(
        "illogical-impulse-hyprland",
        pacman_q("illogical-impulse-hyprland"),
        aur_pkg="illogical-impulse-hyprland",
    ),
    Dep(
        "illogical-impulse-kde",
        pacman_q("illogical-impulse-kde"),
        aur_pkg="illogical-impulse-kde",
    ),
    Dep(
        "illogical-impulse-portal",
        pacman_q("illogical-impulse-portal"),
        aur_pkg="illogical-impulse-portal",
    ),
    Dep(
        "illogical-impulse-python",
        pacman_q("illogical-impulse-python"),
        aur_pkg="illogical-impulse-python",
    ),
    Dep(
        "illogical-impulse-screencapture",
        pacman_q("illogical-impulse-screencapture"),
        aur_pkg="illogical-impulse-screencapture",
    ),
    Dep(
        "illogical-impulse-toolkit",
        pacman_q("illogical-impulse-toolkit"),
        aur_pkg="illogical-impulse-toolkit",
    ),
    Dep(
        "illogical-impulse-widgets",
        pacman_q("illogical-impulse-widgets"),
        aur_pkg="illogical-impulse-widgets",
    ),
    Dep(
        "illogical-impulse-microtex-git",
        pacman_q("illogical-impulse-microtex-git"),
        aur_pkg="illogical-impulse-microtex-git",
    ),
]


# ---------------------------------------------------------------------------
# Concrete shell
# ---------------------------------------------------------------------------


class IllogicalImpulseShell(GitShell):
    """Illogical Impulse shell — https://github.com/end-4/dots-hyprland/."""

    name = "ii"
    shell_url = "https://github.com/end-4/dots-hyprland.git"
    dots_url = "https://github.com/end-4/dots-hyprland.git"

    @property
    def install_dir(self) -> Path:
        return II_DOTFILES_DIR

    @property
    def quickshell_dir(self) -> Path:
        return QUICKSHELL_CONFIG_DIR / self.name

    def is_installed(self) -> bool:
        return self.install_dir.exists() and self.quickshell_dir.exists()

    def runtime_deps(self) -> list[Dep]:
        return II_RUNTIME_DEPS

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def install(
        self,
        branch: Optional[str] = None,
        yes: bool = False,
        skip_deps: bool = False,
    ) -> None:
        # Clone repo. Dependency checks are delegated to ./setup install-deps
        #    below, so we always pass skip_deps=True to the git clone step.
        super().install(branch=branch, yes=yes, skip_deps=True)

        # Install AUR meta-packages via the upstream script.
        if not skip_deps:
            flags = ["--skip-sysupdate"]
            if yes:
                flags += ["-f"]
            process.run(
                "Installing dependencies via ./setup install-deps (this may take a while)...",
                ["./setup", "install-deps"] + flags,
                cwd=self.install_dir,
            )

        # Configure permissions, systemd services, python venv, gsettings.
        setup_flags = ["--skip-sysupdate"]
        if yes:
            setup_flags += ["-f"]
        process.run(
            "Configuring services and permissions...",
            ["./setup", "install-setups"] + setup_flags,
            cwd=self.install_dir,
        )

        # Rsync Hyprland dotfiles into the ii profile directory.
        self.sync_hypr_profile()

        # Rsync Hyprland quickshell config into the ii profile directory.
        self.sync_quickshell()

        rich.success_message(f"{self.name} source repo cloned and local config bootstrapped.")
        rich.print(
            f"[dim]Hyprland profile created at [bold]~/.config/hypr/{self.name}/[/bold][/dim]"
        )
        rich.print(
            "[dim]Quickshell config deployed to "
            f"[bold]~/.config/quickshell/{self.name}/[/bold][/dim]"
        )
        rich.print(
            f"[dim]Switch to it with: [bold]qshellctl shells switch {self.name}[/bold][/dim]"
        )

    def update(self) -> None:
        # git stash + git pull
        super().update()
        # Rsync updated dotfiles, backing up any local changes first.
        # self.sync_hypr_profile(backup=True)
        self.sync_quickshell()
        rich.success_message(
            f"{self.name} source repo updated and Quickshell config synced."
        )

    def uninstall(self) -> None:
        paths_to_remove = [path for path in (self.install_dir, self.quickshell_dir) if path.exists()]
        if not paths_to_remove:
            raise ShellNotInstalledError(
                f"Nothing to remove: neither {self.install_dir} nor {self.quickshell_dir} exist."
            )

        for path in paths_to_remove:
            try:
                shutil.rmtree(path)
            except OSError as exc:
                raise ShellError(f"Failed to remove {path}: {exc}") from exc

        rich.success_message(
            f"Removed {', '.join(str(path) for path in paths_to_remove)}."
        )

    # ------------------------------------------------------------------
    # Dotfile sync
    # ------------------------------------------------------------------

    def sync_dotfiles(self, *, backup: bool = True) -> None:
        """Sync dotfiles from the repo into the home directory."""
        src = self.install_dir / "dots" / ".config"
        dst = Path.home() / ".config"
        self._rsync(src, dst, backup=backup)

    def sync_hypr_profile(self, *, backup: bool = True) -> None:
        """Sync dots-hyprland's hypr config into ~/.config/hypr/ii/."""
        src = self.install_dir / "dots" / ".config" / "hypr"
        dst = Path.home() / ".config" / "hypr" / self.name
        self._rsync(src, dst, backup=backup)

    def sync_quickshell(self, *, backup: bool = True) -> None:
        """Sync dots-hyprland's quickshell config into ~/.config/quickshell/ii/."""
        src = self.install_dir / "dots" / ".config" / "quickshell" / "ii"
        dst = Path.home() / ".config" / "quickshell" / self.name
        self._rsync(src, dst, backup=backup)
