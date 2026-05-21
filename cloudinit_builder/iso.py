"""Build NoCloud cidata ISO images from generated seed files."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

_SEED_NAMES = ("user-data", "meta-data")


def genisoimageAvailable() -> bool:
    """Return True when ``genisoimage`` is on PATH."""
    return shutil.which("genisoimage") is not None


def _requireSeedFiles(seed_dir: Path) -> None:
    missing = [name for name in _SEED_NAMES if not (seed_dir / name).is_file()]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Missing seed file(s) in {seed_dir}: {joined}")


def buildCidataIso(seed_dir: Path, iso_path: Path) -> None:
    """Create a NoCloud ISO at ``iso_path`` from ``user-data`` and ``meta-data`` in ``seed_dir``."""
    seed_dir = seed_dir.resolve()
    iso_path = iso_path.resolve()
    _requireSeedFiles(seed_dir)

    result = subprocess.run(
        [
            "genisoimage",
            "-output",
            str(iso_path),
            "-volid",
            "cidata",
            "-joliet",
            "-r",
            str(seed_dir),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        msg = f"genisoimage failed (exit {result.returncode})"
        if detail:
            msg = f"{msg}: {detail}"
        raise RuntimeError(msg)
