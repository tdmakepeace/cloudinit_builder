"""Project-relative directories for initial seed, generated output, and preference backup."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def project_root() -> Path:
    """Repository root (parent of the ``cloudinit_builder`` package)."""
    return Path(__file__).resolve().parent.parent


def initial_dir() -> Path:
    """Directory containing ``user-data`` and ``meta-data`` templates."""
    raw = os.environ.get("CLOUDINIT_INITIAL_DIR")
    if raw:
        return Path(raw).expanduser()
    return project_root() / "initial"


def output_dir() -> Path:
    """Directory where generated ``user-data`` / ``meta-data`` are written."""
    raw = os.environ.get("CLOUDINIT_OUTPUT_DIR")
    if raw:
        return Path(raw).expanduser()
    return project_root() / "output"


def backup_dir() -> Path:
    """Directory for ``preferences.json`` (saved UI state)."""
    raw = os.environ.get("CLOUDINIT_BACKUP_DIR")
    if raw:
        return Path(raw).expanduser()
    return project_root() / "backup"


def ensure_backup_env() -> None:
    """Point ``CLOUDINIT_BACKUP_DIR`` at the project ``backup/`` folder unless already set."""
    os.environ.setdefault("CLOUDINIT_BACKUP_DIR", str(backup_dir()))


def write_output_files(user_data: str, meta_data: str) -> Path:
    """Write generated NoCloud files under ``output/``; returns the output directory."""
    d = output_dir()
    d.mkdir(parents=True, exist_ok=True)
    (d / "user-data").write_text(user_data, encoding="utf-8", newline="\n")
    (d / "meta-data").write_text(meta_data, encoding="utf-8", newline="\n")
    return d


def read_output_files_if_present() -> tuple[Optional[str], Optional[str]]:
    """Return ``(user_data, meta_data)`` if both files exist under ``output_dir()``; else ``(None, None)``."""
    d = output_dir()
    user_path = d / "user-data"
    meta_path = d / "meta-data"
    if not user_path.is_file() or not meta_path.is_file():
        return None, None
    try:
        return user_path.read_text(encoding="utf-8"), meta_path.read_text(encoding="utf-8")
    except OSError:
        return None, None
