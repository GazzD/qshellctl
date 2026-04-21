from typing import Optional

import utils.rich_helper as rich
from models.shell import Shell


class DefaultShell(Shell):
    """Fallback profile — Hyprland without any Quickshell shell.

    This entry represents the ``default`` Hyprland profile.  There is nothing
    to install, update, or uninstall; the profile directory is managed by the
    user directly.  Switching to ``default`` stops any running QS instance and
    reloads Hyprland with the default profile config.
    """

    name = "default"
    shell_url = ""
    dots_url = ""

    def is_installed(self) -> bool:
        return True

    def install(
        self,
        branch: Optional[str] = None,
        yes: bool = False,
        skip_deps: bool = False,
    ) -> None:
        rich.print(
            "[dim]The default profile requires no installation — "
            "manage ~/.config/hypr/default/ directly.[/dim]"
        )

    def update(self) -> None:
        rich.print("[dim]The default profile has no upstream to update from.[/dim]")

    def uninstall(self) -> None:
        rich.error_message("The default profile cannot be uninstalled.")

    def start(self) -> None:
        # No Quickshell shell to launch for the default profile.
        pass

    def status(self) -> None:
        rich.success_message("default profile is always available.")
        rich.print(f"  [dim]Location :[/dim] ~/.config/hypr/{self.name}/")

    # ------------------------------------------------------------------
    # Dotfile sync
    # ------------------------------------------------------------------

    def sync_dotfiles(self, *, backup: bool = True) -> None:
        """No-op: the default profile has no dotfiles to sync."""

    def sync_hypr_profile(self, *, backup: bool = False) -> None:
        """No-op: the default profile is always available and does not need a Hyprland profile sync."""
