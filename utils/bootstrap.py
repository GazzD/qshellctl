from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import shutil

from models.exceptions import BootstrapError
import utils.state as state

_HYPRLAND_DIR = Path.home() / ".config" / "hypr"
_HYPRLAND_CONF = _HYPRLAND_DIR / "hyprland.conf"
_DEFAULT_PROFILE = "default"
_SELECTOR_TEMPLATE = "$profile = default\n\nsource = $profile/hyprland.conf\n"


@dataclass(frozen=True)
class BootstrapResult:
    default_profile_dir: Path
    backup_path: Path | None
    copied_entries: int
    root_rewritten: bool


def ensure_default_profile_dir(hyprland_dir: Path | None = None) -> Path:
    hyprland_root = hyprland_dir or _HYPRLAND_DIR
    default_dir = hyprland_root / _DEFAULT_PROFILE
    default_dir.mkdir(parents=True, exist_ok=True)
    return default_dir


def _copy_path_if_missing(src: Path, dst: Path) -> int:
    if src.is_dir() and not src.is_symlink():
        dst.mkdir(parents=True, exist_ok=True)
        copied_entries = 0
        for child in src.iterdir():
            copied_entries += _copy_path_if_missing(child, dst / child.name)
        return copied_entries

    if dst.exists():
        return 0

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return 1


def copy_current_config_to_default(
    hyprland_dir: Path | None = None,
    default_profile_dir: Path | None = None,
) -> int:
    hyprland_root = hyprland_dir or _HYPRLAND_DIR
    default_dir = default_profile_dir or ensure_default_profile_dir(hyprland_root)
    copied_entries = 0
    for entry in hyprland_root.iterdir():
        if entry == default_dir:
            continue
        copied_entries += _copy_path_if_missing(entry, default_dir / entry.name)
    return copied_entries


def backup_root_hyprland_conf(hyprland_conf: Path | None = None) -> Path:
    root_conf = hyprland_conf or _HYPRLAND_CONF
    if not root_conf.exists():
        raise BootstrapError(f"Cannot back up missing file: {root_conf}")

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = root_conf.with_name(f"{root_conf.name}.qshellctl.bak.{timestamp}")
    shutil.copy2(root_conf, backup_path)
    return backup_path


def write_profile_selector_root(hyprland_conf: Path | None = None) -> None:
    root_conf = hyprland_conf or _HYPRLAND_CONF
    root_conf.write_text(_SELECTOR_TEMPLATE)


def initialize_profile_system() -> BootstrapResult:
    status = state.detect_bootstrap()
    if status.initialized:
        return BootstrapResult(
            default_profile_dir=_HYPRLAND_DIR / _DEFAULT_PROFILE,
            backup_path=None,
            copied_entries=0,
            root_rewritten=False,
        )

    if not _HYPRLAND_CONF.exists():
        raise BootstrapError(f"Hyprland config not found: {_HYPRLAND_CONF}")

    partial_selector = status.profile_source_present and not status.profile_assignment_present
    if partial_selector:
        raise BootstrapError(
            "Partial profile selector detected in root hyprland.conf. "
            "Please fix it manually before running qshellctl init."
        )

    default_profile_dir = ensure_default_profile_dir()
    root_rewritten = False
    copied_entries = 0
    backup_path: Path | None = None

    if status.profile_assignment_present and status.profile_source_present:
        if not status.default_profile_conf_exists:
            raise BootstrapError(
                "Root hyprland.conf already uses profile selection, but "
                "~/.config/hypr/default/hyprland.conf is missing."
            )
    else:
        copied_entries = copy_current_config_to_default(
            hyprland_dir=_HYPRLAND_DIR,
            default_profile_dir=default_profile_dir,
        )
        backup_path = backup_root_hyprland_conf()
        write_profile_selector_root()
        root_rewritten = True

    state.save(
        {
            "active_profile": _DEFAULT_PROFILE,
            "hyprland_conf": str(_HYPRLAND_CONF),
        }
    )

    return BootstrapResult(
        default_profile_dir=default_profile_dir,
        backup_path=backup_path,
        copied_entries=copied_entries,
        root_rewritten=root_rewritten,
    )
