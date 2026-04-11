from dataclasses import dataclass
from typing import Callable, Optional

# ---------------------------------------------------------------------------
# Dependency model
# ---------------------------------------------------------------------------


@dataclass
class Dep:
    label: str
    checker: Callable[[], bool]
    pacman_pkg: Optional[str] = None
    aur_pkg: Optional[str] = None

    def is_installed(self) -> bool:
        try:
            return self.checker()
        except Exception:
            return False

    @property
    def pkg(self) -> str:
        return self.aur_pkg or self.pacman_pkg or self.label

    @property
    def is_aur(self) -> bool:
        return self.aur_pkg is not None
