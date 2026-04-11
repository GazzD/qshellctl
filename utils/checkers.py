import shutil
import subprocess
from typing import Callable


def which(binary: str) -> Callable[[], bool]:
    """Return a checker that verifies *binary* exists in PATH."""
    return lambda: shutil.which(binary) is not None


def pkgconfig(module: str) -> Callable[[], bool]:
    """Return a checker that verifies a pkg-config module is available."""
    return lambda: (
        subprocess.run(
            ["pkg-config", "--modversion", module], capture_output=True
        ).returncode
        == 0
    )


def pacman_q(pkg: str) -> Callable[[], bool]:
    """Return a checker that verifies a pacman package is installed."""
    return lambda: (
        subprocess.run(["pacman", "-Q", pkg], capture_output=True).returncode == 0
    )


def font(pattern: str) -> Callable[[], bool]:
    """Return a checker that verifies a font matching *pattern* is installed."""

    def check() -> bool:
        result = subprocess.run(["fc-list"], capture_output=True, text=True)
        return pattern.lower() in result.stdout.lower()

    return check
