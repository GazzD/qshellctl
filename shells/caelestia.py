from pathlib import Path

import utils.process as process
from models.dep import Dep
from models.shell import CMakeShell
from utils.checkers import font, pacman_q, pkgconfig, which

# ---------------------------------------------------------------------------
# Dependency lists
# ---------------------------------------------------------------------------

CAELESTIA_BUILD_DEPS: list[Dep] = [
    Dep("git", which("git"), pacman_pkg="git"),
    Dep("cmake", which("cmake"), pacman_pkg="cmake"),
    Dep("ninja", which("ninja"), pacman_pkg="ninja"),
]

CAELESTIA_RUNTIME_DEPS: list[Dep] = [
    Dep("quickshell", which("qs"), aur_pkg="quickshell-git"),
    Dep("caelestia-cli", which("caelestia"), aur_pkg="caelestia-cli"),
    Dep("ddcutil", which("ddcutil"), pacman_pkg="ddcutil"),
    Dep("brightnessctl", which("brightnessctl"), pacman_pkg="brightnessctl"),
    Dep("app2unit", which("app2unit"), aur_pkg="app2unit"),
    Dep("libcava", pkgconfig("libcava"), aur_pkg="libcava"),
    Dep("networkmanager", which("nmcli"), pacman_pkg="networkmanager"),
    Dep("lm-sensors", which("sensors"), pacman_pkg="lm_sensors"),
    Dep("fish", which("fish"), pacman_pkg="fish"),
    Dep("aubio", pkgconfig("aubio"), pacman_pkg="aubio"),
    Dep("pipewire", pkgconfig("libpipewire-0.3"), pacman_pkg="pipewire"),
    Dep("qt6-declarative", pacman_q("qt6-declarative"), pacman_pkg="qt6-declarative"),
    Dep("qt6-base", pacman_q("qt6-base"), pacman_pkg="qt6-base"),
    Dep("swappy", which("swappy"), pacman_pkg="swappy"),
    Dep("libqalculate", pkgconfig("libqalculate"), pacman_pkg="libqalculate"),
    Dep(
        "material-symbols",
        font("Material Symbols"),
        aur_pkg="ttf-material-symbols-variable-git",
    ),
    Dep(
        "caskaydia-cove-nerd",
        font("CaskaydiaCove"),
        pacman_pkg="ttf-caskaydia-cove-nerd",
    ),
]


# ---------------------------------------------------------------------------
# Concrete shell
# ---------------------------------------------------------------------------


class CaelestiaShell(CMakeShell):
    """Caelestia shell — https://github.com/caelestia-dots/shell."""

    name = "caelestia"
    shell_url = "https://github.com/caelestia-dots/shell.git"
    dots_url = "https://github.com/caelestia-dots/caelestia.git"

    @property
    def dots_dir(self) -> Path:
        """Local clone of the caelestia dotfiles repo."""
        return Path.home() / ".cache" / "caelestia-dots"

    def build_deps(self) -> list[Dep]:
        return CAELESTIA_BUILD_DEPS

    def runtime_deps(self) -> list[Dep]:
        return CAELESTIA_RUNTIME_DEPS

    def install(
        self,
        branch: str | None = None,
        yes: bool = False,
        skip_deps: bool = False,
    ) -> None:
        super().install(branch=branch, yes=yes, skip_deps=skip_deps)
        self.sync_hypr_profile()

    def update(self) -> None:
        super().update()
        # self.sync_hypr_profile(backup=True)

    def stop(self) -> None:
        """Stop caelestia using its own CLI kill command."""
        process.run(
            "Killing caelestia shell...", ["caelestia", "shell", "-k"], ok_codes=(0, 1)
        )

    # ------------------------------------------------------------------
    # Dotfile sync
    # ------------------------------------------------------------------

    def sync_dotfiles(self, *, backup: bool = True) -> None:
        """Sync dotfiles from the repo into the home directory."""
        # FIXME: Caelestia dotfiles have hypr folder, syncing directly may overwrite, think about a better approach
        # src = self.dots_dir
        # dst = Path.home() / ".config"
        # self._rsync(src, dst, backup=backup)

    def sync_hypr_profile(self, *, backup: bool = False) -> None:
        """Clone (or update) the caelestia dotfiles repo and sync the
        Hyprland config into ~/.config/hypr/caelestia/.
        """
        if not self.dots_dir.exists():
            process.run(
                "Cloning caelestia dotfiles...",
                ["git", "clone", self.dots_url, str(self.dots_dir)],
            )
        else:
            process.run(
                "Updating caelestia dotfiles...",
                ["git", "pull"],
                cwd=self.dots_dir,
            )

        src = self.dots_dir / ".config" / "hypr"
        dst = Path.home() / ".config" / "hypr" / self.name
        self._rsync(src, dst, backup=backup)
