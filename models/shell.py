import os
import shutil
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import utils.deps as deps_utils
import utils.process as process
import utils.rich_helper as rich
from models.dep import Dep
from models.exceptions import (
    DependencyError,
    ShellAlreadyInstalledError,
    ShellError,
    ShellNotInstalledError,
)

QUICKSHELL_CONFIG_DIR = Path.home() / ".config" / "quickshell"


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


class Shell(ABC):
    """Common interface for all Quickshell configurations.

    Subclasses must declare two class-level attributes:

        name     (str) – unique identifier used as the install dir name
                         and in CLI commands, e.g. "caelestia".
        shell_url (str) – git URL of the upstream repository.
        dots_url (str) – git URL of the upstream dotfiles repository.
        dots_files (list[str]) – list of dotfiles to install.

    Then they must implement :meth:`install` and :meth:`update`.
    All other methods have sensible defaults that subclasses may override.
    """

    name: str
    shell_url: str
    dots_url: str
    dots_files: list[str]

    # ------------------------------------------------------------------
    # Filesystem helpers
    # ------------------------------------------------------------------

    @property
    def install_dir(self) -> Path:
        """Default install location: ~/.config/quickshell/<name>."""
        return QUICKSHELL_CONFIG_DIR / self.name

    def is_installed(self) -> bool:
        return self.install_dir.exists()

    # ------------------------------------------------------------------
    # Dependency declarations (override to add deps)
    # ------------------------------------------------------------------

    def build_deps(self) -> list[Dep]:
        """Dependencies required to compile the shell. Empty by default."""
        return []

    def runtime_deps(self) -> list[Dep]:
        """Dependencies required to run the shell. Empty by default."""
        return []

    def all_deps(self) -> list[Dep]:
        return self.build_deps() + self.runtime_deps()

    # ------------------------------------------------------------------
    # Lifecycle — must be implemented by concrete shells
    # ------------------------------------------------------------------

    @abstractmethod
    def install(
        self,
        branch: Optional[str] = None,
        yes: bool = False,
        skip_deps: bool = False,
    ) -> None:
        """Install the shell from scratch.

        Args:
            branch:    Optional git branch or tag to check out.
            yes:       Skip interactive confirmation prompts.
            skip_deps: Skip the dependency check entirely.
        """

    @abstractmethod
    def update(self) -> None:
        """Pull the latest changes and apply them (e.g. rebuild)."""

    # ------------------------------------------------------------------
    # Lifecycle — default implementations (safe to override)
    # ------------------------------------------------------------------

    def uninstall(self) -> None:
        """Remove the shell's config directory.

        Confirmation (if desired) is the responsibility of the caller
        so that this method stays free of any UI concerns.
        """
        if not self.is_installed():
            raise ShellNotInstalledError(
                f"Nothing to remove: {self.install_dir} does not exist."
            )
        try:
            shutil.rmtree(self.install_dir)
        except OSError as exc:
            raise ShellError(f"Failed to remove {self.install_dir}: {exc}") from exc

        rich.success_message(f"Removed {self.install_dir}.")

    def status(self) -> None:
        """Print the installation status of the shell."""
        if not self.is_installed():
            rich.warning_message(f"{self.name} shell is [bold]not[/bold] installed.")
            return

        rich.success_message(f"{self.name} shell is installed.")
        rich.print(f"  [dim]Location :[/dim] {self.install_dir}")

    def start(self) -> None:
        """Launch the shell (detached). Override for custom launch commands."""
        process.launch(f"Starting {self.name}...", ["qs", "-c", self.name])

    def stop(self) -> None:
        """Stop any running qs instance. Override for custom stop behaviour."""
        code = process.run(
            "Killing current shell...", ["pkill", "-x", "qs"], ok_codes=(0, 1)
        )
        if code == 1:
            rich.print("[dim]No shell was running.[/dim]")


# ---------------------------------------------------------------------------
# Intermediate base: git-based shells (clone only, no build step)
# ---------------------------------------------------------------------------


class GitShell(Shell):
    """Shell installed from a git repository with no compilation step.

    Provides a full default lifecycle based on git clone / pull.
    Shells that only need their dotfiles cloned can inherit directly from
    this class without overriding anything beyond ``name``, ``shell_url``
    and the optional ``*_deps`` methods.
    """

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def install(
        self,
        branch: Optional[str] = None,
        yes: bool = False,
        skip_deps: bool = False,
    ) -> None:
        if self.is_installed():
            raise ShellAlreadyInstalledError(
                f"{self.name} is already installed at {self.install_dir}. "
                f"Run 'qshellctl shells update {self.name}' to update it."
            )

        QUICKSHELL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        if not skip_deps:
            self._ensure_deps(yes=yes)

        clone_cmd = ["git", "clone", self.shell_url, str(self.install_dir)]
        if branch:
            clone_cmd += ["--branch", branch]
        process.run(
            f"Cloning {self.name}{f' ({branch})' if branch else ''}...", clone_cmd
        )

    def update(self) -> None:
        if not self.is_installed():
            raise ShellNotInstalledError(
                f"{self.name} does not appear to be installed at {self.install_dir}. "
                f"Run 'qshellctl shells install {self.name}' first."
            )
        process.run("Stash possible changes...", ["git", "stash"], cwd=self.install_dir)
        process.run("Pulling latest changes...", ["git", "pull"], cwd=self.install_dir)

    def status(self) -> None:
        if not self.is_installed():
            rich.warning_message(f"{self.name} shell is [bold]not[/bold] installed.")
            return

        result_tag = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=self.install_dir,
            capture_output=True,
            text=True,
        )
        version = result_tag.stdout.strip() if result_tag.returncode == 0 else "unknown"

        result_rev = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=self.install_dir,
            capture_output=True,
            text=True,
        )
        revision = (
            result_rev.stdout.strip() if result_rev.returncode == 0 else "unknown"
        )

        rich.success_message(f"{self.name} shell is installed.")
        rich.print(f"  [dim]Location :[/dim] {self.install_dir}")
        rich.print(f"  [dim]Version  :[/dim] {version}")
        rich.print(f"  [dim]Revision :[/dim] {revision}")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _ensure_deps(self, yes: bool = False) -> None:
        """Check all deps and offer to install missing ones.

        Raises :exc:`DependencyError` if any dep remains missing after
        the installation attempt.
        """
        all_deps = self.all_deps()
        if not all_deps:
            return

        missing = deps_utils.get_missing(all_deps)
        if not missing:
            return

        rich.warning_message(
            f"{len(missing)} missing dependenc{'y' if len(missing) == 1 else 'ies'}:"
        )
        deps_utils.print_deps_table(missing, title=f"{self.name} – missing deps")

        deps_utils.install_missing(missing, yes=yes)

        still_missing = deps_utils.get_missing(all_deps)
        if still_missing:
            labels = ", ".join(d.label for d in still_missing)
            raise DependencyError(
                f"The following dependencies are still missing: {labels}."
            )


# ---------------------------------------------------------------------------
# Intermediate base: shells that require a CMake build step
# ---------------------------------------------------------------------------


class CMakeShell(GitShell):
    """Shell that must be compiled with CMake after cloning.

    Inherits the full git lifecycle from :class:`GitShell` and adds a
    CMake configure → build → install pipeline on top of it.

    The install prefix defaults to ``/`` which is standard for Quickshell
    plugins; override ``cmake_install_prefix`` in the subclass if needed.
    """

    cmake_install_prefix: str = "/"

    # ------------------------------------------------------------------
    # Lifecycle overrides
    # ------------------------------------------------------------------

    def install(
        self,
        branch: Optional[str] = None,
        yes: bool = False,
        skip_deps: bool = False,
    ) -> None:
        # 1. Clone (dependency check is done inside GitShell.install)
        super().install(branch=branch, yes=yes, skip_deps=skip_deps)
        # 2. Compile & install system components
        self._cmake_build()
        # 3. Fix ownership that sudo cmake --install may have changed
        self._restore_ownership()

        rich.success_message(f"{self.name} shell installed at {self.install_dir}.")
        rich.print(f"[dim]Launch it with: [bold]qs -c {self.name}[/bold][/dim]")

    def update(self) -> None:
        # 1. Pull
        super().update()
        # 2. Rebuild
        self._cmake_build()
        rich.success_message(f"{self.name} shell updated successfully.")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _cmake_build(self) -> None:
        """Run the full CMake configure → build → install pipeline."""
        process.run(
            "Configuring build with CMake...",
            [
                "cmake",
                "-B",
                "build",
                "-G",
                "Ninja",
                "-DCMAKE_BUILD_TYPE=Release",
                f"-DCMAKE_INSTALL_PREFIX={self.cmake_install_prefix}",
                f"-DINSTALL_QSCONFDIR={self.install_dir}",
            ],
            cwd=self.install_dir,
        )
        process.run(
            "Building (this may take a while)...",
            ["cmake", "--build", "build"],
            cwd=self.install_dir,
        )
        rich.print(
            "[dim]The next step installs compiled libraries to /usr/lib. "
            "sudo may ask for your password.[/dim]"
        )
        process.run(
            "Installing system components (requires sudo)...",
            ["sudo", "cmake", "--install", "build"],
            cwd=self.install_dir,
        )

    def _restore_ownership(self) -> None:
        """Restore ownership of the install dir after a sudo cmake --install."""
        user = os.environ.get("USER") or os.environ.get("LOGNAME") or ""
        if not user:
            return
        process.run(
            f"Restoring ownership of {self.install_dir} to {user}...",
            ["sudo", "chown", "-R", user, str(self.install_dir)],
        )
