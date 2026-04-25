class ShellError(Exception):
    """Base exception for all shell operation failures."""


class ShellNotFoundError(ShellError):
    """Raised when a shell name is not found in the registry."""


class ShellAlreadyInstalledError(ShellError):
    """Raised when trying to install a shell that is already installed."""


class ShellNotInstalledError(ShellError):
    """Raised when operating on a shell that is not installed."""


class DependencyError(ShellError):
    """Raised when required dependencies are still missing after an install attempt."""


class HyprlandProfileNotFoundError(ShellError):
    """Raised when the Hyprland profile directory for a shell does not exist."""


class ProcessError(Exception):
    """Raised when a subprocess command exits with an unexpected return code."""

    def __init__(self, message: str, cmd: list[str], returncode: int) -> None:
        super().__init__(message)
        self.cmd = cmd
        self.returncode = returncode


class BootstrapError(Exception):
    """Raised when qshellctl cannot initialize the Hyprland profile system."""
