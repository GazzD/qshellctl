import json
import re
from dataclasses import dataclass
from pathlib import Path

_STATE_FILE = Path.home() / ".local" / "state" / "qshellctl" / "state.json"
_HYPRLAND_DIR = Path.home() / ".config" / "hypr"
_HYPRLAND_CONF = _HYPRLAND_DIR / "hyprland.conf"

# Check: $profile = <something>
_PROFILE_ASSIGNMENT_RE = re.compile(r"^\s*\$profile\s*=\s*(\S+)", re.MULTILINE)

# Check: source = $profile/hyprland.conf
_PROFILE_SOURCE_RE = re.compile(
    r"^\s*source\s*=\s*\$profile/hyprland\.conf\s*$", re.MULTILINE
)


@dataclass(frozen=True)
class BootstrapStatus:
    hyprland_conf_exists: bool
    profile_assignment_present: bool
    profile_source_present: bool
    default_profile_exists: bool
    default_profile_conf_exists: bool
    state_file_exists: bool
    state_matches_root: bool
    state_active_profile_valid: bool
    initialized: bool

    def detail(self) -> str:
        if not self.hyprland_conf_exists:
            return f"Missing {_HYPRLAND_CONF}"
        if not self.default_profile_exists:
            return "Missing ~/.config/hypr/default/"
        if not self.default_profile_conf_exists:
            return "Missing ~/.config/hypr/default/hyprland.conf"
        if not self.profile_assignment_present or not self.profile_source_present:
            return "Root hyprland.conf is not a compatible profile selector"
        if not self.state_matches_root:
            return "state.json points to a different hyprland.conf"
        if not self.state_active_profile_valid:
            return "state.json references a missing active profile"
        return "Ready"


def _load_existing_state() -> dict | None:
    if not _STATE_FILE.exists():
        return None
    return json.loads(_STATE_FILE.read_text())


def _has_profile_selector(conf_text: str) -> tuple[bool, bool]:
    """Check whether the root config contains the minimal profile selector."""
    profile_assignment_present = _PROFILE_ASSIGNMENT_RE.search(conf_text) is not None
    profile_source_present = _PROFILE_SOURCE_RE.search(conf_text) is not None
    return profile_assignment_present, profile_source_present


def detect_bootstrap() -> BootstrapStatus:
    """Inspect whether qshellctl's Hyprland profile system is initialized."""
    hyprland_conf_exists = _HYPRLAND_CONF.exists()
    profile_assignment_present = False
    profile_source_present = False
    if hyprland_conf_exists:
        # Get configuration text
        conf_text = _HYPRLAND_CONF.read_text()

        # Has an existing profile selected
        profile_assignment_present, profile_source_present = _has_profile_selector(
            conf_text
        )

    default_profile_dir = _HYPRLAND_DIR / "default"
    default_profile_exists = default_profile_dir.exists()
    default_profile_conf_exists = (default_profile_dir / "hyprland.conf").exists()

    existing_state = _load_existing_state()
    state_file_exists = existing_state is not None
    state_matches_root = True
    state_active_profile_valid = True
    if existing_state is not None:
        state_matches_root = existing_state.get("hyprland_conf") == str(_HYPRLAND_CONF)
        active_profile = existing_state.get("active_profile")
        if active_profile:
            state_active_profile_valid = (
                _HYPRLAND_DIR / active_profile / "hyprland.conf"
            ).exists()

    initialized = (
        hyprland_conf_exists
        and profile_assignment_present
        and profile_source_present
        and default_profile_exists
        and default_profile_conf_exists
        and state_matches_root
        and state_active_profile_valid
    )

    return BootstrapStatus(
        hyprland_conf_exists=hyprland_conf_exists,
        profile_assignment_present=profile_assignment_present,
        profile_source_present=profile_source_present,
        default_profile_exists=default_profile_exists,
        default_profile_conf_exists=default_profile_conf_exists,
        state_file_exists=state_file_exists,
        state_matches_root=state_matches_root,
        state_active_profile_valid=state_active_profile_valid,
        initialized=initialized,
    )


def is_bootstrapped() -> bool:
    """Return True when qshellctl's profile system is ready to use."""
    return detect_bootstrap().initialized


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
