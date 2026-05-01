"""Save and reload form preferences (JSON in project ``backup/`` by default)."""

from __future__ import annotations

import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Any, Optional

SCHEMA_VERSION = 1
PREFS_FILENAME = "preferences.json"


def preferences_path() -> Path:
    """Path to the saved preferences JSON file."""
    if os.environ.get("CLOUDINIT_PREFS_FILE"):
        return Path(os.environ["CLOUDINIT_PREFS_FILE"]).expanduser()
    backup = os.environ.get("CLOUDINIT_BACKUP_DIR")
    if backup:
        return Path(backup).expanduser() / PREFS_FILENAME
    override_dir = os.environ.get("CLOUDINIT_PREFS_DIR")
    if override_dir:
        return Path(override_dir).expanduser() / "cloudinit_builder_preferences.json"
    return Path(tempfile.gettempdir()) / "cloudinit_builder_preferences.json"


def load_preferences() -> Optional[dict[str, Any]]:
    """Return saved preferences dict, or ``None`` if missing, invalid, or unreadable."""
    try:
        path = preferences_path()
        if not path.is_file():
            return None
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None
    if raw.get("schema_version") != SCHEMA_VERSION:
        return None
    prefs = raw.get("preferences")
    if not isinstance(prefs, dict):
        return None
    return prefs


def sanitize_for_save(form: dict[str, Any]) -> dict[str, Any]:
    """Strip non-persistent secrets and ensure JSON-serializable values."""
    out: dict[str, Any] = {}
    for key, val in form.items():
        if key == "password_plain":
            continue
        if key == "late_users" and isinstance(val, list):
            out[key] = val
            continue
        try:
            json.dumps(val)
        except (TypeError, ValueError):
            continue
        out[key] = val
    return out


def _unlink_file_best_effort(path: Path) -> bool:
    """Delete a file if it exists. Clears read-only on Windows (OneDrive / attrib +R)."""
    try:
        if not path.is_file():
            return False
        try:
            mode = path.stat().st_mode
            path.chmod(mode | stat.S_IWRITE)
        except OSError:
            pass
        path.unlink()
        return True
    except OSError:
        return False


def save_preferences(form: dict[str, Any]) -> Path:
    """Write preferences; returns the path written."""
    path = preferences_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": SCHEMA_VERSION, "preferences": sanitize_for_save(form)}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def clear_preferences() -> bool:
    """Remove backup state (best-effort; does not raise).

    Only removes the preferences **file** (e.g. ``backup/preferences.json``). The ``backup``
    folder is left in place so ``rmtree`` is never used — that avoids ``PermissionError``
    (WinError 5) on OneDrive / locked folders on Windows.

    If ``CLOUDINIT_PREFS_FILE`` is set, deletes that file only.
    Otherwise removes the legacy temp JSON file if present.
    """
    removed = False
    try:
        if os.environ.get("CLOUDINIT_PREFS_FILE"):
            p = Path(os.environ["CLOUDINIT_PREFS_FILE"]).expanduser()
            if _unlink_file_best_effort(p):
                removed = True
            return removed

        pref = preferences_path()
        if _unlink_file_best_effort(pref):
            removed = True

        if os.environ.get("CLOUDINIT_BACKUP_DIR"):
            return removed

        legacy = Path(tempfile.gettempdir()) / "cloudinit_builder_preferences.json"
        if _unlink_file_best_effort(legacy):
            removed = True
    except OSError:
        pass
    return removed


def merge_saved_over_base(base: dict[str, Any], saved: dict[str, Any]) -> dict[str, Any]:
    """Overlay saved keys onto seed/fallback defaults (saved wins)."""
    out = dict(base)
    for key, val in saved.items():
        if key == "password_plain":
            continue
        out[key] = val
    out["password_plain"] = ""
    return out
