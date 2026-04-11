import json
import re
from pathlib import Path

_STATE_FILE = Path.home() / ".local" / "state" / "qshellctl" / "state.json"
_HYPRLAND_CONF = Path.home() / ".config" / "hypr" / "hyprland.conf"


def _detect_active_profile(hyprland_conf: Path) -> str | None:
    """Parse $profile = <name> from hyprland.conf to detect the active profile."""
    if not hyprland_conf.exists():
        return None
    for line in hyprland_conf.read_text().splitlines():
        match = re.match(r"^\s*\$profile\s*=\s*(\S+)", line)
        if match:
            return match.group(1)
    return None


def load() -> dict:
    """Load state from disk.

    If the state file does not exist, attempts to bootstrap it by reading
    the active profile from hyprland.conf, then persists the result.
    Returns the state dict (always has at least 'active_profile').
    """
    if _STATE_FILE.exists():
        return json.loads(_STATE_FILE.read_text())

    active_profile = _detect_active_profile(_HYPRLAND_CONF)
    state = {
        "active_profile": active_profile,
        "hyprland_conf": str(_HYPRLAND_CONF),
    }
    save(state)
    return state


def save(state: dict) -> None:
    """Persist state to disk, creating parent directories if needed."""
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")


def get_active_profile() -> str | None:
    """Return the name of the currently active profile, or None if unknown."""
    return load().get("active_profile")
