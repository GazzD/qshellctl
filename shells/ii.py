from pathlib import Path
from typing import Optional

from models.dep import Dep
from models.shell import CMakeShell, GitShell
from utils.checkers import font, pacman_q, pkgconfig, which
from utils.process import run

II_DOTFILES_DIR = Path.home() / ".cache" / "dots-hyprland"
II_HYPR_CONFIG_DIR = II_DOTFILES_DIR / ".config" / "hypr"
USER_HYPR_CONFIG_DIR = Path.home() / ".config" / "hypr"

# ---------------------------------------------------------------------------
# Dependency lists
# ---------------------------------------------------------------------------

II_RUNTIME_DEPS: list[Dep] = [
    Dep("quickshell", which("qs"), aur_pkg="quickshell-git"),
    Dep(
        "illogical-impulse-audio",
        which("illogical-impulse-audio"),
        aur_pkg="illogical-impulse-audio",
    ),
    Dep(
        "illogical-impulse-backlight",
        which("illogical-impulse-backlight"),
        aur_pkg="illogical-impulse-backlight",
    ),
    Dep(
        "illogical-impulse-basic",
        which("illogical-impulse-basic"),
        aur_pkg="illogical-impulse-basic",
    ),
    Dep(
        "illogical-impulse-bibata-modern-classic-bin",
        which("illogical-impulse-bibata-modern-classic-bin"),
        aur_pkg="illogical-impulse-bibata-modern-classic-bin",
    ),
    Dep(
        "illogical-impulse-fonts-themes",
        which("illogical-impulse-fonts-themes"),
        aur_pkg="illogical-impulse-fonts-themes",
    ),
    Dep("illogical-impulse-", which("illogical-"), aur_pkg="illogical-impulse-"),
    Dep("illogical-impulse-", which("illogical-"), aur_pkg="illogical-impulse-"),
    Dep("illogical-impulse-", which("illogical-"), aur_pkg="illogical-impulse-"),
    Dep("illogical-impulse-", which("illogical-"), aur_pkg="illogical-impulse-"),
    Dep("illogical-impulse-", which("illogical-"), aur_pkg="illogical-impulse-"),
    Dep("illogical-impulse-", which("illogical-"), aur_pkg="illogical-impulse-"),
    Dep("illogical-impulse-", which("illogical-"), aur_pkg="illogical-impulse-"),
    Dep("illogical-impulse-", which("illogical-"), aur_pkg="illogical-impulse-"),
]


# ---------------------------------------------------------------------------
# Concrete shell
# ---------------------------------------------------------------------------


class IllogicalImpulseShell(GitShell):
    """Illogical Impulse shell — https://github.com/end-4/dots-hyprland/."""

    name = "illogical-impulse"
    shell_url = "https://github.com/end-4/dots-hyprland.git"

    @property
    def install_dir(self) -> Path:
        return II_DOTFILES_DIR

    def install(
        self, branch: Optional[str] = None, yes: bool = False, skip_deps: bool = False
    ) -> None:
        run("Installing dependencies...", ["ls", "-la"])
        # Clone repo
        # super().install(branch, yes, skip_deps)

        # Install deps
        # run("Installing dependencies...", ["./setup", "install-deps"])

        # Setup for permissions/services etc
        # run("Setup for permissions/services etc", ["./setup", "install-setups"])

        # Install config files
        run(
            "Installing config files",
            ["ln -s", str(II_HYPR_CONFIG_DIR), str(USER_HYPR_CONFIG_DIR / self.name)],
        )
