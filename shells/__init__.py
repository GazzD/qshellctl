from models.exceptions import ShellNotFoundError
from models.shell import Shell
from shells.caelestia import CaelestiaShell
from shells.ii import IllogicalImpulseShell

# ---------------------------------------------------------------------------
# Registry
#
# Add new shells here — that's the only change needed to make a new shell
# available to all CLI commands.
# ---------------------------------------------------------------------------

REGISTRY: dict[str, type[Shell]] = {
    "caelestia": CaelestiaShell,
    "ii": IllogicalImpulseShell,
}


def get_shell(name: str) -> Shell:
    """Return an instance of the shell registered under *name*.

    Raises:
        ShellNotFoundError: if *name* is not in the registry.
    """
    cls = REGISTRY.get(name)
    if cls is None:
        available = ", ".join(REGISTRY)
        raise ShellNotFoundError(
            f"Unknown shell: '{name}'. Available shells: {available}"
        )
    return cls()


def list_shells() -> list[str]:
    """Return the names of all registered shells."""
    return list(REGISTRY)
